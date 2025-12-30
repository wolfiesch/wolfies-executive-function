# Frontend Optimizations: Code-Splitting & Real-Time Updates

**Created:** 12/30/2025 06:00 AM PST (via pst-timestamp)
**Status:** Planning Phase
**Prerequisite:** FastAPI backend (in progress by another agent)

---

## Executive Summary

Two critical optimizations to transform the frontend from a good MVP to a production-grade application:

1. **Code-Splitting** - Reduce initial bundle from 559KB → ~150KB (73% reduction)
2. **Real-Time Updates** - WebSocket-based sync for instant multi-device updates

---

# Part 1: Code-Splitting

## 1.1 Current State Analysis

```
Build Output (Current):
─────────────────────────────────────────────────────────
dist/assets/index-dwbLpUQv.js   559.89 KB │ gzip: 175.97 KB
dist/assets/index-B3f0Ov19.css   42.76 KB │ gzip:   7.46 KB
─────────────────────────────────────────────────────────
                         TOTAL: 602.65 KB │ gzip: 183.43 KB

⚠️ Warning: Chunk exceeds 500KB limit
```

### Estimated Bundle Composition

Based on package.json dependencies and typical bundle sizes:

| Library | Estimated Size | Splitting Strategy |
|---------|----------------|-------------------|
| **react + react-dom** | ~140KB | Keep in main (required) |
| **recharts** | ~180KB | Lazy load (charts heavy) |
| **framer-motion** | ~80KB | Lazy load (animations) |
| **@radix-ui/*** | ~60KB | Tree-shake, partial load |
| **react-router-dom** | ~30KB | Keep in main (routing) |
| **@tanstack/react-query** | ~25KB | Keep in main (data layer) |
| **date-fns** | ~20KB | Tree-shakeable |
| **cmdk** | ~15KB | Lazy load (command palette) |
| **zustand** | ~3KB | Keep in main (tiny) |
| **Other** | ~6KB | Various |

### Key Insight

**Recharts alone is ~180KB** - nearly 1/3 of the bundle. It's only used on Dashboard and Goals pages. Lazy loading just recharts would cut initial load significantly.

---

## 1.2 Code-Splitting Strategy

### Three-Layer Approach

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Critical Path (loads immediately)          ~150KB │
│ ─────────────────────────────────────────────────────────── │
│ React, React Router, React Query, Zustand                   │
│ Core UI components (Button, Input, Card)                    │
│ AppShell, Sidebar, Header                                   │
│ Dashboard page (landing)                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Route Chunks (loaded on navigation)         ~200KB │
│ ─────────────────────────────────────────────────────────── │
│ Tasks page chunk                                            │
│ Calendar page chunk                                         │
│ Notes page chunk                                            │
│ Goals page chunk                                            │
│ Projects page chunk                                         │
│ Settings page chunk                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Feature Chunks (loaded on demand)           ~200KB │
│ ─────────────────────────────────────────────────────────── │
│ recharts (when charts render)                               │
│ CommandPalette (on ⌘K press)                               │
│ Tiptap editor (on note edit)                                │
│ framer-motion animations (progressive)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 1.3 Implementation Plan

### Step 1: Route-Based Code Splitting

**File:** `frontend/src/routes.tsx`

```tsx
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { AppShell } from '@/components/layout'

// ============================================================
// LAZY-LOADED PAGES
// ============================================================
// React.lazy() enables automatic code splitting. Each page becomes
// a separate chunk that's only downloaded when the user navigates to it.
//
// CS Concept: **Dynamic Imports** - The import() function returns a Promise
// that resolves to the module. Webpack/Vite sees this and creates a separate
// bundle for each dynamically imported module.
// ============================================================

// Dashboard loads eagerly (it's the landing page)
import { Dashboard } from '@/pages'

// All other pages load lazily
const Tasks = lazy(() => import('@/pages/Tasks'))
const Calendar = lazy(() => import('@/pages/Calendar'))
const Notes = lazy(() => import('@/pages/Notes'))
const Goals = lazy(() => import('@/pages/Goals'))
const Projects = lazy(() => import('@/pages/Projects'))
const Settings = lazy(() => import('@/pages/Settings'))
const NotFound = lazy(() => import('@/pages/NotFound'))

// ============================================================
// LOADING FALLBACK
// ============================================================
// Shown while lazy components are loading. Keep it minimal and fast.
// ============================================================

function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
        <span className="text-sm text-text-secondary">Loading...</span>
      </div>
    </div>
  )
}

// ============================================================
// SUSPENSE WRAPPER
// ============================================================
// Wraps lazy components with Suspense boundary and fallback.
// ============================================================

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<PageLoader />}>
      {children}
    </Suspense>
  )
}

// ============================================================
// ROUTE CONFIGURATION
// ============================================================

export const router = createBrowserRouter([
  // Dashboard - Loads immediately (critical path)
  {
    path: '/',
    element: <Dashboard />,
  },

  // Tasks - Lazy loaded
  {
    path: '/tasks',
    element: <LazyPage><Tasks /></LazyPage>,
  },
  {
    path: '/tasks/:id',
    element: <LazyPage><Tasks /></LazyPage>,
  },

  // Calendar - Lazy loaded
  {
    path: '/calendar',
    element: <LazyPage><Calendar /></LazyPage>,
  },

  // Notes - Lazy loaded
  {
    path: '/notes',
    element: <LazyPage><Notes /></LazyPage>,
  },
  {
    path: '/notes/:id',
    element: <LazyPage><Notes /></LazyPage>,
  },

  // Goals - Lazy loaded (contains recharts)
  {
    path: '/goals',
    element: <LazyPage><Goals /></LazyPage>,
  },
  {
    path: '/goals/:id',
    element: <LazyPage><Goals /></LazyPage>,
  },

  // Projects - Lazy loaded
  {
    path: '/projects',
    element: <LazyPage><Projects /></LazyPage>,
  },

  // Settings - Lazy loaded
  {
    path: '/settings',
    element: <LazyPage><Settings /></LazyPage>,
  },

  // Search redirect
  {
    path: '/search',
    element: <Navigate to="/" replace />,
  },

  // 404 - Lazy loaded
  {
    path: '*',
    element: <LazyPage><NotFound /></LazyPage>,
  },
])

// Route helpers remain the same
export const routes = {
  dashboard: () => '/',
  tasks: () => '/tasks',
  task: (id: string) => `/tasks/${id}`,
  calendar: () => '/calendar',
  notes: () => '/notes',
  note: (id: string) => `/notes/${id}`,
  goals: () => '/goals',
  goal: (id: string) => `/goals/${id}`,
  projects: () => '/projects',
  search: () => '/search',
  settings: () => '/settings',
} as const
```

### Step 2: Update Page Exports for Default Exports

Each page needs a default export for `lazy()` to work:

**Pattern for each page file:**

```tsx
// frontend/src/pages/Tasks.tsx
// ... existing code ...

// Add default export at the bottom
export default Tasks
```

**File:** `frontend/src/pages/index.ts` - Update for mixed exports:

```tsx
// Named exports for direct imports
export { Dashboard } from './Dashboard'

// Default exports are handled by lazy() imports in routes.tsx
// We keep named exports here for backwards compatibility
export { default as Tasks } from './Tasks'
export { default as Calendar } from './Calendar'
export { default as Notes } from './Notes'
export { default as Goals } from './Goals'
export { default as Projects } from './Projects'
export { default as Settings } from './Settings'
export { default as NotFound } from './NotFound'
```

### Step 3: Vite Manual Chunks Configuration

**File:** `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // WebSocket proxy for real-time updates
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },

  build: {
    // ========================================================
    // MANUAL CHUNKS CONFIGURATION
    // ========================================================
    // Splits vendor libraries into separate chunks for better caching.
    // When your code changes, only the app chunk is invalidated.
    // Vendor chunks stay cached in the browser.
    //
    // CS Concept: **HTTP Caching** - Browsers cache files by URL.
    // Separate chunks = separate cache entries = unchanged chunks
    // don't need to be re-downloaded when you deploy updates.
    // ========================================================
    rollupOptions: {
      output: {
        manualChunks: {
          // React core - rarely changes, cache forever
          'vendor-react': [
            'react',
            'react-dom',
            'react-router-dom',
          ],

          // Data layer - changes occasionally
          'vendor-data': [
            '@tanstack/react-query',
            'zustand',
            'axios',
          ],

          // UI libraries - Radix components
          'vendor-ui': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-popover',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-select',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-slot',
          ],

          // Charts - HEAVY, only load when needed
          'vendor-charts': [
            'recharts',
          ],

          // Animation library
          'vendor-motion': [
            'framer-motion',
          ],

          // Utilities
          'vendor-utils': [
            'date-fns',
            'clsx',
            'tailwind-merge',
            'zod',
          ],

          // Command palette
          'vendor-cmdk': [
            'cmdk',
          ],
        },
      },
    },

    // Increase warning limit slightly (we'll still be well under)
    chunkSizeWarningLimit: 250,
  },
})
```

### Step 4: Lazy Load Command Palette

The command palette (⌘K) is not needed on initial load:

**File:** `frontend/src/components/layout/AppShell.tsx`

```tsx
import { lazy, Suspense, useEffect, useState } from 'react'
import { useUIStore } from '@/stores'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { RightPanel } from './RightPanel'

// Lazy load CommandPalette - only when user presses ⌘K
const CommandPalette = lazy(() => import('./CommandPalette'))

export function AppShell({ children }: { children: React.ReactNode }) {
  const { commandPaletteOpen } = useUIStore()

  // Only mount CommandPalette after first open
  // This prevents loading the chunk until needed
  const [hasOpenedPalette, setHasOpenedPalette] = useState(false)

  useEffect(() => {
    if (commandPaletteOpen && !hasOpenedPalette) {
      setHasOpenedPalette(true)
    }
  }, [commandPaletteOpen, hasOpenedPalette])

  return (
    <div className="flex h-screen bg-bg-primary">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
      <RightPanel />

      {/* Only load CommandPalette chunk after first ⌘K press */}
      {hasOpenedPalette && (
        <Suspense fallback={null}>
          <CommandPalette />
        </Suspense>
      )}
    </div>
  )
}
```

### Step 5: Lazy Load Charts in Dashboard

**File:** `frontend/src/components/dashboard/StatsChart.tsx` (new file)

```tsx
// Heavy recharts component - loaded separately
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface StatsChartProps {
  data: Array<{ date: string; completed: number; created: number }>
}

