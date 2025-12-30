/**
 * API Layer Index
 *
 * Central export for all API-related modules.
 *
 * Architecture:
 * - client.ts: Axios configuration and error handling
 * - endpoints.ts: API functions for each domain
 * - hooks/: React Query hooks for data fetching
 * - mock-data.ts: Development mock data
 *
 * Usage:
 * @example
 * // Import hooks for components
 * import { useTasks, useCreateTask } from '@/api/hooks'
 *
 * // Import API functions for custom logic
 * import { taskApi, calendarApi } from '@/api'
 *
 * // Import client for custom requests
 * import { api, ApiError } from '@/api'
 */

// HTTP client and error handling
export { apiClient, api, ApiError } from './client'

// API endpoint functions
export { taskApi, calendarApi, noteApi, goalApi, projectApi, dashboardApi, nlpApi } from './endpoints'

// Re-export all hooks
export * from './hooks'

// Re-export mock data for development/testing
export {
  mockTasks,
  mockEvents,
  mockNotes,
  mockGoals,
  mockProjects,
  mockDashboardData,
  mockDashboardStats,
  mockGoalSummaries,
  mockActivityItems,
  mockProgressLogs,
  mockParsedInputs,
  simulateDelay,
  cloneDeep,
  createMockTask,
  createMockEvent,
  createMockNote,
  createMockGoal,
} from './mock-data'
