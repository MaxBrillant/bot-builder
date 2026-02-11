# Bot Builder v1.0

A production-ready conversational bot framework with multi-tenant support, built with FastAPI and PostgreSQL.

## 🚀 Features

### Core Capabilities

- **6 Node Types**: PROMPT, MENU, API_ACTION, LOGIC_EXPRESSION, TEXT, END
- **Multi-Tenant**: Complete user isolation with database-level security
- **Template System**: Variable substitution with `{{variable}}` syntax
- **Validation**: REGEX and EXPRESSION-based input validation
- **Session Management**: 30-minute absolute timeout with state persistence
- **Flow Validation**: Comprehensive validation on submission
- **Auto-Progression**: Track consecutive nodes without user input (max 10)
- **API Integration**: HTTP requests with 30-second timeout and JSON response handling

### Security

- JWT-based authentication
- Password hashing with bcrypt
- Flow ownership enforcement
- Input sanitization
- Audit logging with PII masking

### Architecture

- Async-first design with SQLAlchemy 2.0
- PostgreSQL with JSONB support
- FastAPI with automatic OpenAPI documentation
- Docker deployment ready

## 📋 Requirements

- Python 3.11+
- PostgreSQL 15+
- Redis 5.0+ (required for production - caching, rate limiting, trigger keywords)
- Docker & Docker Compose (for containerized deployment)

## 🛠️ Installation

### Local Development

1. **Clone the repository**

```bash
cd v1
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**

```bash
# Create PostgreSQL database
createdb botbuilder

# Run migrations (if using Alembic)
alembic upgrade head
```

6. **Run application**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Configure environment**

```bash
cp .env.example .env
# Edit .env with production values
```

2. **Build and start services**

```bash
docker-compose up -d
```

**Note:** Database migrations run automatically on container startup. The entrypoint script will:

- Wait for PostgreSQL to be ready (up to 60 seconds)
- Run Alembic migrations (`alembic upgrade head`)
- Start the application server

You can monitor the migration process in the logs:

```bash
docker-compose logs -f api
```

3. **Check health**

```bash
curl http://localhost:8000/health
```

4. **Verify migrations** (optional)

```bash
# Check that tables were created
docker-compose exec db psql -U botbuilder -d botbuilder -c "\dt"
```

## 📚 API Documentation

Once running, access the interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Quick Start API Examples

#### 1. Register User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

#### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

#### 3. Create Bot

```bash
curl -X POST http://localhost:8000/bots \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "My First Bot",
    "description": "A conversational bot for customer support"
  }'
```

Response includes `bot_id` and `webhook_secret` - save these!

#### 4. Create Flow for Bot

```bash
curl -X POST http://localhost:8000/bots/YOUR_BOT_ID/flows \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "flow_id": "user123_welcome_flow",
    "trigger_keywords": ["START", "HELLO"],
    "start_node_id": "node_welcome",
    "nodes": {
      "node_welcome": {
        "id": "node_welcome",
        "type": "TEXT",
        "config": {"text": "Welcome! 👋"},
        "routes": [{"condition": "true", "target_node": "node_end"}]
      },
      "node_end": {
        "id": "node_end",
        "type": "END",
        "config": {}
      }
    }
  }'
```

#### 5. Send Message via Webhook

```bash
curl -X POST http://localhost:8000/webhook/YOUR_BOT_ID \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_WEBHOOK_SECRET" \
  -d '{
    "channel": "whatsapp",
    "channel_user_id": "+254712345678",
    "message_text": "START"
  }'