export default function StatsChart({ data }: StatsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <XAxis dataKey="date" stroke="var(--color-text-tertiary)" />
        <YAxis stroke="var(--color-text-tertiary)" />
        <Tooltip
          contentStyle={{
            background: 'var(--color-bg-tertiary)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: '8px',
          }}
        />
        <Area
          type="monotone"
          dataKey="completed"
          stroke="var(--color-accent-green)"
          fill="var(--color-accent-green)"
          fillOpacity={0.2}
        />
        <Area
          type="monotone"
          dataKey="created"
          stroke="var(--color-accent-blue)"
          fill="var(--color-accent-blue)"
          fillOpacity={0.2}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
```

**Usage in Dashboard:**

```tsx
import { lazy, Suspense } from 'react'

const StatsChart = lazy(() => import('@/components/dashboard/StatsChart'))

function Dashboard() {
  // ... other code ...

  return (
    <div>
      {/* ... other content ... */}

      {/* Chart loads after main content */}
      <Suspense fallback={<div className="h-[200px] animate-pulse bg-bg-tertiary rounded-lg" />}>
        <StatsChart data={chartData} />
      </Suspense>
    </div>
  )
}
```

### Step 6: Add Bundle Analyzer

**Install:**

```bash
cd frontend
npm install -D rollup-plugin-visualizer
```

**Update vite.config.ts:**

```typescript
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Only in build mode, generates stats.html
    visualizer({
      filename: 'dist/stats.html',
      open: false, // Set to true to auto-open after build
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  // ... rest of config
})
```

**Add npm script:**

```json
{
  "scripts": {
    "build": "tsc -b && vite build",
    "build:analyze": "tsc -b && vite build && open dist/stats.html"
  }
}
```

---

## 1.4 Expected Results

### Before (Current)

```
dist/assets/index.js    559.89 KB │ gzip: 175.97 KB
```

### After (Projected)

```
dist/assets/index.js           ~120 KB │ gzip: ~40 KB  (main app)
dist/assets/vendor-react.js    ~140 KB │ gzip: ~45 KB  (cached)
dist/assets/vendor-data.js      ~30 KB │ gzip: ~10 KB  (cached)
dist/assets/vendor-ui.js        ~60 KB │ gzip: ~20 KB  (cached)
dist/assets/vendor-charts.js   ~180 KB │ gzip: ~55 KB  (lazy)
dist/assets/vendor-motion.js    ~80 KB │ gzip: ~25 KB  (lazy)
dist/assets/Tasks.js            ~15 KB │ gzip:  ~5 KB  (lazy)
dist/assets/Calendar.js         ~15 KB │ gzip:  ~5 KB  (lazy)
dist/assets/Notes.js            ~15 KB │ gzip:  ~5 KB  (lazy)
dist/assets/Goals.js            ~20 KB │ gzip:  ~7 KB  (lazy)
... etc
```

### Critical Path Improvement

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Initial JS** | 559 KB | ~120 KB | **78% smaller** |
| **Initial gzip** | 176 KB | ~40 KB | **77% smaller** |
| **Time to Interactive** | ~2.5s | ~0.8s | **68% faster** |

---

## 1.5 Testing Checklist

- [ ] Run `npm run build` - no errors
- [ ] Run `npm run build:analyze` - verify chunk sizes
- [ ] Test each route loads correctly with lazy loading
- [ ] Verify loading spinners appear during chunk load
- [ ] Test ⌘K command palette lazy loads on first use
- [ ] Test charts lazy load on Dashboard/Goals
- [ ] Lighthouse performance score improvement

---

# Part 2: Real-Time Updates (WebSocket)

## 2.1 Architecture Overview

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│   Browser Tab   │◄════════════════════════►  │  FastAPI Server │
│   (React App)   │         /ws                │   (Python)      │
└────────┬────────┘                            └────────┬────────┘
         │                                              │
         │  ┌────────────────────────────────────────┐  │
         │  │         WebSocket Messages             │  │
         │  │────────────────────────────────────────│  │
         │  │  Client → Server:                      │  │
         │  │    { type: "subscribe", topics: [...]} │  │
         │  │    { type: "ping" }                    │  │
         │  │                                        │  │
         │  │  Server → Client:                      │  │
         │  │    { type: "task_created", data: {...}}│  │
         │  │    { type: "task_updated", data: {...}}│  │
         │  │    { type: "task_deleted", id: "..." } │  │
         │  │    { type: "event_created", data: {...}│  │
         │  │    { type: "pong" }                    │  │
         │  └────────────────────────────────────────┘  │
         │                                              │
         ▼                                              ▼
┌─────────────────┐                            ┌─────────────────┐
│  React Query    │                            │  Event Bus      │
│  Cache Update   │                            │  (Pub/Sub)      │
└─────────────────┘                            └─────────────────┘
```

### Why WebSocket over Polling?

| Approach | Latency | Server Load | Complexity | Verdict |
|----------|---------|-------------|------------|---------|
| **Polling (5s)** | 0-5s avg | High (constant requests) | Low | ❌ Wasteful |
| **Long Polling** | <1s | Medium | Medium | 🟡 Okay |
| **SSE** | <100ms | Low | Medium | 🟡 One-way only |
| **WebSocket** | <50ms | Low | Higher | ✅ Best for this use case |

**Decision:** WebSocket is ideal because:
- Life planner needs **bi-directional** communication (user actions + server updates)
- Sub-50ms latency makes the app feel instant
- Single persistent connection vs. many HTTP requests
- FastAPI has excellent WebSocket support

---

## 2.2 Message Protocol

### Event Types

```typescript
// frontend/src/types/websocket.ts

/**
 * WebSocket Message Types
 *
 * CS Concept: **Event-Driven Architecture** - Components communicate
 * through events rather than direct calls. This decouples the sender
 * from receivers and enables easy extensibility.
 */

// ============================================================
// CLIENT → SERVER MESSAGES
// ============================================================

interface SubscribeMessage {
  type: 'subscribe'
  topics: ('tasks' | 'calendar' | 'notes' | 'goals' | 'dashboard')[]
}

interface UnsubscribeMessage {
  type: 'unsubscribe'
  topics: string[]
}

interface PingMessage {
  type: 'ping'
  timestamp: number
}

type ClientMessage = SubscribeMessage | UnsubscribeMessage | PingMessage

// ============================================================
// SERVER → CLIENT MESSAGES
// ============================================================

interface TaskCreatedEvent {
  type: 'task_created'
  data: Task
  timestamp: string
}

interface TaskUpdatedEvent {
  type: 'task_updated'
  data: Task
  timestamp: string
}

interface TaskDeletedEvent {
  type: 'task_deleted'
  id: string
  timestamp: string
}

interface TaskCompletedEvent {
  type: 'task_completed'
  data: Task
  timestamp: string
}

interface EventCreatedEvent {
  type: 'event_created'
  data: CalendarEvent
  timestamp: string
}

interface EventUpdatedEvent {
  type: 'event_updated'
  data: CalendarEvent
  timestamp: string
}

interface EventDeletedEvent {
  type: 'event_deleted'
  id: string
  timestamp: string
}

interface NoteCreatedEvent {
  type: 'note_created'
  data: Note
  timestamp: string
}

interface NoteUpdatedEvent {
  type: 'note_updated'
  data: Note
  timestamp: string
}

interface GoalProgressEvent {
  type: 'goal_progress'
  goalId: string
  progress: number
  timestamp: string
}

interface DashboardRefreshEvent {
  type: 'dashboard_refresh'
  timestamp: string
}

interface PongMessage {
  type: 'pong'
  timestamp: number
  serverTime: string
}

interface ErrorMessage {
  type: 'error'
  code: string
  message: string
}

type ServerMessage =
  | TaskCreatedEvent
  | TaskUpdatedEvent
  | TaskDeletedEvent
  | TaskCompletedEvent
  | EventCreatedEvent
  | EventUpdatedEvent
  | EventDeletedEvent
  | NoteCreatedEvent
  | NoteUpdatedEvent
  | GoalProgressEvent
  | DashboardRefreshEvent
  | PongMessage
  | ErrorMessage

export type {
  ClientMessage,
  ServerMessage,
  TaskCreatedEvent,
  TaskUpdatedEvent,
  // ... etc
}
```

---

## 2.3 Frontend Implementation

### Step 1: WebSocket Hook

**File:** `frontend/src/hooks/useWebSocket.ts`

```typescript
import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { ClientMessage, ServerMessage } from '@/types/websocket'

/**
 * WebSocket connection states
 */
type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

/**
 * WebSocket configuration
 */
interface WebSocketConfig {
  /** WebSocket URL (defaults to /ws) */
  url?: string
  /** Topics to subscribe to on connect */
  topics?: string[]
  /** Reconnect on disconnect */
  reconnect?: boolean
  /** Reconnect delay in ms (doubles each attempt, max 30s) */
  reconnectDelay?: number
  /** Maximum reconnect attempts (0 = infinite) */
  maxReconnectAttempts?: number
  /** Ping interval in ms (keeps connection alive) */
  pingInterval?: number
}

const DEFAULT_CONFIG: Required<WebSocketConfig> = {
  url: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`,
  topics: ['tasks', 'calendar', 'notes', 'goals', 'dashboard'],
  reconnect: true,
  reconnectDelay: 1000,
  maxReconnectAttempts: 0, // infinite
  pingInterval: 30000, // 30 seconds
}

