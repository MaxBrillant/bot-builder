# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bot Builder is a conversational bot framework with a FastAPI backend and React/TypeScript frontend. The system supports multi-tenant bot creation with a visual flow editor for building conversation flows using 6 node types: PROMPT, MENU, API_ACTION, LOGIC_EXPRESSION, MESSAGE, and END.

## Code Guidelines & Working Principles

### Core Rules

**Rule 1: Always Ask Questions, Be Curious**
- Ask questions about non-trivial ambiguities, risks, and areas with multiple valid approaches
- Don't ask about tiny details or established patterns already clear in the codebase (this slows progress)
- Focus curiosity on things that matter: architectural decisions, unclear requirements, risky assumptions

**Rule 2: Don't Trust Your Intuition - Always Double Check**
- Read actual code/files before making changes or proposing ideas
- Verify against documentation
- Test through terminal when necessary
- Check even trivial things (function existence, exact parameter names, etc.)
- Verify existing code actually does what it claims before relying on it
- Clear all assumptions before proceeding
- Use intuition only for critiquing, novel ideas, or problem-solving, but always validate and verify the outcomes

**Rule 3: Clarity is Everything - No Assumptions**
- If 80-90% confident but there's any ambiguity, pause and ask for clarification
- Never assume what the user meant
- For vague instructions ("make this better", "improve performance", "fix bugs"), always stop and ask for specifics
- When asking for clarification, include suggestions based on your understanding of the problem

**Rule 4: Criticize Everything**
- Criticize new code you're writing
- Criticize existing code in the repository when you encounter it
- Criticize the user's requests and ideas when they seem suboptimal or problematic
- Point out both minor issues (naming, small refactors, code quality) and major ones (architecture, functionality)
- Be direct - say "that approach won't work because X" rather than softening with "there might be an issue"
- List all problems you identify, don't just prioritize a few
- Apply this rule to these guidelines themselves - if you see issues with these rules, point them out

**Rule 5: No Compliments or Flattery**
- Don't use unnecessary praise or excessive enthusiasm
- Avoid positive statements unless something is truly exceptional (not the norm)
- Present things as they are, factually
- Don't use acknowledgment phrases like "that's a valid concern" - just answer directly

### Development Workflow

Follow this 5-step workflow for ALL tasks (including simple ones):

**1. Understand Requirements**
- Clarify what needs to be done using two-phase questioning:
  - **Initial questions** (before exploring code): Ask about high-level ambiguities, approach, scope, constraints
  - **Post-exploration questions** (after reading code): Ask about specific implementation details, discovered issues, clarifications that only became apparent after seeing actual code
- Batch all questions in each phase together rather than asking one at a time

**2. Explore**
- Read relevant files, images, or URLs
- DO NOT write any code during this phase - no implementation, no test code snippets
- Only test through terminal commands if necessary to verify understanding
- For complex problems, consider using subagents
- Goal: Understand the current state before planning changes

**3. Plan**
- Make a detailed plan for how to approach the problem
- Use extended thinking mode for complex decisions requiring deeper analysis
- Consider alternatives and trade-offs
- Document the approach before implementing

**4. Code**
- Implement the plan or solution
- Follow the plan created in step 3
- Make changes systematically

**5. Review**
- Scale review depth based on change complexity:
  - **Trivial changes** (typo fixes, single-line changes): Quick verification of correctness and that nothing obvious breaks
  - **Simple changes** (single function mods, small features): Review logic correctness, edge cases, immediate impact
  - **Complex changes** (multi-file refactors, new features, architecture): Complete thorough audit covering critique, testing considerations, edge cases, performance, security, maintainability

- Categorize all identified issues by severity:
  - **Critical**: Blocks functionality, causes data loss, security vulnerabilities, breaks core features
  - **Major**: Significant bugs, poor architecture, performance problems, maintainability issues
  - **Minor**: Code quality issues, naming problems, small refactoring opportunities, stylistic inconsistencies

- List all issues found, grouped by severity, so critical problems are immediately visible

### Key Principles

- **Progress is pointless if moving in the wrong direction** - prioritize correctness over speed
- **Include all criticisms and alternatives** even if responses become very long
- **Be thorough and detailed** in analysis and review
- **Question everything that matters** but don't waste time on trivial established patterns

## Repository Structure

