# Evolution API v2 - Complete Documentation Reference

## 1. Docker Installation

### Prerequisites
- Docker installed
- PostgreSQL and Redis configured

### Standalone Docker Compose Configuration

```yaml
version: '3.9'
services:
  evolution-api:
    container_name: evolution_api
    image: atendai/evolution-api:v2.1.1
    restart: always
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - evolution_instances:/evolution/instances

volumes:
  evolution_instances:
```

Minimal `.env`:
```
AUTHENTICATION_API_KEY=change-me
```

### Commands
```bash
# Start
docker compose up -d

# Check logs
docker logs evolution_api

# Stop
docker compose down

# Access: http://localhost:8080
```

---

## 2. Database Configuration

### Environment Variables
```bash
DATABASE_ENABLED=true
DATABASE_PROVIDER=postgresql
DATABASE_CONNECTION_URI='postgresql://user:pass@localhost:5432/evolution?schema=public'
DATABASE_CONNECTION_CLIENT_NAME=evolution_exchange
DATABASE_SAVE_DATA_INSTANCE=true
DATABASE_SAVE_DATA_NEW_MESSAGE=true
DATABASE_SAVE_MESSAGE_UPDATE=true
DATABASE_SAVE_DATA_CONTACTS=true
DATABASE_SAVE_DATA_CHATS=true
DATABASE_SAVE_DATA_LABELS=true
DATABASE_SAVE_DATA_HISTORIC=true
```

---

## 3. Redis Configuration

### Environment Variables
```bash
CACHE_REDIS_ENABLED=true
CACHE_REDIS_URI=redis://localhost:6379/6
CACHE_REDIS_PREFIX_KEY=evolution
CACHE_REDIS_SAVE_INSTANCES=false
CACHE_LOCAL_ENABLED=false
```

---

## 4. Environment Variables

### Server
```bash
SERVER_TYPE=http
SERVER_PORT=8080
SERVER_URL=https://example.evolution-api.com
```

### CORS
```bash
CORS_ORIGIN=*
CORS_METHODS=GET,POST,PUT,DELETE
CORS_CREDENTIALS=true
```

### Logging
```bash
LOG_LEVEL=ERROR,WARN,DEBUG,INFO,LOG,VERBOSE,DARK,WEBHOOKS
LOG_COLOR=true
LOG_BAILEYS=error
```

### Instances
```bash
DEL_INSTANCE=false
```

### Session
```bash
CONFIG_SESSION_PHONE_CLIENT=Evolution API
CONFIG_SESSION_PHONE_NAME=Chrome
```

### QR Code
```bash
QRCODE_LIMIT=30
QRCODE_COLOR=#175197
```

### Authentication
```bash
AUTHENTICATION_API_KEY=429683C4C977415CAAFCCE10F7D57E11
AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true
```

### Language
```bash
LANGUAGE=en
```

### Global Webhook
```bash
WEBHOOK_GLOBAL_ENABLED=false
WEBHOOK_GLOBAL_URL=https://webhook.example.com
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false
```

### Webhook Events (true/false)
```bash
WEBHOOK_EVENTS_APPLICATION_STARTUP=false
WEBHOOK_EVENTS_QRCODE_UPDATED=true
WEBHOOK_EVENTS_MESSAGES_SET=false
WEBHOOK_EVENTS_MESSAGES_UPSERT=true
WEBHOOK_EVENTS_MESSAGES_EDITED=false
WEBHOOK_EVENTS_MESSAGES_UPDATE=true
WEBHOOK_EVENTS_MESSAGES_DELETE=true
WEBHOOK_EVENTS_SEND_MESSAGE=false
WEBHOOK_EVENTS_CONTACTS_SET=false
WEBHOOK_EVENTS_CONTACTS_UPSERT=false
WEBHOOK_EVENTS_CONTACTS_UPDATE=false
WEBHOOK_EVENTS_PRESENCE_UPDATE=false
WEBHOOK_EVENTS_CHATS_SET=false
WEBHOOK_EVENTS_CHATS_UPSERT=false
WEBHOOK_EVENTS_CHATS_UPDATE=false
WEBHOOK_EVENTS_CHATS_DELETE=false
WEBHOOK_EVENTS_GROUPS_UPSERT=false
WEBHOOK_EVENTS_GROUPS_UPDATE=false
WEBHOOK_EVENTS_GROUP_PARTICIPANTS_UPDATE=false
WEBHOOK_EVENTS_CONNECTION_UPDATE=true
WEBHOOK_EVENTS_LABELS_EDIT=false
WEBHOOK_EVENTS_LABELS_ASSOCIATION=false
WEBHOOK_EVENTS_CALL=false
WEBHOOK_EVENTS_TYPEBOT_START=false
WEBHOOK_EVENTS_TYPEBOT_CHANGE_STATUS=false
WEBHOOK_EVENTS_ERRORS=false
WEBHOOK_EVENTS_ERRORS_WEBHOOK=false
```