/**
 * useWebSocket - Real-time updates via WebSocket
 *
 * Handles:
 * - Automatic connection management
 * - Reconnection with exponential backoff
 * - Keep-alive pings
 * - React Query cache invalidation on events
 *
 * CS Concept: **Exponential Backoff** - When reconnecting, wait time doubles
 * each attempt (1s, 2s, 4s, 8s...) to avoid overwhelming the server.
 *
 * @example
 * ```tsx
 * function App() {
 *   const { state, isConnected } = useWebSocket({
 *     topics: ['tasks', 'calendar'],
 *   })
 *
 *   return <div>Status: {state}</div>
 * }
 * ```
 */
export function useWebSocket(config: WebSocketConfig = {}) {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const queryClient = useQueryClient()

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const pingIntervalRef = useRef<NodeJS.Timeout>()

  const [state, setState] = useState<ConnectionState>('disconnected')
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null)
  const [error, setError] = useState<Error | null>(null)

  // ============================================================
  // MESSAGE HANDLERS
  // ============================================================

  /**
   * Handle incoming WebSocket messages.
   * Updates React Query cache based on event type.
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: ServerMessage = JSON.parse(event.data)
      setLastMessage(message)

      // Route message to appropriate handler
      switch (message.type) {
        // ──────────────────────────────────────────────────
        // TASK EVENTS
        // ──────────────────────────────────────────────────
        case 'task_created':
          // Add new task to cache
          queryClient.setQueryData(['tasks'], (old: any) => {
            if (!old?.data) return old
            return { ...old, data: [message.data, ...old.data] }
          })
          // Invalidate dashboard (stats changed)
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        case 'task_updated':
        case 'task_completed':
          // Update task in cache
          queryClient.setQueryData(['tasks'], (old: any) => {
            if (!old?.data) return old
            return {
              ...old,
              data: old.data.map((t: any) =>
                t.id === message.data.id ? message.data : t
              ),
            }
          })
          // Also update individual task query
          queryClient.setQueryData(['tasks', message.data.id], message.data)
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        case 'task_deleted':
          // Remove task from cache
          queryClient.setQueryData(['tasks'], (old: any) => {
            if (!old?.data) return old
            return {
              ...old,
              data: old.data.filter((t: any) => t.id !== message.id),
            }
          })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        // ──────────────────────────────────────────────────
        // CALENDAR EVENTS
        // ──────────────────────────────────────────────────
        case 'event_created':
          queryClient.setQueryData(['calendar'], (old: any) => {
            if (!old?.data) return old
            return { ...old, data: [...old.data, message.data] }
          })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        case 'event_updated':
          queryClient.setQueryData(['calendar'], (old: any) => {
            if (!old?.data) return old
            return {
              ...old,
              data: old.data.map((e: any) =>
                e.id === message.data.id ? message.data : e
              ),
            }
          })
          break

        case 'event_deleted':
          queryClient.setQueryData(['calendar'], (old: any) => {
            if (!old?.data) return old
            return {
              ...old,
              data: old.data.filter((e: any) => e.id !== message.id),
            }
          })
          break

        // ──────────────────────────────────────────────────
        // NOTE EVENTS
        // ──────────────────────────────────────────────────
        case 'note_created':
          queryClient.setQueryData(['notes'], (old: any) => {
            if (!old?.data) return old
            return { ...old, data: [message.data, ...old.data] }
          })
          break

        case 'note_updated':
          queryClient.setQueryData(['notes'], (old: any) => {
            if (!old?.data) return old
            return {
              ...old,
              data: old.data.map((n: any) =>
                n.id === message.data.id ? message.data : n
              ),
            }
          })
          queryClient.setQueryData(['notes', message.data.id], message.data)
          break

        // ──────────────────────────────────────────────────
        // GOAL EVENTS
        // ──────────────────────────────────────────────────
        case 'goal_progress':
          queryClient.invalidateQueries({ queryKey: ['goals'] })
          queryClient.invalidateQueries({ queryKey: ['goals', message.goalId] })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        // ──────────────────────────────────────────────────
        // DASHBOARD REFRESH
        // ──────────────────────────────────────────────────
        case 'dashboard_refresh':
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          break

        // ──────────────────────────────────────────────────
        // SYSTEM MESSAGES
        // ──────────────────────────────────────────────────
        case 'pong':
          // Connection is healthy, nothing to do
          break

        case 'error':
          console.error('[WebSocket] Server error:', message.message)
          setError(new Error(message.message))
          break

        default:
          console.warn('[WebSocket] Unknown message type:', (message as any).type)
      }
    } catch (err) {
      console.error('[WebSocket] Failed to parse message:', err)
    }
  }, [queryClient])

  // ============================================================
  // CONNECTION MANAGEMENT
  // ============================================================

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    setState('connecting')

    try {
      const ws = new WebSocket(cfg.url)
      wsRef.current = ws

      ws.onopen = () => {
        setState('connected')
        setError(null)
        reconnectAttemptRef.current = 0

        // Subscribe to topics
        const subscribeMsg: ClientMessage = {
          type: 'subscribe',
          topics: cfg.topics as any,
        }
        ws.send(JSON.stringify(subscribeMsg))

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const pingMsg: ClientMessage = {
              type: 'ping',
              timestamp: Date.now(),
            }
            ws.send(JSON.stringify(pingMsg))
          }
        }, cfg.pingInterval)
      }

      ws.onmessage = handleMessage

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event)
        setError(new Error('WebSocket connection error'))
      }

      ws.onclose = (event) => {
        setState('disconnected')

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
        }

        // Attempt reconnection if enabled
        if (cfg.reconnect && !event.wasClean) {
          const maxAttempts = cfg.maxReconnectAttempts
          if (maxAttempts === 0 || reconnectAttemptRef.current < maxAttempts) {
            setState('reconnecting')

            // Exponential backoff: 1s, 2s, 4s, 8s... up to 30s
            const delay = Math.min(
              cfg.reconnectDelay * Math.pow(2, reconnectAttemptRef.current),
              30000
            )

            reconnectAttemptRef.current++

            console.log(
              `[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`
            )

            reconnectTimeoutRef.current = setTimeout(connect, delay)
          }
        }
      }
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err)
      setError(err instanceof Error ? err : new Error('Connection failed'))
      setState('disconnected')
    }
  }, [cfg, handleMessage])

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    setState('disconnected')
  }, [])

  /**
   * Send a message to the server
   */
  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('[WebSocket] Cannot send - not connected')
    }
  }, [])

  // ============================================================
  // LIFECYCLE
  // ============================================================

  useEffect(() => {
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, []) // Only run on mount/unmount

  // ============================================================
  // RETURN VALUE
  // ============================================================

  return {
    /** Current connection state */
    state,
    /** Whether connected */
    isConnected: state === 'connected',
    /** Whether reconnecting */
    isReconnecting: state === 'reconnecting',
    /** Last received message */
    lastMessage,
    /** Last error */
    error,
    /** Manually send a message */
    send,
    /** Manually disconnect */
    disconnect,
    /** Manually reconnect */
    reconnect: connect,
  }
}
```

### Step 2: WebSocket Provider

**File:** `frontend/src/providers/WebSocketProvider.tsx`

```typescript
import { createContext, useContext, ReactNode } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'