```
bot-builder/
├── backend/v1/          # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Application entry point
│   │   ├── config.py         # Settings management
│   │   ├── database.py       # Database connection
│   │   ├── api/              # API endpoints (auth, bots, flows, webhooks)
│   │   ├── models/           # SQLAlchemy models (user, bot, flow, session)
│   │   ├── schemas/          # Pydantic schemas for validation
│   │   ├── core/             # Business logic
│   │   │   ├── engine.py                # Main orchestration
│   │   │   ├── session_manager.py      # Session handling
│   │   │   ├── template_engine.py      # Variable substitution
│   │   │   ├── conditions.py           # Route evaluation
│   │   │   ├── validators.py           # Input validation
│   │   │   └── redis_manager.py        # Redis integration
│   │   ├── processors/       # Node type processors
│   │   │   ├── base_processor.py       # Abstract base class
│   │   │   ├── factory.py              # Processor factory pattern
│   │   │   └── [type]_processor.py     # Per-node-type logic
│   │   ├── services/         # Service layer (bot_service, flow_service)
│   │   ├── repositories/     # Database access layer
│   │   └── utils/            # Utilities, logging, exceptions
│   ├── alembic/              # Database migrations
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── README.md
│
└── frontend/            # React/TypeScript frontend
    ├── src/
    │   ├── App.tsx           # Router setup
    │   ├── main.tsx          # React entry point
    │   ├── pages/            # Page components
    │   │   ├── LoginPage.tsx
    │   │   ├── RegisterPage.tsx
    │   │   ├── BotsPage.tsx
    │   │   └── FlowEditorPage.tsx
    │   ├── components/       # Reusable components
    │   │   ├── ui/           # shadcn/ui components
    │   │   ├── flows/        # Flow editor components
    │   │   └── bots/         # Bot management components
    │   ├── contexts/         # React contexts (AuthContext)
    │   └── lib/              # Utilities and types
    │       ├── types.ts           # TypeScript type definitions
    │       ├── api.ts             # API client
    │       ├── flowLayoutUtils.ts # Dagre layout
    │       ├── routeConditionUtils.ts
    │       └── validators/        # Frontend validation
    ├── package.json
    └── vite.config.ts
```

## Development Setup

### Backend

```bash
cd backend/v1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

API available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

### Docker (Full Stack)

```bash
cd backend/v1

# Start all services (PostgreSQL, Redis, API, Evolution API)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Migrations run automatically on container startup via entrypoint script.

## Key Architecture Concepts

### Three-Tier Hierarchy

```
User (1) → (N) Bots → (N) Flows
```

- **User**: Authenticated account holder
- **Bot**: Logical grouping of flows with unique webhook URL
- **Flow**: Conversation definition with nodes and routing logic

### Platform-Agnostic Design

The core system is messaging-platform-agnostic. Integration layers (WhatsApp via Evolution API, etc.) translate platform-specific messages to normalized format and POST to bot webhooks: `/webhook/{bot_id}`

Sessions are keyed by: `channel:channel_user_id:bot_id`

### Flow Processing Architecture

The **ConversationOrchestrator** (in `engine.py`) orchestrates flow execution:

1. Receives incoming message via webhook
2. Loads or creates session for user-bot combination
3. Matches trigger keywords (bot-scoped) to select flow
4. Processes current node using appropriate processor
5. Evaluates routes (sorted by specificity) to determine next node
6. Auto-progresses through non-input nodes (max 10 consecutive)
7. Returns response to integration layer

### Node Processors

Each node type has a dedicated processor inheriting from `BaseProcessor`:

- **PromptProcessor**: Collects user input with validation
- **MenuProcessor**: Displays options (static or dynamic)
- **APIActionProcessor**: Calls external APIs, stores responses
- **LogicProcessor**: Conditional routing only
- **MessageProcessor**: Displays information
- **EndProcessor**: Terminates conversation

Processors return `ProcessResult` containing:
- `message`: Response text (rendered with template engine)
- `needs_input`: Whether to wait for user input
- `next_node`: Next node ID or None
- `context`: Updated session variables
- `terminal`: Whether conversation ends

### Template System

Variables use `{{variable}}` syntax. Available contexts:
- `{{context.variable_name}}` - Flow variables
- `{{session.channel_user_id}}` - Session data
- `{{api.field_name}}` - Last API response

### Route Evaluation