```

## 🏗️ Project Structure

```
v1/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── database.py             # Database setup
│   ├── dependencies.py         # FastAPI dependencies
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── flow.py
│   │   └── session.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── auth_schema.py
│   │   ├── flow_schema.py
│   │   ├── session_schema.py
│   │   └── message_schema.py
│   │
│   ├── core/                   # Core business logic
│   │   ├── template_engine.py
│   │   ├── condition_evaluator.py
│   │   ├── validation_system.py
│   │   ├── flow_validator.py
│   │   ├── session_manager.py
│   │   └── conversation_engine.py
│   │
│   ├── processors/             # Node processors
│   │   ├── base_processor.py
│   │   ├── prompt_processor.py
│   │   ├── menu_processor.py
│   │   ├── api_action_processor.py
│   │   ├── logic_processor.py
│   │   ├── message_processor.py
│   │   └── end_processor.py
│   │
│   ├── api/                    # API routes
│   │   ├── auth.py
│   │   ├── flows.py
│   │   └── messages.py
│   │
│   └── utils/                  # Utilities
│       ├── constants.py
│       ├── exceptions.py
│       ├── logger.py
│       └── security.py
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://botbuilder:password@localhost:5432/botbuilder

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Application
ENVIRONMENT=development
DEBUG=True
SESSION_TIMEOUT_MINUTES=30
MAX_AUTO_PROGRESSION=10
```

### System Constraints

| Constraint           | Limit             | Reason              |
| -------------------- | ----------------- | ------------------- |
| Max nodes per flow   | 48                | Performance         |
| Max routes per node  | 8                 | Complexity          |
| Session timeout      | 30 min (absolute) | Resource management |
| API timeout          | 30 seconds        | Fixed               |
| Max auto-progression | 10 nodes          | Prevent loops       |

## 📖 Flow Development Guide

### Node Types

1. **PROMPT** - Collect user input with validation
2. **MENU** - Present options (static or dynamic)
3. **API_ACTION** - Call external APIs
4. **LOGIC_EXPRESSION** - Conditional routing
5. **TEXT** - Display information
6. **END** - Terminate conversation

### Example Flow

```json
{
  "flow_id": "user123_data_collection",
  "trigger_keywords": ["REGISTER"],
  "variables": {
    "name": { "type": "string", "default": null },
    "age": { "type": "integer", "default": 0 }
  },
  "start_node_id": "node_get_name",
  "nodes": {
    "node_get_name": {
      "id": "node_get_name",
      "type": "PROMPT",
      "config": {
        "text": "What's your name?",
        "save_to_variable": "name",
        "validation": {
          "type": "EXPRESSION",
          "rule": "input.isAlpha() && input.length >= 2",
          "error_message": "Name must be at least 2 letters"
        }
      },
      "routes": [{ "condition": "true", "target_node": "node_get_age" }]
    },
    "node_get_age": {
      "id": "node_get_age",
      "type": "PROMPT",
      "config": {
        "text": "How old are you?",
        "save_to_variable": "age",
        "validation": {
          "type": "EXPRESSION",
          "rule": "input.isNumeric() && input > 0",
          "error_message": "Please enter a valid age"
        }
      },
      "routes": [{ "condition": "true", "target_node": "node_confirm" }]
    },
    "node_confirm": {
      "id": "node_confirm",
      "type": "TEXT",
      "config": {
        "text": "Thanks {{context.name}}! You are {{context.age}} years old."
      },
      "routes": [{ "condition": "true", "target_node": "node_end" }]
    },
    "node_end": {
      "id": "node_end",
      "type": "END",
      "config": {}
    }
  }
}
```

## 🔒 Security Best Practices

1. **Never store API keys in flow JSON**

   - Use environment variables
   - Server-side credential injection

2. **Validate all user input**

   - Use REGEX or EXPRESSION validation
   - Appropriate for data type

3. **Use HTTPS in production**

   - All API endpoints
   - External API calls

4. **Regular security updates**
   - Keep dependencies updated
   - Monitor security advisories

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**

   ```bash
   # Check PostgreSQL is running
   pg_isready -h localhost -p 5432

   # Verify DATABASE_URL in .env
   ```

2. **Session Timeout Issues**

   ```bash
   # Sessions expire after 30 minutes (absolute)
   # This is by design and cannot be extended
   ```

3. **Flow Validation Errors**
   - Check all node IDs are unique
   - Verify all routes reference existing nodes
   - Ensure no circular references

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

```bash
# Docker logs
docker-compose logs -f api

# Local development
# Logs written to stdout
```

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest

# With coverage
pytest --cov=app tests/
```

## 📝 License

See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues and questions:

- GitHub Issues: [Create an issue](https://github.com/yourrepo/bot-builder/issues)
- Documentation: See `BOT_BUILDER_SPECIFICATIONS.md` for detailed specs

## 🎯 Roadmap

### v1.1 (Future)

- [ ] WebSocket support for real-time messaging
- [ ] Flow analytics dashboard
- [ ] A/B testing for flows
- [ ] Visual flow builder
- [ ] Multi-channel support (WhatsApp, Telegram)

---

**Built with ❤️ using FastAPI, PostgreSQL, and Python**