type WebSocketContextType = ReturnType<typeof useWebSocket>

const WebSocketContext = createContext<WebSocketContextType | null>(null)

interface WebSocketProviderProps {
  children: ReactNode
  /** Topics to subscribe to */
  topics?: string[]
}

/**
 * WebSocketProvider - Provides WebSocket connection to the app
 *
 * Wrap your app with this provider to enable real-time updates.
 *
 * @example
 * ```tsx
 * <WebSocketProvider topics={['tasks', 'calendar']}>
 *   <App />
 * </WebSocketProvider>
 * ```
 */
export function WebSocketProvider({ children, topics }: WebSocketProviderProps) {
  const ws = useWebSocket({ topics })

  return (
    <WebSocketContext.Provider value={ws}>
      {children}
    </WebSocketContext.Provider>
  )
}

/**
 * useWebSocketContext - Access WebSocket connection from any component
 */
export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}
```

### Step 3: Update App.tsx

**File:** `frontend/src/App.tsx`

```tsx
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { router } from '@/routes'
import { WebSocketProvider } from '@/providers/WebSocketProvider'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* WebSocket provider wraps the app for real-time updates */}
      <WebSocketProvider topics={['tasks', 'calendar', 'notes', 'goals', 'dashboard']}>
        <RouterProvider router={router} />
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-subtle)',
            },
            success: {
              iconTheme: {
                primary: 'var(--color-accent-green)',
                secondary: 'var(--color-bg-tertiary)',
              },
            },
            error: {
              iconTheme: {
                primary: 'var(--color-accent-red)',
                secondary: 'var(--color-bg-tertiary)',
              },
            },
          }}
        />
      </WebSocketProvider>
    </QueryClientProvider>
  )
}

