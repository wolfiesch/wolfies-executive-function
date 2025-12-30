/**
 * API Hooks Index
 *
 * Re-exports all React Query hooks for convenient importing.
 *
 * @example
 * import { useTasks, useCreateTask, useDashboardData } from '@/api/hooks'
 */

// Task hooks
export {
  taskKeys,
  useTasks,
  useTask,
  useSubtasks,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useCompleteTask,
  useReopenTask,
  useToggleTaskComplete,
} from './useTasks'

// Calendar hooks
export {
  calendarKeys,
  useEvents,
  useTodayEvents,
  useEvent,
  useCreateEvent,
  useUpdateEvent,
  useDeleteEvent,
  useRescheduleEvent,
} from './useCalendar'

// Note hooks
export {
  noteKeys,
  useNotes,
  useNote,
  useBacklinks,
  useCreateNote,
  useUpdateNote,
  useDeleteNote,
  useToggleNotePin,
  useSearchNotes,
} from './useNotes'

// Goal hooks
export {
  goalKeys,
  useGoals,
  useActiveGoals,
  useGoal,
  useProgressHistory,
  useCreateGoal,
  useUpdateGoal,
  useDeleteGoal,
  useLogProgress,
  useUpdateMilestone,
  useToggleMilestone,
  useArchiveGoal,
  useCompleteGoal,
} from './useGoals'

// Dashboard hooks
export {
  dashboardKeys,
  useDashboardData,
  useNLPParse,
  usePrefetchDashboard,
  useInvalidateDashboard,
  useDashboardStats,
} from './useDashboard'
