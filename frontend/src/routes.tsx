import { createBrowserRouter, Navigate } from 'react-router-dom'
import {
  Dashboard,
  Tasks,
  Calendar,
  Notes,
  Goals,
  Projects,
  Settings,
  NotFound,
} from '@/pages'

/**
 * Application route configuration using React Router v7.
 *
 * Route structure:
 * - / (Dashboard) - Today view, landing page
 * - /tasks - Task management with list and filters
 * - /tasks/:id - Individual task detail (loads in right panel or full page)
 * - /calendar - Calendar view with day/week/month
 * - /notes - Notes list with search and tags
 * - /notes/:id - Individual note viewer/editor
 * - /goals - Goals dashboard
 * - /goals/:id - Individual goal detail
 * - /projects - Project management
 * - /search - Global search results (TODO: implement)
 * - /settings - User preferences
 * - * - 404 Not Found
 *
 * Design pattern: **Route Configuration Object** - centralizes route definitions
 * making it easier to understand the app structure and add new routes.
 *
 * CS concept: **Code Splitting with Lazy Loading** - for production, consider
 * using React.lazy() for page components to enable automatic code splitting.
 * This means each page's code is only downloaded when the user navigates to it.
 */
export const router = createBrowserRouter([
  // Dashboard - Today view (landing page)
  {
    path: '/',
    element: <Dashboard />,
  },

  // Tasks
  {
    path: '/tasks',
    element: <Tasks />,
  },
  {
    path: '/tasks/:id',
    element: <Tasks />, // Same page, opens detail in right panel
  },

  // Calendar
  {
    path: '/calendar',
    element: <Calendar />,
  },

  // Notes
  {
    path: '/notes',
    element: <Notes />,
  },
  {
    path: '/notes/:id',
    element: <Notes />, // Same page, opens note in editor panel
  },

  // Goals
  {
    path: '/goals',
    element: <Goals />,
  },
  {
    path: '/goals/:id',
    element: <Goals />, // Same page, opens goal detail
  },

  // Projects
  {
    path: '/projects',
    element: <Projects />,
  },

  // Search (redirects to dashboard for now, will implement later)
  {
    path: '/search',
    element: <Navigate to="/" replace />,
  },

  // Settings
  {
    path: '/settings',
    element: <Settings />,
  },

  // 404 - Not Found (catch-all)
  {
    path: '*',
    element: <NotFound />,
  },
])

/**
 * Route helpers for programmatic navigation.
 * Use these instead of hardcoding paths to enable type-safe refactoring.
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
