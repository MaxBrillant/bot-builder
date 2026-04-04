# Bot Builder

Bot Builder is a platform for creating conversational bots. You design conversation flows visually in a drag-and-drop editor, connect them to messaging channels like WhatsApp, and your bot handles conversations automatically.

## What It Does

**Build flows visually** — drag nodes onto a canvas, connect them with routes, and configure each step. Some steps involve writing expressions (conditions, validation rules, API configs).

**6 node types** cover common conversation patterns:
- **Text** — send a message
- **Prompt** — ask for input with validation (regex or expressions)
- **Menu** — present choices (static list or fetched from an API)
- **API Action** — call an external HTTP API and use the response
- **Logic** — branch the conversation based on conditions
- **Set Variable** — assign values to flow variables (supports template substitution)

**Connect to WhatsApp** — link your bot to a WhatsApp number through the built-in Evolution API integration. Scan a QR code from the dashboard and you're live.

**Webhook API** — for other channels, send messages to your bot's webhook endpoint and get responses back. Any platform that can make HTTP requests can integrate.

**Multi-tenant** — each user has their own bots, flows, and data, fully isolated.

## How It Works

1. Sign up and create a bot — you get a webhook URL and secret
2. Build a flow — add nodes, connect them, set trigger keywords (e.g. "HELLO", "START")
3. Activate the bot and connect a channel (WhatsApp or custom webhook)
4. When a user sends a message matching a trigger keyword, the bot executes the flow — sending messages, collecting input, calling APIs, branching on conditions — until the conversation ends or times out (30 minutes)

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Redis |
| Frontend | React 19, TypeScript, Vite, React Flow, Tailwind CSS |
| Infrastructure | Docker Compose, Caddy (reverse proxy + auto-HTTPS), Prometheus, Grafana |
| WhatsApp | Evolution API (self-hosted, included in Docker Compose) |
| CI/CD | GitHub Actions — auto-deploys on push to main |

## Running Locally

### Prerequisites

- Python 3.11+, Node 20+
- PostgreSQL 15+, Redis 5.0+

### Backend

```bash
cd backend/v1
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # edit with your database, redis, and security keys
alembic upgrade head
uvicorn app.main:app --reload
```

API at `http://localhost:8000`. Swagger docs at `/docs` (debug mode only).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI at `http://localhost:5173`.

### Docker (full stack)

```bash
cd backend/v1
cp .env.example .env    # configure all values
docker compose up -d
```

This starts everything: API, frontend, PostgreSQL, Redis, Caddy, Evolution API, Prometheus, and Grafana.

## Project Structure

```
bot-builder/
├── backend/v1/          # API server, conversation engine, all business logic
│   ├── app/             # FastAPI application
│   └── docs/            # System documentation
├── frontend/            # React dashboard and visual flow editor
└── .github/workflows/   # CI/CD pipeline
```

## Documentation

Detailed docs live in [`backend/v1/docs/`](backend/v1/docs/):

- [Architecture](backend/v1/docs/architecture.md) — system overview, request flow, component roles
- [Nodes](backend/v1/docs/nodes/overview.md) — all 6 node types, configs, processing behavior
- [Routing](backend/v1/docs/routing/conditions.md) — condition evaluation and route sorting
- [Templates](backend/v1/docs/templates.md) — `{{variable}}` substitution syntax
- [Sessions](backend/v1/docs/sessions.md) — session lifecycle and state management
- [Validation](backend/v1/docs/validation.md) — input and flow validation rules
- [Error Handling](backend/v1/docs/error-handling.md) — exception hierarchy and error responses
- [Security](backend/v1/docs/security.md) — auth, encryption, rate limiting
- [Deployment](backend/v1/docs/DEPLOYMENT_GUIDE.md) — production setup, Docker, CI/CD, monitoring

See also: [Backend README](backend/v1/README.md) | [Frontend README](frontend/README.md)
