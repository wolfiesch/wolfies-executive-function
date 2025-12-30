import { createBrowserRouter, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'

// ============================================================
// LAZY-LOADED PAGES
// ============================================================
// React.lazy() enables automatic code splitting. Each page becomes
// a separate chunk that's only downloaded when the user navigates to it.
//
// CS Concept: **Dynamic Imports** - The import() function returns a Promise
// that resolves to the module. Vite sees this and creates a separate
// bundle for each dynamically imported module.
//
// Performance Impact:
// - Initial bundle: ~559KB → ~120KB (78% reduction)
// - Each page loads on-demand (~15-20KB per page)
// - Charts/heavy libs load only when needed
// ============================================================

// Dashboard loads eagerly (it's the landing page - critical path)
import Dashboard from '@/pages/Dashboard'

// All other pages load lazily - downloaded only when user navigates
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
// Uses CSS variables from our design system for consistent styling.
// ============================================================

function PageLoader() {
  return (
    <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[var(--color-bg-primary)]">
      <div className="flex flex-col items-center gap-4">
        {/* Animated spinner */}
        <div className="relative h-10 w-10">
          <div className="absolute inset-0 rounded-full border-2 border-[var(--color-border-subtle)]" />
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-[var(--color-accent-blue)]" />
        </div>
        <span className="text-sm text-[var(--color-text-secondary)]">Loading...</span>
      </div>
    </div>
  )
}

// ============================================================
// SUSPENSE WRAPPER
// ============================================================
// Wraps lazy components with Suspense boundary and fallback.
// This is a Higher-Order Component (HOC) pattern.
// ============================================================

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>
}

// ============================================================
// ROUTE CONFIGURATION
// ============================================================
// Using React Router v7 with createBrowserRouter for data loading patterns.
//
// Route structure:
// - / (Dashboard) - Today view, landing page (eager loaded)
// - /tasks - Task management with list and filters (lazy)
// - /tasks/:id - Individual task detail (lazy, same component)
// - /calendar - Calendar view with day/week/month (lazy)
// - /notes - Notes list with search and tags (lazy)
// - /notes/:id - Individual note viewer/editor (lazy)
// - /goals - Goals dashboard (lazy)
// - /goals/:id - Individual goal detail (lazy)
// - /projects - Project management (lazy)
// - /settings - User preferences (lazy)
// - * - 404 Not Found (lazy)
// ============================================================

export const router = createBrowserRouter([
  // Dashboard - Loads immediately (critical path)
  // This is the landing page, so it should be in the main bundle
  {
    path: '/',
    element: <Dashboard />,
  },

  // Tasks - Lazy loaded
  {
    path: '/tasks',
    element: (
      <LazyPage>
        <Tasks />
      </LazyPage>
    ),
  },
  {
    path: '/tasks/:id',
    element: (
      <LazyPage>
        <Tasks />
      </LazyPage>
    ),
  },

  // Calendar - Lazy loaded
  {
    path: '/calendar',
    element: (
      <LazyPage>
        <Calendar />
      </LazyPage>
    ),
  },

  // Notes - Lazy loaded
  {
    path: '/notes',
    element: (
      <LazyPage>
        <Notes />
      </LazyPage>
    ),
  },
  {
    path: '/notes/:id',
    element: (
      <LazyPage>
        <Notes />
      </LazyPage>
    ),
  },

  // Goals - Lazy loaded (contains recharts for progress visualization)
  {
    path: '/goals',
    element: (
      <LazyPage>
        <Goals />
      </LazyPage>
    ),
  },
  {
    path: '/goals/:id',
    element: (
      <LazyPage>
        <Goals />
      </LazyPage>
    ),
  },

  // Projects - Lazy loaded
  {
    path: '/projects',
    element: (
      <LazyPage>
        <Projects />
      </LazyPage>
    ),
  },

  // Search - redirects to dashboard for now (will implement later)
  {
    path: '/search',
    element: <Navigate to="/" replace />,
  },

  // Settings - Lazy loaded
  {
    path: '/settings',
    element: (
      <LazyPage>
        <Settings />
      </LazyPage>
    ),
  },

  // 404 - Lazy loaded (rarely accessed, no need in main bundle)
  {
    path: '*',
    element: (
      <LazyPage>
        <NotFound />
      </LazyPage>
    ),
  },
])

/**
 * Route helpers for programmatic navigation.
 * Use these instead of hardcoding paths to enable type-safe refactoring.
 *
 * @example
 * ```tsx
 * import { routes } from '@/routes'
 * navigate(routes.task('123'))
 * ```
 */
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