export default App
```

### Step 4: Connection Status Indicator

**File:** `frontend/src/components/common/ConnectionStatus.tsx`

```tsx
import { useWebSocketContext } from '@/providers/WebSocketProvider'
import { Wifi, WifiOff, Loader2 } from 'lucide-react'
import { Tooltip } from '@/components/ui'

/**
 * ConnectionStatus - Shows WebSocket connection state
 *
 * Use in the header or sidebar to give users visibility
 * into real-time sync status.
 */
export function ConnectionStatus() {
  const { state, isConnected, isReconnecting } = useWebSocketContext()

  if (isConnected) {
    return (
      <Tooltip content="Real-time sync active">
        <div className="flex items-center gap-1.5 text-accent-green">
          <Wifi className="h-4 w-4" />
          <span className="text-xs hidden sm:inline">Live</span>
        </div>
      </Tooltip>
    )
  }

  if (isReconnecting) {
    return (
      <Tooltip content="Reconnecting...">
        <div className="flex items-center gap-1.5 text-accent-yellow">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-xs hidden sm:inline">Syncing</span>
        </div>
      </Tooltip>
    )
  }

  return (
    <Tooltip content="Offline - changes will sync when reconnected">
      <div className="flex items-center gap-1.5 text-text-tertiary">
        <WifiOff className="h-4 w-4" />
        <span className="text-xs hidden sm:inline">Offline</span>
      </div>
    </Tooltip>
  )
}
```

---

## 2.4 Backend Implementation

### FastAPI WebSocket Endpoint

**File:** `src/api/websocket.py`

```python
"""
WebSocket server for real-time updates.

CS Concept: **Pub/Sub Pattern** - The server acts as a message broker.
Clients subscribe to topics (tasks, calendar, etc.) and the server
publishes events to all subscribers when data changes.

Architecture:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client A   │────►│  WebSocket  │◄────│  Client B   │
│  (browser)  │◄────│   Manager   │────►│  (browser)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   API       │
                    │   Routes    │
                    │  (publish)  │
                    └─────────────┘
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
import json
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum


class TopicType(str, Enum):
    """Available subscription topics"""
    TASKS = "tasks"
    CALENDAR = "calendar"
    NOTES = "notes"
    GOALS = "goals"
    DASHBOARD = "dashboard"


@dataclass
class Connection:
    """Represents a WebSocket connection"""
    websocket: WebSocket
    topics: Set[str]
    connected_at: datetime


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Thread-safe implementation for handling multiple concurrent connections.

    Usage:
        manager = WebSocketManager()

        # In WebSocket endpoint
        await manager.connect(websocket)

        # When data changes (e.g., task created)
        await manager.broadcast_to_topic("tasks", {
            "type": "task_created",
            "data": task_data
        })
    """

    def __init__(self):
        # Map of connection_id -> Connection
        self.connections: Dict[str, Connection] = {}
        # Map of topic -> set of connection_ids
        self.topic_subscribers: Dict[str, Set[str]] = {
            topic.value: set() for topic in TopicType
        }
        # Lock for thread safety
        self._lock = asyncio.Lock()

    def _get_connection_id(self, websocket: WebSocket) -> str:
        """Generate unique ID for a connection"""
        return f"{id(websocket)}"

    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept and register a new WebSocket connection.

        Returns:
            Connection ID
        """
        await websocket.accept()

        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            self.connections[conn_id] = Connection(
                websocket=websocket,
                topics=set(),
                connected_at=datetime.now(timezone.utc)
            )

        return conn_id

    async def disconnect(self, websocket: WebSocket):
        """Remove a connection and all its subscriptions"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id in self.connections:
                # Remove from all topic subscriptions
                for topic in self.connections[conn_id].topics:
                    self.topic_subscribers[topic].discard(conn_id)

                # Remove connection
                del self.connections[conn_id]

    async def subscribe(self, websocket: WebSocket, topics: list[str]):
        """Subscribe a connection to topics"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id not in self.connections:
                return

            for topic in topics:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].add(conn_id)
                    self.connections[conn_id].topics.add(topic)

    async def unsubscribe(self, websocket: WebSocket, topics: list[str]):
        """Unsubscribe a connection from topics"""
        conn_id = self._get_connection_id(websocket)

        async with self._lock:
            if conn_id not in self.connections:
                return

            for topic in topics:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].discard(conn_id)
                    self.connections[conn_id].topics.discard(topic)

    async def broadcast_to_topic(self, topic: str, message: dict):
        """
        Send a message to all connections subscribed to a topic.

        Args:
            topic: The topic name (e.g., "tasks", "calendar")
            message: The message to send (will be JSON serialized)
        """
        if topic not in self.topic_subscribers:
            return

        # Add timestamp
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message_json = json.dumps(message)

        # Get subscribers (copy to avoid modification during iteration)
        async with self._lock:
            subscriber_ids = list(self.topic_subscribers[topic])

        # Send to all subscribers (handle disconnections)
        disconnected = []
        for conn_id in subscriber_ids:
            if conn_id in self.connections:
                try:
                    await self.connections[conn_id].websocket.send_text(message_json)
                except Exception:
                    disconnected.append(conn_id)

        # Clean up disconnected connections
        if disconnected:
            async with self._lock:
                for conn_id in disconnected:
                    if conn_id in self.connections:
                        for t in self.connections[conn_id].topics:
                            self.topic_subscribers[t].discard(conn_id)
                        del self.connections[conn_id]

    async def broadcast_to_all(self, message: dict):
        """Send a message to all connected clients"""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        message_json = json.dumps(message)

        async with self._lock:
            conn_ids = list(self.connections.keys())

        disconnected = []
        for conn_id in conn_ids:
            if conn_id in self.connections:
                try:
                    await self.connections[conn_id].websocket.send_text(message_json)
                except Exception:
                    disconnected.append(conn_id)

        # Clean up
        if disconnected:
            async with self._lock:
                for conn_id in disconnected:
                    if conn_id in self.connections:
                        del self.connections[conn_id]

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for a topic"""
        return len(self.topic_subscribers.get(topic, set()))


