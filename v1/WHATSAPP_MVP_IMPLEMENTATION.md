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
✅ Connection status monitoring  
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

### Key Design Decision: Direct Integration

For MVP, we're **embedding WhatsApp management directly into Bot Builder** rather than creating a separate adapter service. This:

- ✅ Reduces complexity (one service instead of two)
- ✅ Easier deployment (users manage everything from Bot Builder UI)
- ✅ Faster to implement
- ✅ Can be refactored to separate service later if needed

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

    qr_code TEXT,  -- Base64 QR code (temporary)
    qr_code_updated_at TIMESTAMP,

    connected_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    error_message TEXT,

    -- Settings
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_bot_whatsapp UNIQUE (bot_id),
    CONSTRAINT fk_bot FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE,
    CONSTRAINT fk_owner FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_whatsapp_instances_bot ON whatsapp_instances(bot_id);
CREATE INDEX idx_whatsapp_instances_owner ON whatsapp_instances(owner_user_id);
CREATE INDEX idx_whatsapp_instances_status ON whatsapp_instances(status);
CREATE INDEX idx_whatsapp_instances_phone ON whatsapp_instances(phone_number);

-- Note: One WhatsApp instance per bot (enforced by unique_bot_whatsapp)
```

### Table 2: `whatsapp_messages`

```sql
CREATE TABLE whatsapp_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    instance_id UUID NOT NULL REFERENCES whatsapp_instances(id) ON DELETE CASCADE,
    bot_id UUID NOT NULL REFERENCES bots(bot_id) ON DELETE CASCADE,

    -- Message details
    direction VARCHAR(20) NOT NULL,  -- 'inbound' or 'outbound'
    phone_number VARCHAR(50) NOT NULL,
    message_text TEXT NOT NULL,

    -- Evolution API details
    evolution_message_id VARCHAR(255),

    -- Processing
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Values: 'pending', 'processing', 'sent', 'delivered', 'failed'

    retry_count INT NOT NULL DEFAULT 0,
    error_message TEXT,

    -- Bot Builder session
    session_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,

    -- Constraints
    CONSTRAINT fk_instance FOREIGN KEY (instance_id) REFERENCES whatsapp_instances(id) ON DELETE CASCADE,
    CONSTRAINT fk_bot FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_whatsapp_messages_instance ON whatsapp_messages(instance_id);
CREATE INDEX idx_whatsapp_messages_bot ON whatsapp_messages(bot_id);
CREATE INDEX idx_whatsapp_messages_status ON whatsapp_messages(status);
CREATE INDEX idx_whatsapp_messages_direction ON whatsapp_messages(direction);
CREATE INDEX idx_whatsapp_messages_created ON whatsapp_messages(created_at);
```

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
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "qr_code_expires_at": "2024-12-06T15:05:00Z",
  "created_at": "2024-12-06T15:00:00Z",
  "message": "Scan QR code with WhatsApp to connect"
}
```

**Business Logic:**

