# Bot Builder v1.0

Multi-tenant conversational bot framework. FastAPI backend, PostgreSQL, Redis (mandatory). Users build conversation flows with 6 node types; bots receive messages via webhooks and execute flows.

## Quick Start (Local)

```bash
cd backend/v1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # edit with your values
alembic upgrade head
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Swagger UI at `/docs` (debug mode only).

## Quick Start (Docker)

```bash
cd backend/v1
cp .env.example .env    # edit with production values
docker compose up -d
```

Migrations run automatically on container startup. See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for full production setup.

## Project Structure

```
v1/
├── app/
│   ├── main.py                  # FastAPI application + lifespan
│   ├── config.py                # Pydantic settings (nested env vars)
│   ├── database.py              # Async SQLAlchemy setup
│   ├── dependencies.py          # FastAPI dependencies
│   │
│   ├── api/                     # Route handlers
│   │   ├── auth.py              # Register, login, logout, profile
│   │   ├── bots.py              # Bot CRUD + activate/deactivate
│   │   ├── flows.py             # Flow CRUD (nested under /bots/{bot_id}/flows)
│   │   ├── oauth.py             # Google OAuth2
│   │   ├── whatsapp.py          # WhatsApp instance management
│   │   ├── evolution_proxy.py   # Evolution API proxy
│   │   ├── middleware.py        # Exception handlers, security headers
│   │   └── webhooks/            # Inbound message handlers
│   │       ├── core.py          # Platform-agnostic webhook
│   │       ├── whatsapp.py      # WhatsApp/Evolution webhooks
│   │       └── sanitization.py  # Input sanitization
│   │
│   ├── core/                    # Business logic
│   │   ├── engine.py            # Conversation orchestration (~800 lines)
│   │   ├── session_manager.py   # Session lifecycle
│   │   ├── conditions.py        # Route condition evaluation
│   │   ├── template_engine.py   # {{variable}} substitution
│   │   ├── input_validator.py   # REGEX/EXPRESSION validation
│   │   ├── flow_validator.py    # Flow definition validation
│   │   ├── redis_manager.py     # Redis connection + operations
│   │   └── circuit_breaker.py   # External call protection
│   │
│   ├── processors/              # One per node type
│   │   ├── base_processor.py
│   │   ├── text_processor.py
│   │   ├── prompt_processor.py
│   │   ├── menu_processor.py
│   │   ├── api_action_processor.py
│   │   ├── logic_processor.py
│   │   ├── set_variable_processor.py
│   │   ├── retry_handler.py
│   │   └── factory.py
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py
│   │   ├── bot.py
│   │   ├── flow.py
│   │   ├── session.py
│   │   ├── audit_log.py
│   │   ├── bot_integration.py
│   │   └── node_configs.py      # Pydantic models for node configs
│   │
│   ├── schemas/                 # API request/response schemas
│   │   ├── auth_schema.py
│   │   ├── bot_schema.py
│   │   ├── flow_schema.py
│   │   ├── webhook_schema.py
│   │   ├── whatsapp_schema.py
│   │   └── evolution_webhook_schema.py
│   │
│   ├── services/                # Business services
│   │   ├── bot_service.py
│   │   ├── flow_service.py
│   │   ├── evolution_service.py
│   │   └── integrations/        # WhatsApp integration layer
│   │
│   ├── repositories/            # Data access layer
│   │   ├── base.py
│   │   ├── user_repository.py
│   │   ├── bot_repository.py
│   │   ├── flow_repository.py
│   │   ├── session_repository.py
│   │   ├── audit_log_repository.py
│   │   └── bot_integration_repository.py
│   │
│   └── utils/
│       ├── constants/           # Enums, constraints, patterns
│       ├── security/            # Password hashing, sanitization, SSRF protection
│       ├── exceptions.py        # Exception hierarchy
│       ├── logger.py            # Structured logging
│       ├── responses.py         # Standard error responses
│       ├── encryption.py        # Fernet PII encryption
│       ├── shared.py            # Path resolution, type conversion
│       └── example_flows.py     # Sample flow definitions
│
├── alembic/                     # Database migrations
├── docs/                        # System documentation
├── docker-compose.yml
├── Dockerfile
├── Caddyfile
├── entrypoint.sh
├── prometheus.yml
├── requirements.txt
├── .env.example
└── .dockerignore
```

## Configuration

Environment variables use nested structure with `__` delimiter. See `.env.example` for all options.

```bash
DATABASE__URL=postgresql+asyncpg://...
REDIS__URL=redis://...
SECURITY__SECRET_KEY=...
SECURITY__ENCRYPTION_KEY=...
```

## Documentation

Detailed system docs are in [`docs/`](docs/):

- [Architecture](docs/architecture.md) — system overview, request flow, component roles
- [Nodes](docs/nodes/overview.md) — all 6 node types, configs, processing behavior
- [Routing](docs/routing/conditions.md) — condition evaluation, route sorting
- [Templates](docs/templates.md) — variable substitution syntax and resolution
- [Sessions](docs/sessions.md) — session lifecycle, timeouts, state management
- [Validation](docs/validation.md) — input validation and flow validation
- [Error Handling](docs/error-handling.md) — exception hierarchy, error responses
- [Security](docs/security.md) — auth, encryption, rate limiting, SSRF protection
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) — production setup, CI/CD, monitoring