# Global manager instance
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint handler.

    Protocol:
        Client sends: { "type": "subscribe", "topics": ["tasks", "calendar"] }
        Client sends: { "type": "ping", "timestamp": 1234567890 }
        Server sends: { "type": "task_created", "data": {...}, "timestamp": "..." }
        Server sends: { "type": "pong", "timestamp": 1234567890, "serverTime": "..." }
    """
    conn_id = await ws_manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    topics = message.get("topics", [])
                    await ws_manager.subscribe(websocket, topics)

                elif msg_type == "unsubscribe":
                    topics = message.get("topics", [])
                    await ws_manager.unsubscribe(websocket, topics)

                elif msg_type == "ping":
                    # Respond with pong
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp"),
                        "serverTime": datetime.now(timezone.utc).isoformat(),
                    }))

                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unknown message type: {msg_type}",
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Message must be valid JSON",
                }))

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


# ============================================================
# HELPER FUNCTIONS FOR API ROUTES
# ============================================================

async def notify_task_created(task: dict):
    """Call this after creating a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_created",
        "data": task,
    })
    # Also notify dashboard
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_task_updated(task: dict):
    """Call this after updating a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_updated",
        "data": task,
    })


async def notify_task_completed(task: dict):
    """Call this after completing a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_completed",
        "data": task,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_task_deleted(task_id: str):
    """Call this after deleting a task"""
    await ws_manager.broadcast_to_topic("tasks", {
        "type": "task_deleted",
        "id": task_id,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })


