# Life Planner Frontend

React + Vite frontend for the Life Planner system. This UI surfaces tasks, calendar events, notes, goals, and the daily dashboard with real-time updates via WebSockets.

## Requirements

- Node.js 18+ (20+ recommended)
- npm (or your preferred Node package manager)

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## API Configuration

The frontend uses a dev proxy by default:

- `/api` -> `http://localhost:8000`
- `/ws` -> `ws://localhost:8000`

To override the API base URL (e.g., for a hosted backend), set `VITE_API_URL`:

```bash
VITE_API_URL=https://your-api.example.com npm run dev
```

## Useful Scripts

- `npm run dev` - Start the Vite dev server
- `npm run build` - Typecheck + production build
- `npm run build:analyze` - Build and generate `dist/stats.html`
- `npm run preview` - Preview the production build locally
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
|-- src/
|   |-- api/         # HTTP client + API helpers
|   |-- components/  # UI components
|   |-- hooks/       # Shared React hooks
|   |-- pages/       # Route-level pages
|   |-- providers/   # App-wide providers (React Query, WebSockets)
|   |-- stores/      # Zustand stores
|   |-- styles/      # Global styles and design tokens
|   `-- routes.tsx   # Router definitions
`-- vite.config.ts
```