---

## 5. Webhooks

### Instance Webhook Setup
**Endpoint:** `POST /webhook/instance`

```json
{
  "url": "https://your-webhook-url.com",
  "webhook_by_events": false,
  "webhook_base64": false,
  "events": [
    "QRCODE_UPDATED",
    "MESSAGES_UPSERT",
    "MESSAGES_UPDATE",
    "MESSAGES_DELETE",
    "SEND_MESSAGE",
    "CONNECTION_UPDATE",
    "TYPEBOT_START",
    "TYPEBOT_CHANGE_STATUS"
  ]
}
```

### Supported Events
- `APPLICATION_STARTUP` - Application startup notification
- `QRCODE_UPDATED` - QR code in base64
- `CONNECTION_UPDATE` - WhatsApp connection status
- `MESSAGES_SET` - Initial message load
- `MESSAGES_UPSERT` - New message received
- `MESSAGES_UPDATE` - Message updated
- `MESSAGES_DELETE` - Message deleted
- `SEND_MESSAGE` - Message sent
- `CONTACTS_SET` - Initial contacts load
- `CONTACTS_UPSERT` - Contacts reload
- `CONTACTS_UPDATE` - Contact updated
- `PRESENCE_UPDATE` - User online/typing/recording status
- `CHATS_SET` - Chats loaded
- `CHATS_UPDATE` - Chat updated
- `CHATS_UPSERT` - New chat info
- `CHATS_DELETE` - Chat deleted
- `GROUPS_UPSERT` - Group created
- `GROUPS_UPDATE` - Group updated
- `GROUP_PARTICIPANTS_UPDATE` - Group participant action
- `NEW_TOKEN` - JWT token updated

### Webhook by Events
When `webhook_by_events: true`, event name appended to URL:
```
Base URL: https://sub.domain.com/webhook/
Event: MESSAGES_UPSERT
Result: https://sub.domain.com/webhook/messages-upsert
```

### Locate Webhook
**Endpoint:** `GET /webhook/find/[instance]`

---

## 6. WebSocket

### Enable WebSocket
```bash
WEBSOCKET_ENABLED=true
WEBSOCKET_GLOBAL_EVENTS=false  # true for global mode
```

### Connection URLs

**Global Mode:**
```javascript
wss://api.yoursite.com
```

**Traditional Mode:**
```javascript
wss://api.yoursite.com/instance_name
```

### Example Connection
```javascript
const socket = io('wss://api.yoursite.com/instance_name', {
  transports: ['websocket']
});

socket.on('connect', () => {
  console.log('Connected to Evolution API WebSocket');
});

socket.on('event_name', (data) => {
  console.log('Event received:', data);
});

socket.on('disconnect', () => {
  console.log('Disconnected');
});

// Close connection
socket.disconnect();
```

---

## 7. Instance Management API

### Authentication
All instance endpoints require API key authentication via header:
```
apikey: YOUR_API_KEY
```

### Create Instance
**Endpoint:** `POST /instance/create`

