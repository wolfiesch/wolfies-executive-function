/**
 * Dashboard React Query hooks
 *
 * Provides a combined data hook for the dashboard view.
 * Aggregates multiple data sources for efficient loading.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardApi, taskApi, calendarApi, nlpApi } from '../endpoints'

// Query key factory
export const dashboardKeys = {
  all: ['dashboard'] as const,
  data: () => [...dashboardKeys.all, 'data'] as const,
  nlp: (input: string) => [...dashboardKeys.all, 'nlp', input] as const,
}

/**
 * Fetch all dashboard data in one request
 *
 * Returns combined stats, priority tasks, upcoming events,
 * goal summaries, and recent activity.
 *
 * This is more efficient than making multiple requests because:
 * 1. Single network round-trip instead of multiple
 * 2. Backend can optimize the aggregation
 * 3. Consistent snapshot of data at a point in time
 *
 * @returns Query result with dashboard data
 *
 * @example
 * const { data, isLoading } = useDashboardData()
 * if (isLoading) return <DashboardSkeleton />
 * return <Dashboard data={data} />
 */
export function useDashboardData() {
  return useQuery({
    queryKey: dashboardKeys.data(),
    queryFn: () => dashboardApi.getData(),
    // Dashboard data should be fresh, but don't refetch too aggressively
    staleTime: 30 * 1000,
    // Keep previous data while refetching for smooth UX
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Parse natural language input
 *
 * Converts user input like "remind me to call mom tomorrow at 3pm"
 * into structured data for task/event creation.
 *
 * @param input - Natural language input string
 * @returns Query result with parsed input structure
 *
 * @example
 * const [inputText, setInputText] = useState('')
 * const { data: parsed } = useNLPParse(inputText)
 *
 * // parsed might be:
 * // {
 * //   type: 'task',
 * //   title: 'Call mom',
 * //   due_date: '2024-01-16',
 * //   due_time: '15:00',
 * // }
 */
export function useNLPParse(input: string) {
  return useQuery({
    queryKey: dashboardKeys.nlp(input),
    queryFn: () => nlpApi.parse(input),
    // Only run when we have meaningful input
    enabled: input.length >= 3,
    // Don't refetch on window focus for typed input
    refetchOnWindowFocus: false,
    // Cache parsed results
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Prefetch dashboard data
 *
 * Use this to eagerly load dashboard data before navigating.
 * Useful for hover-to-prefetch patterns or app startup.
 *
 * @returns Prefetch function
 *
 * @example
 * const prefetchDashboard = usePrefetchDashboard()
 *
 * // On hover over dashboard link
 * <Link onMouseEnter={prefetchDashboard}>Dashboard</Link>
 */
export function usePrefetchDashboard() {
  const queryClient = useQueryClient()

  return () => {
    queryClient.prefetchQuery({
      queryKey: dashboardKeys.data(),
      queryFn: () => dashboardApi.getData(),
      staleTime: 30 * 1000,
    })
  }
}

/**
 * Invalidate dashboard data
 *
 * Call this after mutations that affect dashboard data
 * (task completion, event creation, etc.)
 *
 * @returns Invalidate function
 */
export function useInvalidateDashboard() {
  const queryClient = useQueryClient()

  return () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.data() })
  }
}

/**
 * Dashboard stats derived from real-time task data
 *
 * Alternative approach that computes stats from cached task data.
 * Useful when you want stats to update immediately after mutations.
 */
export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats', 'computed'],
    queryFn: async () => {
      const today = new Date()
      const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())
      const todayEnd = new Date(todayStart.getTime() + 24 * 60 * 60 * 1000)

      // Fetch fresh data for accurate stats
      const [allTasks, todayEvents] = await Promise.all([
        taskApi.list(),
        calendarApi.list(todayStart.toISOString(), todayEnd.toISOString()),
      ])

      const todayTasks = allTasks.filter((t) => {
        if (!t.due_date) return false
        const dueDate = new Date(t.due_date)
        return dueDate >= todayStart && dueDate < todayEnd
      })

      const overdueTasks = allTasks.filter((t) => {
        if (!t.due_date || t.status === 'done' || t.status === 'cancelled') return false
        return new Date(t.due_date) < todayStart
      })

      const completedToday = todayTasks.filter((t) => t.status === 'done').length
      const totalToday = todayTasks.length

      return {
        tasks_today: totalToday,
        tasks_overdue: overdueTasks.length,
        completion_rate: totalToday > 0 ? Math.round((completedToday / totalToday) * 100) : 0,
        events_today: todayEvents.length,
        pending_tasks: allTasks.filter((t) => t.status === 'todo' || t.status === 'in_progress').length,
      }
    },
    staleTime: 30 * 1000,
  })
}