1. Check user owns the bot
2. Check bot doesn't already have WhatsApp instance (one per bot)
3. Generate unique instance name: `bot_{bot_id}_{random_4_chars}`
4. Call Evolution API to create instance
5. Get QR code from Evolution API
6. Store in database
7. Return QR code to user

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
@router.post("/webhooks/whatsapp/evolution")
async def evolution_webhook(
    webhook_data: EvolutionWebhookSchema,
    x_api_key: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive webhooks from Evolution API

    Events:
    - messages.upsert: New message received
    - messages.update: Message status changed
    - connection.update: Connection status changed
    """

    # Validate API key
    if x_api_key != settings.EVOLUTION_WEBHOOK_SECRET:
        raise HTTPException(401, "Invalid API key")

    # Get instance by name
    instance = await get_instance_by_name(webhook_data.instance)
    if not instance:
        return {"status": "ignored", "reason": "instance_not_found"}

    if webhook_data.event == "messages.upsert":
        # Queue inbound message for processing
        await process_whatsapp_message.delay(
            instance_id=str(instance.id),
            message_data=webhook_data.data
        )
        return {"status": "queued"}

    elif webhook_data.event == "connection.update":
        # Update instance connection status
        new_status = map_connection_status(webhook_data.data.state)
        await update_instance_status(instance.id, new_status)
        return {"status": "updated"}

    return {"status": "ok"}
```

---

## ⚙️ Celery Tasks (Add to Bot Builder)

### Task 1: Process Inbound WhatsApp Message

```python
# app/tasks/whatsapp_tasks.py

from celery import Celery
from app.config import settings

celery_app = Celery(
    "bot_builder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task(bind=True, max_retries=3)
async def process_whatsapp_message(
    self,
    instance_id: str,
    message_data: dict
):
    """
    Process incoming WhatsApp message

    Steps:
    1. Extract phone number and message text
    2. Save to whatsapp_messages table
    3. Call Bot Builder's existing webhook (process_bot_message)
    4. Queue response for sending
    """
    try:
        # Extract data
        remote_jid = message_data["key"]["remoteJid"]
        phone = extract_phone_from_jid(remote_jid)  # "254712345678"
        formatted_phone = f"+{phone}"

        text_content = message_data["message"].get("conversation", "")
        message_id = message_data["key"]["id"]

        # Get instance
        instance = await get_instance_by_id(instance_id)

        # Save to messages table
        msg_record = await WhatsAppMessage.create(
            instance_id=instance_id,
            bot_id=instance.bot_id,
            direction="inbound",
            phone_number=formatted_phone,
            message_text=text_content,
            evolution_message_id=message_id,
            status="processing"
        )

        # Process through conversation engine
        from app.core.conversation_engine import ConversationEngine

        engine = ConversationEngine(db)
        result = await engine.process_message(
            channel="whatsapp",
            channel_user_id=formatted_phone,
            bot_id=instance.bot_id,
            message=text_content
        )

        # Update message record
        await msg_record.update(
            status="sent",
            session_id=result.get("session_id"),
            processed_at=datetime.utcnow()
        )

        # Queue response if present
        response_text = "\n\n".join(result.get("messages", []))
        if response_text:
            await send_whatsapp_message.delay(
                instance_id=instance_id,
                phone_number=formatted_phone,
                message_text=response_text,
                remote_jid=remote_jid
            )

    except Exception as exc:
        await msg_record.update(
            status="failed",
            error_message=str(exc),
            retry_count=msg_record.retry_count + 1
        )

        if msg_record.retry_count < 3:
            raise self.retry(exc=exc, countdown=60)
        raise
```

### Task 2: Send Outbound WhatsApp Message

```python
@celery_app.task(bind=True, max_retries=3)
async def send_whatsapp_message(
    self,
    instance_id: str,
    phone_number: str,
    message_text: str,
    remote_jid: str
):
    """
    Send message via Evolution API
    """
    try:
        instance = await get_instance_by_id(instance_id)

        # Save to messages table
        msg_record = await WhatsAppMessage.create(
            instance_id=instance_id,
            bot_id=instance.bot_id,
            direction="outbound",
            phone_number=phone_number,
            message_text=message_text,
            status="processing"
        )

        # Send via Evolution API
        phone_clean = phone_number.replace("+", "")
        response = await evolution_client.send_text(
            instance_name=instance.instance_name,
            phone=phone_clean,
            text=message_text
        )

        # Update record
        await msg_record.update(
            status="sent",
            evolution_message_id=response["key"]["id"],
            processed_at=datetime.utcnow()
        )

    except Exception as exc:
        await msg_record.update(
            status="failed",
            error_message=str(exc),
            retry_count=msg_record.retry_count + 1
        )

        if msg_record.retry_count < 3:
            raise self.retry(exc=exc, countdown=30)
        raise
```

---

## 🔧 Evolution API Client

```python
# app/services/evolution_api_client.py

import httpx
from app.config import settings

class EvolutionAPIClient:
    """Client for Evolution API operations"""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)

    async def create_instance(self, instance_name: str) -> dict:
        """Create new WhatsApp instance"""
        response = await self.client.post(
            f"{self.base_url}/instance/create",
            json={
                "instanceName": instance_name,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            },
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()

    async def get_qr_code(self, instance_name: str) -> dict:
        """Get QR code for instance connection"""
        response = await self.client.get(
            f"{self.base_url}/instance/connect/{instance_name}",
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()

    async def set_webhook(self, instance_name: str) -> dict:
        """Configure webhook for instance"""
        webhook_url = f"{settings.PUBLIC_URL}/webhooks/whatsapp/evolution"

        response = await self.client.post(
            f"{self.base_url}/webhook/set/{instance_name}",
            json={
                "url": webhook_url,
                "webhook_by_events": True,
                "webhook_base64": False,
                "events": [
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "CONNECTION_UPDATE"
                ]
            },
            headers={"apikey": self.api_key}
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
        response = await self.client.post(
            f"{self.base_url}/message/sendText/{instance_name}",
            json={
                "number": phone,
                "text": text
            },
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()

    async def logout_instance(self, instance_name: str) -> dict:
        """Logout WhatsApp instance"""
        response = await self.client.delete(
            f"{self.base_url}/instance/logout/{instance_name}",
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()

    async def get_connection_state(self, instance_name: str) -> dict:
        """Get instance connection status"""
        response = await self.client.get(
            f"{self.base_url}/instance/connectionState/{instance_name}",
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()

# Singleton instance
evolution_client = EvolutionAPIClient()
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

- [ ] Add Evolution API config to [`app/config.py`](app/config.py:1)
- [ ] Implement [`EvolutionAPIClient`](app/services/evolution_api_client.py) class
- [ ] Add Evolution API to [`requirements.txt`](requirements.txt:1)
- [ ] Deploy Evolution API container (docker-compose)

### Phase 3: API Endpoints (Week 2)

- [ ] Create [`app/api/whatsapp.py`](app/api/whatsapp.py) router
- [ ] Implement `POST /bots/{bot_id}/whatsapp/instances`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances/{id}/qr`
- [ ] Implement `GET /bots/{bot_id}/whatsapp/instances/{id}/status`
- [ ] Implement `PATCH /bots/{bot_id}/whatsapp/instances/{id}`
- [ ] Implement `DELETE /bots/{bot_id}/whatsapp/instances/{id}`
- [ ] Register router in [`app/main.py`](app/main.py:1)

### Phase 4: Webhooks & Celery (Week 2-3)

- [ ] Create [`app/tasks/whatsapp_tasks.py`](app/tasks/whatsapp_tasks.py)
- [ ] Implement `process_whatsapp_message` Celery task
- [ ] Implement `send_whatsapp_message` Celery task
- [ ] Add webhook endpoint `POST /webhooks/whatsapp/evolution`
- [ ] Configure Celery in Bot Builder
- [ ] Update [`docker-compose.yml`](docker-compose.yml:1) with Celery workers

### Phase 5: Testing & Polish (Week 3-4)

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

```bash
# Evolution API Configuration
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=your-evolution-api-key-here
EVOLUTION_WEBHOOK_SECRET=your-webhook-secret-here

# Public URL for webhooks (ngrok, domain, etc.)
PUBLIC_URL=https://your-domain.com

# Celery (already exists, ensure configured)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Docker Compose Updates

```yaml
# Add to docker-compose.yml

services:
  # Existing services...

  evolution-api:
    image: atendai/evolution-api:latest
    container_name: evolution-api
    ports:
      - "8080:8080"
    environment:
      - SERVER_URL=${PUBLIC_URL}
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_CONNECTION_URI=postgresql://botbuilder:password@postgres:5432/evolution
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis:6379/1
    networks:
      - app_network
    restart: unless-stopped

  celery-worker:
    build: .
    container_name: bot-builder-celery
    command: celery -A app.tasks.celery_app worker -l info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - EVOLUTION_API_URL=${EVOLUTION_API_URL}
      - EVOLUTION_API_KEY=${EVOLUTION_API_KEY}
    depends_on:
      - postgres
      - redis
    networks:
      - app_network
    restart: unless-stopped
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
       ├─> Celery queues message
       │
       └─> Celery worker processes
           │
           ├─> Finds WhatsApp instance
           │
           ├─> Extracts phone number & text
           │
           └─> Calls conversation engine
               │
               ├─> Engine processes flow
               │
               └─> Returns response text
                   │
                   ├─> Queue outbound message
                   │
                   └─> Celery sends via Evolution API
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
- [ ] Evolution API container running
- [ ] Celery worker running
- [ ] Redis accessible
- [ ] Check [`whatsapp_messages`](whatsapp_messages) table for errors

### Issue 3: Bot Not Responding

**Debug Steps**:

1. Check message reached Celery: `SELECT * FROM whatsapp_messages WHERE status='failed'`
2. Check bot has active flows with trigger keywords
3. Check Bot Builder logs for conversation engine errors
4. Verify webhook secret matches in Evolution API

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

- ✅ **Lean**: Adds WhatsApp to Bot Builder without separate services
- ✅ **User-Friendly**: Self-service instance creation and management
- ✅ **Scalable**: Async processing with Celery ensures performance
- ✅ **Maintainable**: Clean separation with Evolution API client
- ✅ **Production-Ready**: Error handling, retries, logging included

**Total Implementation Time**: 3-4 weeks for core team

**Files to Create/Modify**:

- New: 6 files (models, API, tasks, client)
- Modify: 4 files (main.py, config.py, docker-compose.yml, requirements.txt)
- Database: 2 new tables

Ready to implement! 🚀
