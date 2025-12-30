/**
 * Goals React Query hooks
 *
 * Provides data fetching and mutation hooks for goal operations.
 * Includes specialized hooks for progress logging and milestone management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { goalApi } from '../endpoints'
import type { Goal, GoalCreateInput, GoalFilters, Milestone } from '@/types/models'

// Query key factory
export const goalKeys = {
  all: ['goals'] as const,
  lists: () => [...goalKeys.all, 'list'] as const,
  list: (filters?: GoalFilters) => [...goalKeys.lists(), filters] as const,
  details: () => [...goalKeys.all, 'detail'] as const,
  detail: (id: string) => [...goalKeys.details(), id] as const,
  progress: (id: string) => [...goalKeys.all, 'progress', id] as const,
}

/**
 * Fetch goals with optional filtering
 *
 * @param filters - Optional filters for status, life_area
 * @returns Query result with goals array
 *
 * @example
 * // Get all active goals
 * const { data: goals } = useGoals({ status: ['active'] })
 *
 * // Get health goals
 * const { data: healthGoals } = useGoals({ life_area: ['health'] })
 */
export function useGoals(filters?: GoalFilters) {
  return useQuery({
    queryKey: goalKeys.list(filters),
    queryFn: () => goalApi.list(filters),
    staleTime: 60 * 1000, // Goals change less frequently
  })
}

/**
 * Fetch only active goals
 *
 * Convenience hook for dashboard and common views.
 */
export function useActiveGoals() {
  return useGoals({ status: ['active'] })
}

/**
 * Fetch a single goal by ID
 *
 * @param id - Goal ID
 * @returns Query result with single goal
 */
export function useGoal(id: string) {
  return useQuery({
    queryKey: goalKeys.detail(id),
    queryFn: () => goalApi.get(id),
    enabled: !!id,
  })
}

/**
 * Fetch progress history for a goal
 *
 * Returns all progress log entries for tracking over time.
 *
 * @param goalId - Goal ID
 * @returns Query result with progress logs array
 */
export function useProgressHistory(goalId: string) {
  return useQuery({
    queryKey: goalKeys.progress(goalId),
    queryFn: () => goalApi.getProgressHistory(goalId),
    enabled: !!goalId,
  })
}

/**
 * Create a new goal
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const createGoal = useCreateGoal()
 * createGoal.mutate({
 *   title: 'Run a marathon',
 *   life_area: 'health',
 *   target_date: '2025-06-01',
 *   milestones: [
 *     { title: 'Run 5K' },
 *     { title: 'Run 10K' },
 *     { title: 'Run half marathon' },
 *   ],
 * })
 */
export function useCreateGoal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: GoalCreateInput) => goalApi.create(input),
    onSuccess: (newGoal) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() })
      queryClient.setQueryData(goalKeys.detail(newGoal.id), newGoal)
    },
  })
}

/**
 * Update an existing goal
 *
 * @returns Mutation object with mutate function
 */
export function useUpdateGoal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string
      input: Partial<GoalCreateInput> & { status?: string; progress?: number }
    }) => goalApi.update(id, input),
    onMutate: async ({ id, input }) => {
      await queryClient.cancelQueries({ queryKey: goalKeys.detail(id) })

      const previousGoal = queryClient.getQueryData<Goal>(goalKeys.detail(id))

      if (previousGoal) {
        queryClient.setQueryData<Goal>(goalKeys.detail(id), {
          ...previousGoal,
          ...input,
          updated_at: new Date().toISOString(),
        } as Goal)
      }

      return { previousGoal }
    },
    onError: (_error, { id }, context) => {
      if (context?.previousGoal) {
        queryClient.setQueryData(goalKeys.detail(id), context.previousGoal)
      }
    },
    onSettled: (_data, _error, { id }) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() })
    },
  })
}

/**
 * Delete a goal
 *
 * @returns Mutation object with mutate function
 */
export function useDeleteGoal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => goalApi.delete(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: goalKeys.detail(id) })
      queryClient.removeQueries({ queryKey: goalKeys.progress(id) })
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() })
    },
  })
}

