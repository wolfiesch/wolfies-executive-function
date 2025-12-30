/**
 * Task-related React Query hooks
 *
 * Provides data fetching and mutation hooks for task operations.
 * Includes optimistic updates for a snappy user experience.
 *
 * Key patterns:
 * - Query keys include all filters for proper cache invalidation
 * - Optimistic updates for mutations that affect UI immediately
 * - Automatic cache invalidation after mutations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { taskApi } from '../endpoints'
import type { Task, TaskCreateInput, TaskUpdateInput, TaskFilters } from '@/types/models'

// Query key factory for consistent cache management
// This pattern (sometimes called "query key factory") helps organize cache keys
// and ensures related queries are invalidated together
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters?: TaskFilters) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  subtasks: (parentId: string) => [...taskKeys.all, 'subtasks', parentId] as const,
}

/**
 * Fetch tasks with optional filtering
 *
 * @param filters - Optional filters for status, priority, life area, etc.
 * @returns Query result with tasks array
 *
 * @example
 * // Get all tasks
 * const { data: tasks } = useTasks()
 *
 * // Get only high priority incomplete tasks
 * const { data: tasks } = useTasks({ status: ['todo', 'in_progress'], priority: [4, 5] })
 */
export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () => taskApi.list(filters),
    // Data is considered fresh for 30 seconds
    // After that, it will refetch in background on next access
    staleTime: 30 * 1000,
  })
}

/**
 * Fetch a single task by ID
 *
 * @param id - Task ID
 * @returns Query result with single task
 */
export function useTask(id: string) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => taskApi.get(id),
    // Only run query if we have an ID
    enabled: !!id,
  })
}

/**
 * Fetch subtasks for a parent task
 *
 * @param parentId - Parent task ID
 * @returns Query result with subtasks array
 */
export function useSubtasks(parentId: string) {
  return useQuery({
    queryKey: taskKeys.subtasks(parentId),
    queryFn: () => taskApi.getSubtasks(parentId),
    enabled: !!parentId,
  })
}

/**
 * Create a new task
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const createTask = useCreateTask()
 * createTask.mutate({ title: 'New task', priority: 3 })
 */
export function useCreateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: TaskCreateInput) => taskApi.create(input),
    onSuccess: () => {
      // Invalidate all task lists to refetch with new task
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/**
 * Update an existing task
 *
 * Uses optimistic updates: the UI updates immediately while the
 * request is in flight, then reconciles with server response.
 *
 * @returns Mutation object with mutate function
 */
export function useUpdateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: TaskUpdateInput }) => taskApi.update(id, input),
    // Optimistic update: update cache immediately before server responds
    onMutate: async ({ id, input }) => {
      // Cancel any outgoing refetches to prevent race conditions
      await queryClient.cancelQueries({ queryKey: taskKeys.detail(id) })

      // Snapshot current value for rollback
      const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(id))

      // Optimistically update the cache
      if (previousTask) {
        queryClient.setQueryData<Task>(taskKeys.detail(id), {
          ...previousTask,
          ...input,
          updated_at: new Date().toISOString(),
        })
      }

      // Return context for rollback
      return { previousTask }
    },
    // If mutation fails, rollback to previous value
    onError: (_error, { id }, context) => {
      if (context?.previousTask) {
        queryClient.setQueryData(taskKeys.detail(id), context.previousTask)
      }
    },
    // After success or failure, invalidate to ensure consistency
    onSettled: (_data, _error, { id }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/**
 * Delete a task
 *
 * @returns Mutation object with mutate function
 */
export function useDeleteTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => taskApi.delete(id),
    onSuccess: (_data, id) => {
      // Remove from detail cache
      queryClient.removeQueries({ queryKey: taskKeys.detail(id) })
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/**
 * Mark a task as complete
 *
 * Uses optimistic updates for instant feedback. The checkbox
 * updates immediately even before server confirmation.
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const completeTask = useCompleteTask()
 * // In a checkbox onChange handler:
 * completeTask.mutate(task.id)
 */
export function useCompleteTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => taskApi.complete(id),
    // Optimistic update
    onMutate: async (id) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: taskKeys.detail(id) })
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() })

      // Snapshot for rollback
      const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(id))

      // Optimistically update detail cache
      if (previousTask) {
        queryClient.setQueryData<Task>(taskKeys.detail(id), {
          ...previousTask,
          status: 'done',
          completed_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
      }

      // Also update the task in list caches
      queryClient.setQueriesData<Task[]>({ queryKey: taskKeys.lists() }, (old) => {
        if (!old) return old
        return old.map((task) =>
          task.id === id
            ? {
                ...task,
                status: 'done' as const,
                completed_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              }
            : task
        )
      })

      return { previousTask }
    },
    onError: (_error, id, context) => {
      // Rollback on error
      if (context?.previousTask) {
        queryClient.setQueryData(taskKeys.detail(id), context.previousTask)
      }
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/**
 * Reopen a completed task
 *
 * @returns Mutation object with mutate function
 */
export function useReopenTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => taskApi.reopen(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: taskKeys.detail(id) })
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() })

      const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(id))

      if (previousTask) {
        queryClient.setQueryData<Task>(taskKeys.detail(id), {
          ...previousTask,
          status: 'todo',
          completed_at: undefined,
          updated_at: new Date().toISOString(),
        })
      }

      queryClient.setQueriesData<Task[]>({ queryKey: taskKeys.lists() }, (old) => {
        if (!old) return old
        return old.map((task) =>
          task.id === id
            ? {
                ...task,
                status: 'todo' as const,
                completed_at: undefined,
                updated_at: new Date().toISOString(),
              }
            : task
        )
      })

      return { previousTask }
    },
    onError: (_error, id, context) => {
      if (context?.previousTask) {
        queryClient.setQueryData(taskKeys.detail(id), context.previousTask)
      }
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() })
    },
  })
}

/**
 * Toggle task completion status
 *
 * Convenience hook that checks current status and calls
 * complete or reopen accordingly.
 */
export function useToggleTaskComplete() {
  const completeTask = useCompleteTask()
  const reopenTask = useReopenTask()

  return {
    mutate: (task: Task) => {
      if (task.status === 'done') {
        reopenTask.mutate(task.id)
      } else {
        completeTask.mutate(task.id)
      }
    },
    isPending: completeTask.isPending || reopenTask.isPending,
  }
}