async def notify_event_created(event: dict):
    """Call this after creating a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_created",
        "data": event,
    })


async def notify_event_updated(event: dict):
    """Call this after updating a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_updated",
        "data": event,
    })


async def notify_event_deleted(event_id: str):
    """Call this after deleting a calendar event"""
    await ws_manager.broadcast_to_topic("calendar", {
        "type": "event_deleted",
        "id": event_id,
    })


async def notify_note_created(note: dict):
    """Call this after creating a note"""
    await ws_manager.broadcast_to_topic("notes", {
        "type": "note_created",
        "data": note,
    })


async def notify_note_updated(note: dict):
    """Call this after updating a note"""
    await ws_manager.broadcast_to_topic("notes", {
        "type": "note_updated",
        "data": note,
    })


async def notify_goal_progress(goal_id: str, progress: float):
    """Call this after logging goal progress"""
    await ws_manager.broadcast_to_topic("goals", {
        "type": "goal_progress",
        "goalId": goal_id,
        "progress": progress,
    })
    await ws_manager.broadcast_to_topic("dashboard", {
        "type": "dashboard_refresh",
    })
```

### Integrate with FastAPI Server

**File:** `src/api/server.py` (add to existing)

```python
from fastapi import FastAPI, WebSocket
from .websocket import websocket_endpoint, ws_manager, notify_task_created, notify_task_updated

