# Bot Builder Frontend

React/TypeScript single-page application for building and managing conversational bots. Built with Vite, React 19, and React Flow.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. Expects the backend API at the URL set by `VITE_API_URL` (defaults to `http://localhost:8000`).

## Scripts

```bash
npm run dev       # Development server with HMR
npm run build     # TypeScript check + production build
npm run preview   # Preview production build
npm run lint      # ESLint
```

## Stack

- **React 19** + TypeScript
- **Vite** — build tooling
- **React Flow** — visual flow editor canvas
- **React Router** — client-side routing
- **TanStack Query** — server state management
- **React Hook Form** + Zod — form handling and validation
- **Radix UI** — accessible UI primitives
- **Tailwind CSS** — styling (via tailwind-merge, CVA, clsx)
- **Axios** — HTTP client
- **Lucide** — icons

## Pages

| Page | Path | Purpose |
|------|------|---------|
| Login | `/login` | Email/password authentication |
| Register | `/register` | Account creation |
| OAuth Callback | `/auth/callback` | Google OAuth2 redirect handler |
| Bots | `/bots` | Bot list, create, edit, delete |
| Flow Editor | `/bots/:botId/flows/:flowId` | Visual flow builder |
| Flow Editor | `/bots/:botId` | Flow editor (bot-level entry) |

## Key Components

- **FlowCanvas** — React Flow wrapper for the visual node editor
- **NodePalette** — drag-and-drop node type selector
- **FlowSidebar** — node configuration panel
- **FlowToolbar** — flow actions (save, export, simulate)
- **ChatSimulator** — in-browser flow testing
- **WhatsAppConnectionModal** — WhatsApp instance management via Evolution API

## Docker

```bash
docker build --build-arg VITE_API_URL=https://your-api.com -t bot-builder-frontend .
```

Builds with Node 20, serves via nginx on port 80.