**Body:**
```json
{
    "instanceName": "my_instance",
    "token": "custom_token",  // Optional - leave empty to auto-generate
    "number": "559999999999",  // Optional - recipient number with country code
    "qrcode": true,  // Optional - generate QR code
    "integration": "WHATSAPP-BAILEYS",  // WHATSAPP-BAILEYS | WHATSAPP-BUSINESS | EVOLUTION

    // Settings (Optional)
    "rejectCall": false,
    "msgCall": "",
    "groupsIgnore": false,
    "alwaysOnline": false,
    "readMessages": false,
    "readStatus": false,
    "syncFullHistory": false,

    // Proxy (Optional)
    "proxyHost": "",
    "proxyPort": "",
    "proxyProtocol": "",
    "proxyUsername": "",
    "proxyPassword": "",

    // Webhook (Optional)
    "webhook": {
        "url": "https://your-webhook-url.com",
        "byEvents": false,
        "base64": true,
        "headers": {
            "authorization": "Bearer TOKEN",
            "Content-Type": "application/json"
        },
        "events": [
            "APPLICATION_STARTUP",
            "QRCODE_UPDATED",
            "MESSAGES_SET",
            "MESSAGES_UPSERT",
            "MESSAGES_UPDATE",
            "MESSAGES_DELETE",
            "SEND_MESSAGE",
            "CONTACTS_SET",
            "CONTACTS_UPSERT",
            "CONTACTS_UPDATE",
            "PRESENCE_UPDATE",
            "CHATS_SET",
            "CHATS_UPSERT",
            "CHATS_UPDATE",
            "CHATS_DELETE",
            "GROUPS_UPSERT",
            "GROUP_UPDATE",
            "GROUP_PARTICIPANTS_UPDATE",
            "CONNECTION_UPDATE",
            "LABELS_EDIT",
            "LABELS_ASSOCIATION",
            "CALL",
            "TYPEBOT_START",
            "TYPEBOT_CHANGE_STATUS"
        ]
    },

    // RabbitMQ (Optional)
    "rabbitmq": {
        "enabled": true,
        "events": [/* Same events as webhook */]
    },

    // SQS (Optional)
    "sqs": {
        "enabled": true,
        "events": [/* Same events as webhook */]
    },

    // Chatwoot (Optional)
    "chatwootAccountId": "1",
    "chatwootToken": "TOKEN",
    "chatwootUrl": "https://chatwoot.com",
    "chatwootSignMsg": true,
    "chatwootReopenConversation": true,
    "chatwootConversationPending": false,
    "chatwootImportContacts": true,
    "chatwootNameInbox": "evolution",
    "chatwootMergeBrazilContacts": true,
    "chatwootImportMessages": true,
    "chatwootDaysLimitImportMessages": 3,
    "chatwootOrganization": "Evolution Bot",
    "chatwootLogo": "https://evolution-api.com/files/evolution-api-favicon.png"
}
```

### Fetch Instances
**Endpoint:** `GET /instance/fetchInstances`

**Query Params:**
- `instanceName` (optional) - Filter by instance name
- `instanceId` (optional) - Filter by instance ID

**Headers:**
```
apikey: YOUR_INSTANCE_TOKEN or GLOBAL_API_KEY
```

### Connect Instance
**Endpoint:** `GET /instance/connect/{instanceName}`

**Query Params:**
- `number` (optional) - Recipient number with country code

Generates QR code for WhatsApp connection.

### Restart Instance
**Endpoint:** `POST /instance/restart/{instanceName}`

Restarts the WhatsApp connection for the instance.

### Set Presence
**Endpoint:** `POST /instance/setPresence/{instanceName}`

**Body:**
```json
{
    "presence": "available"  // available | unavailable
}
```

Sets the online/offline status for the instance.

### Connection Status
**Endpoint:** `GET /instance/connectionState/{instanceName}`

Returns the current connection state of the instance.

**Response:**
```json
{
    "instance": "my_instance",
    "state": "open"  // open | close | connecting
}
```

### Logout Instance
**Endpoint:** `DELETE /instance/logout/{instanceName}`

Logs out the instance from WhatsApp (disconnects but keeps instance data).

### Delete Instance
**Endpoint:** `DELETE /instance/delete/{instanceName}`

**Headers:**
```
apikey: GLOBAL_API_KEY
```

Permanently deletes the instance and all its data.

---

## Key Differences from v1.8.7

### Breaking Changes
1. **Image repository:** `atendai/evolution-api` (same, but versions differ)
2. **PostgreSQL/MySQL support:** Now natively supported (v1 only had MongoDB)
3. **Environment variables:** Many renamed or restructured
4. **Database schema:** Uses Prisma ORM
5. **Webhook format:** May have payload changes
6. **Health check endpoint:** `/health` instead of `/`

### New Features in v2.x
- WhatsApp Business Meta Templates
- Enhanced Events API with sync progress
- Better N8N and WebSocket support
- Pix button messages
- Improved proxy and media upload
- Better Chatwoot and Baileys integrations

---

## Migration Notes

### Data Migration
- Fresh start recommended (v1 → v2 data not directly compatible)
- Re-scan QR codes for instances
- Reconfigure webhooks

### Database Setup
- Create new database or schema for v2
- Prisma will auto-migrate on first start
- Can coexist with v1 using different databases

### Configuration Changes
- Review all environment variables
- Update webhook URLs if needed
- Test thoroughly before production deployment