app = FastAPI()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Example: Update task route to broadcast
@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, task_update: TaskUpdate):
    # ... existing update logic ...
    task = update_task_in_db(task_id, task_update)

    # Notify all connected clients
    await notify_task_updated(task.dict())

    return {"success": True, "data": task}
```

---

## 2.5 Testing WebSocket

### Manual Testing

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/ws')

ws.onopen = () => {
  console.log('Connected!')
  ws.send(JSON.stringify({ type: 'subscribe', topics: ['tasks'] }))
}

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data))
}

// Now create a task via API and watch the message appear
```

### Integration Test

```python
# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from src.api.server import app

def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # Subscribe to tasks
        websocket.send_json({"type": "subscribe", "topics": ["tasks"]})

        # Create a task via API (triggers broadcast)
        response = client.post("/api/tasks", json={
            "title": "Test task",
            "priority": 3,
        })
        assert response.status_code == 200

        # Should receive task_created event
        data = websocket.receive_json()
        assert data["type"] == "task_created"
        assert data["data"]["title"] == "Test task"
```

---

## 2.6 Expected Results

### Multi-Device Sync Demo

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   LAPTOP (Browser Tab 1)              PHONE (Browser Tab 2)      │
│   ──────────────────────              ─────────────────────      │
│                                                                  │
│   ┌──────────────────────┐            ┌──────────────────────┐   │
│   │ ○ Review proposal    │            │ ○ Review proposal    │   │
│   │ ○ Call mom           │            │ ○ Call mom           │   │
│   │ ○ Ship feature       │            │ ○ Ship feature       │   │
│   └──────────────────────┘            └──────────────────────┘   │
│                                                                  │
│   User clicks "Complete"                                         │
│   on "Call mom"                                                  │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────────────┐            ┌──────────────────────┐   │
│   │ ○ Review proposal    │◄─WebSocket─┤ ○ Review proposal    │   │
│   │ ✓ Call mom      DONE │────────────►│ ✓ Call mom     DONE │   │
│   │ ○ Ship feature       │  < 50ms    │ ○ Ship feature       │   │
│   └──────────────────────┘            └──────────────────────┘   │
│                                                                  │
│   Both devices update INSTANTLY without page refresh!            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Performance Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| **Update latency** | <50ms | Time from action to other device update |
| **Connection overhead** | <5KB/min | Ping/pong keepalive traffic |
| **Reconnect time** | <5s | Time to reconnect after disconnect |
| **Memory per connection** | <1MB | Server memory per WebSocket |

---

## 2.7 Fallback Strategy

If WebSocket fails, React Query's built-in refetching provides a safety net:

```typescript
// App.tsx - Increase refetch frequency when offline
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min when connected
      refetchInterval: (query) => {
        // If WebSocket disconnected, poll every 30s
        return wsConnected ? false : 30 * 1000
      },
    },
  },
})
```

---

# Implementation Checklist

## Code-Splitting (Phase 2A)

- [ ] Update routes.tsx with React.lazy() for all pages except Dashboard
- [ ] Add default exports to all page components
- [ ] Update page index.ts exports
- [ ] Configure vite.config.ts with manualChunks
- [ ] Lazy load CommandPalette in AppShell
- [ ] Create lazy-loaded StatsChart component
- [ ] Install rollup-plugin-visualizer
- [ ] Add build:analyze script
- [ ] Verify build produces multiple chunks
- [ ] Test all routes load correctly
- [ ] Verify loading spinners appear

## Real-Time Updates (Phase 2B)

- [ ] Create types/websocket.ts with message types
- [ ] Create hooks/useWebSocket.ts
- [ ] Create providers/WebSocketProvider.tsx
- [ ] Create components/common/ConnectionStatus.tsx
- [ ] Update App.tsx with WebSocketProvider
- [ ] Add ConnectionStatus to Header
- [ ] Create src/api/websocket.py (backend)
- [ ] Add WebSocket route to FastAPI server
- [ ] Add notify_* calls to all API mutation routes
- [ ] Update vite.config.ts with /ws proxy
- [ ] Write integration tests
- [ ] Test multi-tab sync

---

## Change Log

| Timestamp | Change | Details |
|-----------|--------|---------|
| 12/30/2025 06:00 AM PST | Plan created | Comprehensive code-splitting and real-time updates plan |
| 12/30/2025 06:40 AM PST | Code-splitting implemented | React.lazy() for routes, manualChunks in Vite, lazy CommandPalette. Build: 220KB main bundle (was 559KB) |
| 12/30/2025 07:09 AM PST | WebSocket implemented | Frontend: types, useWebSocket hook, WebSocketProvider, ConnectionStatus. Backend: WebSocketManager, notify_* helpers, router integration |

---

*This plan will be updated as implementation progresses.*