Routes are evaluated in sorted order (specific conditions before catch-all):
1. Sort routes by specificity (via `sort_routes()` in `conditions.py`)
2. Evaluate conditions using `ConditionEvaluator`
3. Select first matching route
4. Fall through to next if no match

Condition syntax supports:
- Comparisons: `context.age > 18`
- String operations: `input.contains("yes")`
- Logical operators: `context.verified && input == "1"`

### Session Management

- 30-minute absolute timeout
- State persisted in PostgreSQL
- Redis used for trigger keyword lookup (optional)
- Auto-cleanup runs every 10 minutes via background task

### System Constraints

| Constraint | Limit | Reason |
|------------|-------|--------|
| Max nodes per flow | 48 | Performance |
| Max routes per node | 8 | Complexity |
| Session timeout | 30 min (absolute) | Resource management |
| API timeout | 30 seconds | Fixed |
| Max auto-progression | 10 nodes | Prevent infinite loops |

## Frontend Architecture

### Tech Stack

- React 19 with TypeScript
- Vite for build tooling
- React Router for routing
- React Flow for visual flow editor
- Dagre for automatic graph layout
- shadcn/ui for UI components (Radix UI + Tailwind CSS)
- React Hook Form + Zod for form validation
- Axios for API calls
- TanStack Query for data fetching

### Key Components

- **FlowEditorPage**: Main flow editor using React Flow
- **NodePalette**: Drag-and-drop node creation
- **ChatSimulator**: Test flows in real-time
- **FlowSidebar**: Node configuration panels
- **AuthContext**: JWT-based authentication state

### State Management

- AuthContext provides user authentication state
- Local state for flow editor (nodes, edges, variables)
- No global state management library (Redux, etc.) - using React contexts and local state

### API Integration

The `lib/api.ts` module provides axios-based API client with:
- Automatic JWT token injection
- Base URL configuration
- Error handling
- Type-safe request/response interfaces

## Common Development Tasks

### Adding a New Node Type

1. Backend:
   - Define node config in `app/models/node_configs.py`
   - Create processor in `app/processors/[type]_processor.py`
   - Register in `ProcessorFactory` in `app/processors/factory.py`
   - Add to `NodeType` enum in `app/utils/constants.py`

2. Frontend:
   - Add type to `NodeType` in `lib/types.ts`
   - Create config interface and validator
   - Add node component in `components/flows/nodes/`
   - Add config panel in `FlowSidebar.tsx`
   - Update node palette

### Running Database Migrations

```bash
cd backend/v1

# Create migration
alembic revision --autogenerate -m "description"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Testing Flows

Use the built-in chat simulator in the frontend flow editor, or send webhook requests:

```bash
curl -X POST http://localhost:8000/webhook/{bot_id} \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: {webhook_secret}" \
  -d '{
    "channel": "whatsapp",
    "channel_user_id": "+1234567890",
    "message_text": "START"
  }'
```

## Important Files

- `backend/v1/BOT_BUILDER_SPECIFICATIONS.md`: Detailed system specifications
- `backend/v1/app/core/engine.py`: Main flow execution logic
- `backend/v1/app/processors/base_processor.py`: Base class for node processors
- `frontend/src/lib/types.ts`: TypeScript type definitions matching backend schemas
- `frontend/src/pages/FlowEditorPage.tsx`: Main flow editor implementation

## Dependencies

### Backend (Python 3.11+)

- FastAPI 0.104.1 - Web framework
- SQLAlchemy 2.0.23 - ORM (async-first)
- PostgreSQL 15+ via asyncpg
- Redis 5.0+ (optional but recommended)
- Alembic for migrations
- Pydantic for validation
- python-jose for JWT
- Evolution API v1.8.7 for WhatsApp integration

### Frontend

- React 19 with TypeScript
- Vite for bundling
- React Flow 11 for flow editor
- Dagre for graph layout
- shadcn/ui components
- Zod for validation
- TanStack Query for data fetching

## Security Notes

- JWT-based authentication with bcrypt password hashing
- Flow ownership enforcement at database level
- Webhook secret validation for incoming messages
- Input sanitization via Pydantic schemas
- Audit logging with PII masking
- CORS configured in FastAPI app
- Never store API keys in flow JSON - use environment variables

## Testing

Backend tests use pytest with pytest-asyncio:

```bash
cd backend/v1
pytest
pytest --cov=app tests/  # With coverage
```

Frontend testing setup is available but tests not yet implemented.
