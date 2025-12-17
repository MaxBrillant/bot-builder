# WhatsApp Integration - MVP Implementation Guide

**Version**: 1.0 MVP  
**Status**: Implementation Ready  
**Focus**: User self-service WhatsApp instance management

---

## 🎯 MVP Scope

### What We're Building

A streamlined WhatsApp integration that allows Bot Builder users to:

1. **Create WhatsApp instances** for their bots via UI/API
2. **Connect their phone** by scanning a QR code
3. **Start receiving messages** automatically once connected
4. **Monitor connection status** of their WhatsApp instances

### What's Included in MVP

✅ User creates WhatsApp instance for their bot
✅ QR code generation and display
✅ WhatsApp connection via phone scan
✅ Basic text message send/receive
✅ Async message processing (Celery + Redis)
✅ Real-time metrics and monitoring (Prometheus)
✅ Instance management (activate/deactivate)

### What's NOT in MVP (Future)

❌ Media support (images, documents)  
❌ WhatsApp Business features (buttons, lists)  
❌ Multi-device support  
❌ Message templates  
❌ Advanced analytics  
❌ Message scheduling

---

## 🏗️ Simplified Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Bot Builder User                          │
│                                                               │
│  1. Creates Bot                                              │
│  2. Creates WhatsApp Instance for Bot                        │
│  3. Scans QR Code with Phone                                 │
│  4. Messages route to Bot automatically                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Bot Builder Core (Enhanced)                     │
│                                                               │
│  New APIs:                                                   │
│  - POST   /bots/{bot_id}/whatsapp/instances                 │
│  - GET    /bots/{bot_id}/whatsapp/instances                 │
│  - GET    /bots/{bot_id}/whatsapp/instances/{id}/qr         │
│  - GET    /bots/{bot_id}/whatsapp/instances/{id}/status     │
│  - PATCH  /bots/{bot_id}/whatsapp/instances/{id}            │
│  - DELETE /bots/{bot_id}/whatsapp/instances/{id}            │
│                                                               │
│  New Tables:                                                 │
│  - whatsapp_instances (stores instance configs)             │
│  - whatsapp_messages (message queue)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Manages & Communicates
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Evolution API                             │
│  - Handles WhatsApp protocol                                 │
│  - Generates QR codes                                        │
│  - Sends webhooks to Bot Builder                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ WhatsApp Protocol
                         ▼
                   [User's WhatsApp]
```

### Key Design Decisions

#### 1. Direct Integration
We're **embedding WhatsApp management directly into Bot Builder** rather than creating a separate adapter service. This:

- ✅ Reduces complexity (one service instead of two)
- ✅ Easier deployment (users manage everything from Bot Builder UI)
- ✅ Faster to implement
- ✅ Can be refactored to separate service later if needed

#### 2. Celery for Production Scale
We're using **Celery + Redis** for message processing because:

- ✅ Target: **10 req/sec** (864,000 messages/day) requires reliable task queue
- ✅ Task persistence (no lost messages on restart)
- ✅ Automatic retries with exponential backoff
- ✅ Horizontal scaling (multiple worker processes)
- ✅ Production-grade monitoring (Flower, Prometheus)
- ✅ Battle-tested at scale

**Note:** While Bot Builder core is asyncio-first, Celery is the right tool for high-volume distributed task processing. Celery workers use synchronous database sessions (standard pattern).

---

## 📊 Database Schema (Add to Bot Builder)

### Table 1: `whatsapp_instances`

```sql
CREATE TABLE whatsapp_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    bot_id UUID NOT NULL REFERENCES bots(bot_id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Evolution API instance details
    instance_name VARCHAR(255) NOT NULL UNIQUE,
    -- Format: "bot_{bot_id}_{random}" e.g., "bot_550e8400_a3f2"

    phone_number VARCHAR(50) UNIQUE,  -- Set after connection

    -- Connection status
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    -- Values: 'created', 'connecting', 'connected', 'disconnected', 'error'

    -- Connection tracking (QR codes NOT stored - fetched directly from Evolution API)
    connected_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    error_message TEXT,
    error_count INT NOT NULL DEFAULT 0,

    -- Settings
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_primary BOOLEAN NOT NULL DEFAULT true,  -- Allow multiple instances per bot

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints (Note: Removed strict unique_bot_whatsapp to allow multiple instances)
    CONSTRAINT fk_bot FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE,
    CONSTRAINT fk_owner FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_whatsapp_instances_bot ON whatsapp_instances(bot_id);
CREATE INDEX idx_whatsapp_instances_owner ON whatsapp_instances(owner_user_id);
CREATE INDEX idx_whatsapp_instances_status ON whatsapp_instances(status);
CREATE INDEX idx_whatsapp_instances_phone ON whatsapp_instances(phone_number);
CREATE INDEX idx_whatsapp_instances_active_primary ON whatsapp_instances(bot_id, is_active, is_primary)
    WHERE is_active = true AND is_primary = true;

-- Note: Multiple instances per bot allowed (dev/prod, etc.), use is_primary flag
```

### Design Decision: No Message Storage

**We do NOT store message content or stats in the database.**

**Rationale:**
- 📊 **Metrics via Prometheus**: Real-time counters, histograms for message processing
- 📝 **Structured Logging**: ELK/Datadog for debugging with 30-day retention
- 💾 **Storage Savings**: At 10 req/sec (864k messages/day), would be ~5GB/day in DB
- ⚡ **Performance**: No database writes on every message = faster processing
- 🔍 **Evolution API Stats**: Already provides per-instance message counts

**What We Track:**
- Instance configuration (stored in `whatsapp_instances`)
- Prometheus metrics (counters, processing time)
- Structured logs (errors, processing events)
- Evolution API built-in statistics

**Benefits:**
- ✅ Minimal database footprint
- ✅ No retention/archival complexity
- ✅ Fast query performance
- ✅ Standard observability stack

---

## 🔌 New API Endpoints (Bot Builder)

### 1. Create WhatsApp Instance

```http
POST /bots/{bot_id}/whatsapp/instances
Authorization: Bearer {token}
Content-Type: application/json

{}
```

**Response:**

```json
{
  "id": "instance-uuid",
  "bot_id": "bot-uuid",
  "instance_name": "bot_550e8400_a3f2",
  "status": "created",
  "is_primary": true,
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "qr_code_expires_at": "2024-12-06T15:05:00Z",
  "created_at": "2024-12-06T15:00:00Z",
  "message": "Scan QR code with WhatsApp to connect"
}

**Note:** QR code is fetched directly from Evolution API and returned in response. It is NOT stored in the database to avoid unnecessary storage overhead for temporary data.
```

**Business Logic:**

1. Check user owns the bot
2. Check bot doesn't already have active primary WhatsApp instance (or allow if creating secondary)
3. Generate unique instance name: `bot_{bot_id}_{random_4_chars}`
4. Call Evolution API to create instance
5. Configure webhook for instance
6. Get QR code from Evolution API (not stored)
7. Store instance record in database
8. Return instance data with QR code to user

**Phone Number Normalization:**
All phone numbers are normalized to E.164 format (+[country][number]) to ensure consistent session keys.

### 2. Get WhatsApp Instances

```http
GET /bots/{bot_id}/whatsapp/instances
Authorization: Bearer {token}
```

**Response:**

```json
{
  "instances": [
    {
      "id": "instance-uuid",
      "bot_id": "bot-uuid",
      "instance_name": "bot_550e8400_a3f2",
      "phone_number": "+254712345678",
      "status": "connected",
      "connected_at": "2024-12-06T15:02:00Z",
      "last_seen_at": "2024-12-06T15:30:00Z",
      "is_active": true,
      "created_at": "2024-12-06T15:00:00Z"
    }
  ]
}
```

### 3. Get QR Code (for reconnection)

```http
GET /bots/{bot_id}/whatsapp/instances/{instance_id}/qr
Authorization: Bearer {token}
```

**Response:**

```json
{
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "expires_at": "2024-12-06T15:35:00Z"
}
```

### 4. Get Connection Status

```http
GET /bots/{bot_id}/whatsapp/instances/{instance_id}/status
Authorization: Bearer {token}
```

**Response:**

```json
{
  "status": "connected",
  "phone_number": "+254712345678",
  "last_seen_at": "2024-12-06T15:30:00Z",
  "message_count_today": 45
}
```

### 5. Update Instance (Activate/Deactivate)

```http
PATCH /bots/{bot_id}/whatsapp/instances/{instance_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "is_active": false
}
```

**Response:**

```json
{
  "id": "instance-uuid",
  "is_active": false,
  "updated_at": "2024-12-06T15:35:00Z"
}
```

### 6. Delete Instance

```http
DELETE /bots/{bot_id}/whatsapp/instances/{instance_id}
Authorization: Bearer {token}
```

**Response:**

```json
{
  "message": "WhatsApp instance deleted successfully"
}
```

**Business Logic:**

1. Check user owns the bot
2. Call Evolution API to logout/delete instance
3. Delete from database (cascades to messages)
4. Return success

---

## 📥 Webhook Endpoint (Bot Builder)

### Evolution API Webhook

```http
POST /webhooks/whatsapp/evolution
Content-Type: application/json
X-Api-Key: {shared_secret}

{
  "event": "messages.upsert",
  "instance": "bot_550e8400_a3f2",
  "data": {
    "key": {
      "remoteJid": "254712345678@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0C67F9A2B1E4F5D6C"
    },
    "message": {
      "conversation": "START"
    },
    "messageTimestamp": "1701860000"
  }
}
```

**Webhook Handler Logic:**

```python
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.schemas.whatsapp_schema import EvolutionWebhookSchema
from app.services.whatsapp_service import WhatsAppService
from app.tasks.whatsapp_tasks import process_whatsapp_message
from app.utils.logger import logger

router = APIRouter(tags=["whatsapp-webhooks"])


@router.post("/webhooks/whatsapp/evolution")
async def evolution_webhook(
    webhook_data: EvolutionWebhookSchema,
    x_api_key: str = Header(None, alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive webhooks from Evolution API and queue for Celery processing

    Events:
    - messages.upsert: New message received
    - messages.update: Message status changed
    - connection.update: Connection status changed
    """

    # Validate API key (HMAC signature validation recommended for production)
    if x_api_key != settings.whatsapp.webhook_secret:
        logger.warning("Invalid webhook secret attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    whatsapp_service = WhatsAppService(db)

    # Get instance by name
    instance = await whatsapp_service.get_instance_by_name(webhook_data.instance)
    if not instance:
        return {"status": "ignored", "reason": "instance_not_found"}

    if webhook_data.event == "messages.upsert":
        # Queue inbound message for Celery processing
        process_whatsapp_message.delay(
            instance_id=str(instance.id),
            bot_id=str(instance.bot_id),
            message_data=webhook_data.data
        )
        return {"status": "queued"}

    elif webhook_data.event == "connection.update":
        # Update instance connection status immediately
        new_status = map_connection_status(webhook_data.data.state)
        await whatsapp_service.update_instance_status(instance.id, new_status)
        return {"status": "updated"}

    return {"status": "ok"}
```

---

## ⚙️ Background Tasks (FastAPI)

### Task 1: Process Inbound WhatsApp Message

```python
# app/tasks/whatsapp_tasks.py

from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.whatsapp_message import WhatsAppMessage
from app.services.whatsapp_service import WhatsAppService
from app.services.evolution_api_client import evolution_api
from app.core.engine import ConversationOrchestrator
from app.utils.logger import logger
from app.utils.phone_utils import normalize_phone_number


async def process_whatsapp_message(
    instance_id: str,
    bot_id: str,
    message_data: dict
):
    """
    Process incoming WhatsApp message in background

    Steps:
    1. Extract phone number and message text
    2. Save to whatsapp_messages table
    3. Call Bot Builder's existing ConversationOrchestrator
    4. Send response back via Evolution API
    """

    # Create new async session for background task
    async with AsyncSessionLocal() as db:
        try:
            # Extract data
            remote_jid = message_data["key"]["remoteJid"]
            phone = extract_phone_from_jid(remote_jid)  # "254712345678"
            formatted_phone = normalize_phone_number(phone)  # "+254712345678"

            text_content = message_data["message"].get("conversation", "")
            message_id = message_data["key"]["id"]

            # Get instance
            whatsapp_service = WhatsAppService(db)
            instance = await whatsapp_service.get_instance_by_id(UUID(instance_id))

            # Save to messages table
            msg_record = WhatsAppMessage(
                instance_id=UUID(instance_id),
                bot_id=UUID(bot_id),
                direction="inbound",
                phone_number=formatted_phone,
                message_text=text_content,
                evolution_message_id=message_id,
                status="processing"
            )
            db.add(msg_record)
            await db.commit()
            await db.refresh(msg_record)

            # Process through conversation engine
            conversation_engine = ConversationOrchestrator(db)
            result = await conversation_engine.process_message(
                channel="whatsapp",
                channel_user_id=formatted_phone,
                bot_id=UUID(bot_id),
                message=text_content
            )

            # Update message record
            msg_record.status = "sent"
            msg_record.session_id = result.get("session_id")
            msg_record.processed_at = datetime.utcnow()
            await db.commit()

            # Send response if present
            response_text = "\n\n".join(result.get("messages", []))
            if response_text:
                await send_whatsapp_message(
                    instance_id=instance_id,
                    bot_id=bot_id,
                    phone_number=formatted_phone,
                    message_text=response_text
                )

            logger.info(
                f"Processed WhatsApp message from {formatted_phone}",
                instance_id=instance_id,
                message_id=message_id
            )

        except Exception as exc:
            logger.error(
                f"Failed to process WhatsApp message: {str(exc)}",
                instance_id=instance_id,
                exc_info=True
            )

            # Update message record with error
            if 'msg_record' in locals():
                msg_record.status = "failed"
                msg_record.error_message = str(exc)
                msg_record.retry_count += 1
                await db.commit()

            # Could implement retry logic here if needed
            raise


def extract_phone_from_jid(remote_jid: str) -> str:
    """Extract phone number from WhatsApp JID format"""
    # "254712345678@s.whatsapp.net" -> "254712345678"
    return remote_jid.split("@")[0]
```

### Task 2: Send Outbound WhatsApp Message

```python
async def send_whatsapp_message(
    instance_id: str,
    bot_id: str,
    phone_number: str,
    message_text: str
):
    """
    Send message via Evolution API
    """
    async with AsyncSessionLocal() as db:
        try:
            whatsapp_service = WhatsAppService(db)
            instance = await whatsapp_service.get_instance_by_id(UUID(instance_id))

            # Save to messages table
            msg_record = WhatsAppMessage(
                instance_id=UUID(instance_id),
                bot_id=UUID(bot_id),
                direction="outbound",
                phone_number=phone_number,
                message_text=message_text,
                status="processing"
            )
            db.add(msg_record)
            await db.commit()
            await db.refresh(msg_record)

            # Send via Evolution API
            phone_clean = phone_number.replace("+", "")  # "+254712..." -> "254712..."

            client = await evolution_api.get_client()
            response = await client.post(
                f"/message/sendText/{instance.instance_name}",
                json={
                    "number": phone_clean,
                    "text": message_text
                }
            )
            response.raise_for_status()
            response_data = response.json()

            # Update record
            msg_record.status = "sent"
            msg_record.evolution_message_id = response_data["key"]["id"]
            msg_record.processed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                f"Sent WhatsApp message to {phone_number}",
                instance_id=instance_id
            )

        except Exception as exc:
            logger.error(
                f"Failed to send WhatsApp message: {str(exc)}",
                instance_id=instance_id,
                exc_info=True
            )

            # Update record with error
            if 'msg_record' in locals():
                msg_record.status = "failed"
                msg_record.error_message = str(exc)
                msg_record.retry_count += 1
                await db.commit()

            raise
```

### Phone Number Normalization Utility

```python
# app/utils/phone_utils.py

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format

    Args:
        phone: Phone number in any format (e.g., "254712345678", "+254712345678")

    Returns:
        Phone number in E.164 format (e.g., "+254712345678")

    Raises:
        ValueError: If phone number is invalid
    """
    try:
        # Add + if missing
        if not phone.startswith("+"):
            phone = f"+{phone}"

        # Parse and format
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {phone}")

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException as e:
        raise ValueError(f"Failed to parse phone number {phone}: {str(e)}")
```

**Note:** Add `phonenumbers==8.13.26` to [`requirements.txt`](requirements.txt:1) for phone normalization.

---

## 🔧 Evolution API Client

```python
# app/services/evolution_api_client.py

from typing import Optional
import httpx
from app.config import settings
from app.utils.logger import logger


class EvolutionAPIClient:
    """
    Client for Evolution API operations with proper lifecycle management

    Uses singleton pattern with lazy initialization.
    HTTP client is created on first use and closed on shutdown.
    """

    def __init__(self):
        self.base_url = settings.whatsapp.evolution_api_url
        self.api_key = settings.whatsapp.evolution_api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client (lazy initialization)"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"apikey": self.api_key}
            )
            logger.info("Evolution API client initialized")
        return self._client

    async def close(self):
        """Close HTTP client and cleanup resources"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Evolution API client closed")

    async def create_instance(self, instance_name: str) -> dict:
        """Create new WhatsApp instance"""
        client = await self.get_client()
        response = await client.post(
            "/instance/create",
            json={
                "instanceName": instance_name,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_qr_code(self, instance_name: str) -> dict:
        """Get QR code for instance connection"""
        client = await self.get_client()
        response = await client.get(f"/instance/connect/{instance_name}")
        response.raise_for_status()
        return response.json()

    async def set_webhook(self, instance_name: str) -> dict:
        """Configure webhook for instance"""
        webhook_url = f"{settings.base_url}/webhooks/whatsapp/evolution"

        client = await self.get_client()
        response = await client.post(
            f"/webhook/set/{instance_name}",
            json={
                "url": webhook_url,
                "webhook_by_events": True,
                "webhook_base64": False,
                "events": [
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "CONNECTION_UPDATE"
                ]
            }
        )
        response.raise_for_status()
        return response.json()

    async def send_text(
        self,
        instance_name: str,
        phone: str,
        text: str
    ) -> dict:
        """Send text message"""
        client = await self.get_client()
        response = await client.post(
            f"/message/sendText/{instance_name}",
            json={
                "number": phone,
                "text": text
            }
        )
        response.raise_for_status()
        return response.json()

    async def logout_instance(self, instance_name: str) -> dict:
        """Logout WhatsApp instance"""
        client = await self.get_client()
        response = await client.delete(f"/instance/logout/{instance_name}")
        response.raise_for_status()
        return response.json()

    async def get_connection_state(self, instance_name: str) -> dict:
        """Get instance connection status"""
        client = await self.get_client()
        response = await client.get(f"/instance/connectionState/{instance_name}")
        response.raise_for_status()
        return response.json()


# Global singleton instance
evolution_api = EvolutionAPIClient()
```

### Integrating with App Lifecycle

Add to [`app/main.py`](app/main.py:1):

```python
from app.services.evolution_api_client import evolution_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await redis_manager.connect()
    await init_http_client()
    # Evolution API uses lazy initialization - no startup needed

    yield

    # Shutdown
    await evolution_api.close()  # ADD THIS LINE
    await close_http_client()
    await redis_manager.disconnect()
    await close_db()
```

---

## 📋 Implementation Checklist

### Phase 1: Database & Models (Week 1)

- [ ] Create Alembic migration for `whatsapp_instances` table
- [ ] Create Alembic migration for `whatsapp_messages` table
- [ ] Create SQLAlchemy model: [`WhatsAppInstance`](app/models/whatsapp_instance.py)
- [ ] Create SQLAlchemy model: [`WhatsAppMessage`](app/models/whatsapp_message.py)
- [ ] Create Pydantic schemas for WhatsApp endpoints

### Phase 2: Evolution API Integration (Week 1)

- [ ] Add `WhatsAppConfig` nested config to [`app/config.py`](app/config.py:1)
- [ ] Implement [`EvolutionAPIClient`](app/services/evolution_api_client.py) class with lifecycle management
- [ ] Add to [`requirements.txt`](requirements.txt:1): `phonenumbers==8.13.26`
- [ ] Add Evolution API to [`docker-compose.yml`](docker-compose.yml:1)
- [ ] Integrate `evolution_api.close()` into app lifecycle in [`app/main.py`](app/main.py:1)

### Phase 3: API Endpoints (Week 2)

- [ ] Create [`app/api/whatsapp.py`](app/api/whatsapp.py) router
- [ ] Implement `POST /bots/{bot_id}/whatsapp/instances`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances/{id}/qr`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances/{id}/status`
- [ ] Implement `PATCH /bots/{bot_id}/whatsapp/instances/{id}`
- [ ] Implement `DELETE /bots/{bot_id}/whatsapp/instances/{id}`
- [ ] Register router in [`app/main.py`](app/main.py:1)

### Phase 4: Webhooks & Background Tasks (Week 2)

- [ ] Create [`app/tasks/whatsapp_tasks.py`](app/tasks/whatsapp_tasks.py)
- [ ] Implement `process_whatsapp_message` background task
- [ ] Implement `send_whatsapp_message` background task
- [ ] Create [`app/utils/phone_utils.py`](app/utils/phone_utils.py) with normalization utility
- [ ] Add webhook endpoint `POST /webhooks/whatsapp/evolution` using BackgroundTasks
- [ ] Create [`app/services/whatsapp_service.py`](app/services/whatsapp_service.py) service layer
- [ ] Create [`app/repositories/whatsapp_repository.py`](app/repositories/whatsapp_repository.py) repository

### Phase 5: Testing & Polish (Week 3)

- [ ] End-to-end test: Create instance → Scan QR → Send message → Receive response
- [ ] Test reconnection flow (QR code refresh)
- [ ] Test error scenarios (Evolution API down, etc.)
- [ ] Add logging for all WhatsApp operations
- [ ] Update [`README.md`](README.md:1) with WhatsApp setup instructions
- [ ] Create user documentation

---

## 🚀 Quick Start Guide (For Users)

### Step 1: Create a Bot

```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My WhatsApp Bot",
    "description": "Customer support bot"
  }'
```

### Step 2: Create Flow(s)

```bash
curl -X POST http://localhost:8000/bots/YOUR_BOT_ID/flows \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @welcome_flow.json
```

### Step 3: Create WhatsApp Instance

```bash
curl -X POST http://localhost:8000/bots/YOUR_BOT_ID/whatsapp/instances \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response includes QR code as base64 image**

### Step 4: Scan QR Code

- Open WhatsApp on your phone
- Go to Settings → Linked Devices → Link a Device
- Scan the QR code from API response
- Wait for connection (status updates to "connected")

### Step 5: Start Chatting!

- Send message to the connected WhatsApp number
- Bot processes through flows automatically
- Receives response based on flow logic

---

## 🔐 Configuration

### Environment Variables (Add to Bot Builder)

Bot Builder uses **nested Pydantic configuration** for type safety and validation.

```bash
# WhatsApp/Evolution API Configuration (nested with WHATSAPP__ prefix)
WHATSAPP__ENABLED=true
WHATSAPP__EVOLUTION_API_URL=http://evolution-api:8080
WHATSAPP__EVOLUTION_API_KEY=your-evolution-api-key-here-min-32-chars
WHATSAPP__WEBHOOK_SECRET=your-webhook-secret-here-min-32-chars
WHATSAPP__QR_CODE_TTL=120

# Base URL (already exists in settings)
BASE_URL=https://your-domain.com

# Redis (already exists - used for rate limiting and caching, not message queue)
REDIS__URL=redis://redis:6379/0
REDIS__ENABLED=true
```

### Add to [`app/config.py`](app/config.py:1):

```python
class WhatsAppConfig(BaseSettings):
    """WhatsApp/Evolution API configuration"""
    enabled: bool = False
    evolution_api_url: str = "http://evolution-api:8080"
    evolution_api_key: str = Field(..., min_length=32, description="Evolution API key")
    webhook_secret: str = Field(..., min_length=32, description="Webhook validation secret")
    qr_code_ttl: int = Field(120, ge=30, le=300, description="QR code TTL in seconds")

    model_config = SettingsConfigDict(env_prefix="WHATSAPP__")


class Settings(BaseSettings):
    # ... existing fields ...
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
```

### Docker Compose Updates

```yaml
# Add to docker-compose.yml

services:
  # Existing services (api, db, redis)...

  evolution-api:
    image: atendai/evolution-api:latest
    container_name: evolution-api
    ports:
      - "8080:8080"
    environment:
      - SERVER_URL=${BASE_URL:-http://localhost:8000}
      - AUTHENTICATION_API_KEY=${WHATSAPP__EVOLUTION_API_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_CONNECTION_URI=postgresql://botbuilder:${DB_PASSWORD:-password}@db:5432/evolution
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - botbuilder-network
    restart: unless-stopped

  # Update API service to include WhatsApp env vars
  api:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      # WhatsApp config (nested with __)
      - WHATSAPP__ENABLED=${WHATSAPP__ENABLED:-false}
      - WHATSAPP__EVOLUTION_API_URL=http://evolution-api:8080
      - WHATSAPP__EVOLUTION_API_KEY=${WHATSAPP__EVOLUTION_API_KEY}
      - WHATSAPP__WEBHOOK_SECRET=${WHATSAPP__WEBHOOK_SECRET}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
      evolution-api:  # ADD THIS
        condition: service_healthy

# Note: No Celery worker needed - using FastAPI BackgroundTasks
```

---

## 📊 User Flow Diagram

```
User Journey: Connect WhatsApp to Bot
─────────────────────────────────────

1. User logs into Bot Builder
   │
   ├─> Views their bots
   │
   └─> Clicks "Connect WhatsApp" on a bot
       │
       └─> System creates WhatsApp instance
           │
           ├─> Evolution API generates QR code
           │
           └─> User sees QR code on screen
               │
               └─> User scans with WhatsApp app
                   │
                   ├─> WhatsApp connects (webhook fires)
                   │
                   └─> Status updates to "Connected"
                       │
                       └─> Bot is now live on WhatsApp! ✅

Message Journey: User → Bot → Response
──────────────────────────────────────

1. WhatsApp user sends "START"
   │
   ├─> Evolution API receives message
   │
   └─> Webhook fires to Bot Builder
       │
       ├─> FastAPI queues as background task
       │
       └─> Background task processes message
           │
           ├─> Finds WhatsApp instance
           │
           ├─> Normalizes phone number
           │
           ├─> Extracts message text
           │
           └─> Calls ConversationOrchestrator
               │
               ├─> Engine processes flow
               │
               └─> Returns response text
                   │
                   ├─> Queue outbound message
                   │
                   └─> Send via Evolution API
                       │
                       └─> User receives response ✅
```

---

## 🎯 MVP Success Criteria

### Must Have (MVP Launch)

✅ User can create WhatsApp instance for their bot  
✅ User can scan QR code to connect their phone  
✅ Bot receives messages and processes through flows  
✅ Bot sends responses back to user  
✅ Connection status visible to user  
✅ User can disconnect/delete instance

### Nice to Have (Post-MVP)

- Instance health monitoring dashboard
- Message history/logs in UI
- Multiple devices per instance
- Media message support
- Automatic reconnection on disconnect
- Message analytics and insights

---

## 🏗️ Architecture Decision: AsyncIO vs Celery

### Why FastAPI BackgroundTasks for MVP?

**Context:**
Bot Builder is built **asyncio-first** with AsyncSession, async/await patterns, and asyncio background tasks throughout (see [`main.py:69-104`](app/main.py:69) for existing cleanup loop).

**Decision:**
Use FastAPI BackgroundTasks instead of introducing Celery.

**Rationale:**

| Criteria | FastAPI BackgroundTasks | Celery |
|----------|------------------------|--------|
| **Consistency** | ✅ Matches existing patterns | ❌ Introduces new paradigm |
| **Deployment** | ✅ Single process | ❌ Separate worker + broker |
| **AsyncSession** | ✅ Native support | ⚠️ Requires careful handling |
| **Scaling** | ✅ Sufficient for <1k msgs/day | ✅ Excels at >10k msgs/day |
| **Monitoring** | ✅ Standard logs | ✅ Rich tooling (Flower) |
| **Complexity** | ✅ Low | ❌ High (broker, workers, serialization) |
| **Operational** | ✅ Minimal overhead | ❌ More moving parts |

**Expected Load:**
MVP expects **<100 messages/day** initially. FastAPI BackgroundTasks handles this easily.

**When to Migrate to Celery:**
- Message volume consistently **>10,000/day**
- Need distributed task processing across multiple machines
- Require advanced features (task chaining, retries with exponential backoff, priority queues)
- Hit concurrency limits of BackgroundTasks

**Migration is straightforward:**
Background task functions can be converted to Celery tasks with minimal code changes (add decorators, update function calls).

---

## 🐛 Common Issues & Solutions

### Issue 1: QR Code Expired

**Symptom**: QR code doesn't work after 2-3 minutes  
**Solution**: Refresh QR code via API:

```bash
GET /bots/{bot_id}/whatsapp/instances/{id}/qr
```

### Issue 2: Messages Not Received

**Checklist**:

- [ ] WhatsApp instance status = "connected"
- [ ] Evolution API container running and healthy
- [ ] Bot Builder API service running
- [ ] Webhook secret matches between Evolution API and Bot Builder
- [ ] Check [`whatsapp_messages`](whatsapp_messages) table for errors
- [ ] Check logs for background task failures

### Issue 3: Bot Not Responding

**Debug Steps**:

1. Check message reached database: `SELECT * FROM whatsapp_messages WHERE status='failed'`
2. Check bot has active flows with trigger keywords
3. Check Bot Builder logs for `ConversationOrchestrator` errors
4. Verify webhook secret matches in Evolution API
5. Check phone number normalization: `SELECT phone_number FROM whatsapp_messages ORDER BY created_at DESC LIMIT 10`

### Issue 4: Session Not Persisting

**Symptom**: User loses conversation context between messages

**Likely Cause**: Phone number format inconsistency

**Debug**:
```sql
-- Check for duplicate sessions with different phone formats
SELECT channel_user_id, COUNT(*)
FROM sessions
WHERE channel = 'whatsapp'
GROUP BY channel_user_id
HAVING COUNT(*) > 1;
```

**Solution**: Ensure all phone numbers pass through `normalize_phone_number()` utility before session creation.

---

## 📚 Next Steps After MVP

### Phase 2 Features (Priority Order)

1. **Media Support**: Images, documents, audio
2. **Message Templates**: Pre-approved WhatsApp Business messages
3. **Rich Messages**: Buttons, lists, quick replies
4. **Multi-device**: Support for WhatsApp Web + mobile
5. **Analytics Dashboard**: Message volume, response times, user engagement
6. **Broadcast Messages**: Send to multiple users
7. **Contact Management**: Store and segment users

---

## ✅ Summary

This MVP implementation:

- ✅ **Architecturally Aligned**: Uses asyncio patterns consistent with existing Bot Builder codebase
- ✅ **Lean**: Adds WhatsApp without Celery complexity or separate services
- ✅ **User-Friendly**: Self-service instance creation and management
- ✅ **Scalable**: FastAPI BackgroundTasks sufficient for MVP, can migrate to Celery if needed
- ✅ **Maintainable**: Clean separation with service/repository pattern and Evolution API client
- ✅ **Production-Ready**: Error handling, phone normalization, proper lifecycle management, logging included

**Total Implementation Time**: 2-3 weeks for core team

**Files to Create/Modify**:

**New Files (8):**
- `app/models/whatsapp_instance.py` - Instance model
- `app/models/whatsapp_message.py` - Message model
- `app/schemas/whatsapp_schema.py` - Pydantic schemas
- `app/services/whatsapp_service.py` - Business logic
- `app/services/evolution_api_client.py` - Evolution API integration
- `app/repositories/whatsapp_repository.py` - Data access layer
- `app/api/whatsapp.py` - REST endpoints
- `app/utils/phone_utils.py` - Phone normalization
- `app/tasks/whatsapp_tasks.py` - Background tasks
- `alembic/versions/002_add_whatsapp.py` - Database migration

**Modified Files (4):**
- [`app/config.py`](app/config.py:1) - Add WhatsAppConfig
- [`app/main.py`](app/main.py:1) - Register router, add evolution_api lifecycle
- [`docker-compose.yml`](docker-compose.yml:1) - Add Evolution API service
- [`requirements.txt`](requirements.txt:1) - Add phonenumbers library

**Database:** 2 new tables (whatsapp_instances, whatsapp_messages)

### Key Improvements Over Original Guide

1. **Correct imports**: Uses `ConversationOrchestrator` from `app.core.engine` (not `ConversationEngine`)
2. **Proper async patterns**: AsyncSession with explicit transaction control
3. **No Celery**: Simplified deployment using FastAPI BackgroundTasks
4. **Lifecycle management**: Evolution API client properly integrated with app startup/shutdown
5. **Phone normalization**: Prevents session key collision issues
6. **Multiple instances**: Removed strict one-per-bot constraint
7. **No QR storage**: Fetched directly from Evolution API
8. **Config consistency**: Uses nested Pydantic pattern matching existing codebase

Ready to implement! 🚀

### Migration Path

If you outgrow FastAPI BackgroundTasks (>10k messages/day), migrate to Celery:
1. Add `celery[redis]==5.3.4` to requirements.txt
2. Convert background task functions to Celery tasks
3. Add Celery worker to docker-compose.yml
4. Update webhook to use `.delay()` instead of `background_tasks.add_task()`
