# Bot Builder

A self-hosted platform for building and running conversational bots over WhatsApp and other messaging channels.

Conversational bots that collect information, answer questions, or guide users through multi-step processes typically require writing and maintaining a lot of state management, routing logic, and integration code. Bot Builder replaces that with a visual flow editor where you design the conversation as a graph of connected nodes, and a backend engine that executes it — handling sessions, input validation, external API calls, and message delivery.

## Features

- **Visual flow editor** — drag-and-drop canvas with 6 node types (Text, Prompt, Menu, API Action, Logic, Set Variable), conditional routing, and a built-in chat simulator for testing flows before deployment
- **WhatsApp integration** — connect a WhatsApp number via the bundled Evolution API; scan a QR code from the dashboard and your bot is live
- **Conversation engine** — manages session state, input validation, template rendering, retry logic, and auto-progression through non-input nodes, so flows run without manual intervention
- **External API integration** — API Action nodes can call any HTTP endpoint, map response data into flow variables, and branch on success/failure, letting bots interact with external systems mid-conversation
- **Multi-tenant with security** — user isolation at the database level, httpOnly cookie auth, PII encryption, rate limiting, SSRF protection, and audit logging

## How It Works

1. Create a bot — you get a webhook URL and secret
2. Build a flow — add nodes, connect them with routes, set trigger keywords (e.g. "HELLO", "START")
3. Connect a channel — WhatsApp via QR code, or any platform via the webhook API
4. When a user sends a message matching a trigger keyword, the engine executes the flow — sending messages, collecting input, calling APIs, branching on conditions — until the conversation ends or the session times out

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