/**
 * Log progress on a goal
 *
 * Adds a progress entry and updates the goal's current progress.
 * Essential for tracking goal advancement over time.
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const logProgress = useLogProgress()
 * logProgress.mutate({
 *   goalId: 'goal-1',
 *   delta: 5, // Increase progress by 5%
 *   note: 'Completed morning run',
 * })
 */
export function useLogProgress() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ goalId, delta, note }: { goalId: string; delta: number; note?: string }) =>
      goalApi.logProgress(goalId, delta, note),
    onMutate: async ({ goalId, delta }) => {
      await queryClient.cancelQueries({ queryKey: goalKeys.detail(goalId) })

      const previousGoal = queryClient.getQueryData<Goal>(goalKeys.detail(goalId))

      // Optimistically update progress
      if (previousGoal) {
        const newProgress = Math.min(100, Math.max(0, previousGoal.progress + delta))
        queryClient.setQueryData<Goal>(goalKeys.detail(goalId), {
          ...previousGoal,
          progress: newProgress,
          updated_at: new Date().toISOString(),
        })
      }

      return { previousGoal }
    },
    onError: (_error, { goalId }, context) => {
      if (context?.previousGoal) {
        queryClient.setQueryData(goalKeys.detail(goalId), context.previousGoal)
      }
    },
    onSettled: (_data, _error, { goalId }) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(goalId) })
      queryClient.invalidateQueries({ queryKey: goalKeys.progress(goalId) })
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() })
    },
  })
}

/**
 * Update a milestone completion status
 *
 * Automatically recalculates goal progress based on milestone completion.
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const updateMilestone = useUpdateMilestone()
 * updateMilestone.mutate({
 *   goalId: 'goal-1',
 *   milestoneId: 'm1',
 *   completed: true,
 * })
 */
export function useUpdateMilestone() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ goalId, milestoneId, completed }: { goalId: string; milestoneId: string; completed: boolean }) =>
      goalApi.updateMilestone(goalId, milestoneId, completed),
    onMutate: async ({ goalId, milestoneId, completed }) => {
      await queryClient.cancelQueries({ queryKey: goalKeys.detail(goalId) })

      const previousGoal = queryClient.getQueryData<Goal>(goalKeys.detail(goalId))

      if (previousGoal) {
        // Update milestone
        const updatedMilestones = previousGoal.milestones.map((m) =>
          m.id === milestoneId
            ? {
                ...m,
                completed,
                completed_at: completed ? new Date().toISOString() : undefined,
              }
            : m
        )

        // Recalculate progress
        const completedCount = updatedMilestones.filter((m) => m.completed).length
        const progress = Math.round((completedCount / updatedMilestones.length) * 100)

        queryClient.setQueryData<Goal>(goalKeys.detail(goalId), {
          ...previousGoal,
          milestones: updatedMilestones,
          progress,
          updated_at: new Date().toISOString(),
        })
      }

      return { previousGoal }
    },
    onError: (_error, { goalId }, context) => {
      if (context?.previousGoal) {
        queryClient.setQueryData(goalKeys.detail(goalId), context.previousGoal)
      }
    },
    onSettled: (_data, _error, { goalId }) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(goalId) })
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() })
    },
  })
}

/**
 * Toggle milestone completion
 *
 * Convenience hook that checks current state and toggles.
 */
export function useToggleMilestone() {
  const updateMilestone = useUpdateMilestone()

  return {
    mutate: (goalId: string, milestone: Milestone) => {
      updateMilestone.mutate({
        goalId,
        milestoneId: milestone.id,
        completed: !milestone.completed,
      })
    },
    isPending: updateMilestone.isPending,
  }
}

/**
 * Archive a goal
 *
 * Sets goal status to 'archived'.
 */
export function useArchiveGoal() {
  const updateGoal = useUpdateGoal()

  return {
    mutate: (id: string) => {
      updateGoal.mutate({ id, input: { status: 'archived' } })
    },
    isPending: updateGoal.isPending,
  }
}

/**
 * Complete a goal
 *
 * Sets goal status to 'completed' and progress to 100%.
 */
export function useCompleteGoal() {
  const updateGoal = useUpdateGoal()

  return {
    mutate: (id: string) => {
      updateGoal.mutate({ id, input: { status: 'completed', progress: 100 } })
    },
    isPending: updateGoal.isPending,
  }
}
