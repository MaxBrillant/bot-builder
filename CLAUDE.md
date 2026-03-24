# CLAUDE.md

Bot Builder is a multi-tenant conversational bot framework. FastAPI backend, React/TypeScript frontend. Users build conversation flows visually using 6 node types; bots receive messages via webhooks and execute flows.

For architecture details see `docs/project/architecture.md`.

## Key Paths (Backend)

| Path | Purpose |
|------|---------|
| `backend/v1/app/core/engine.py` | Main conversation orchestration |
| `backend/v1/app/core/session_manager.py` | Session lifecycle |
| `backend/v1/app/core/validators.py` | Input validation (1500+ lines — needs splitting) |
| `backend/v1/app/core/conditions.py` | Route evaluation |
| `backend/v1/app/core/template_engine.py` | Variable substitution |
| `backend/v1/app/core/redis_manager.py` | Redis integration (1000+ lines — needs splitting) |
| `backend/v1/app/models/node_configs.py` | Node config models (1000+ lines — needs splitting) |
| `backend/v1/app/processors/` | One file per node type |
| `backend/v1/BOT_BUILDER_SPECIFICATIONS.md` | Authoritative system spec |

## Dev Commands

```bash
cd backend/v1
source venv/bin/activate
uvicorn app.main:app --reload        # run server
pytest                               # run tests
pytest --cov=app tests/              # with coverage
alembic upgrade head                 # apply migrations
alembic revision --autogenerate -m "description"  # create migration
```

## Critical Constraints

- **Redis is mandatory** — not optional. App fails to start without it.
- **Session timeout**: 30 min absolute (not sliding)
- **Max auto-progression**: 10 consecutive non-input nodes before error
- **Max nodes per flow**: 48
- **Template syntax**: `{{variable_name}}` only — bare name, no prefix. `{{context.x}}` renders literally (broken). `{{user.channel_id}}` only works in API_ACTION nodes.
- **Webhook secret**: validated on every inbound message — never skip
- **API keys in flows**: never store in flow JSON — use env vars

## Git Commit Conventions

Format: `type: brief description`
Types: `feat`, `fix`, `refactor`, `docs`, `chore`
No body, no Co-Authored-By, no trailing punctuation. Match existing log style.
