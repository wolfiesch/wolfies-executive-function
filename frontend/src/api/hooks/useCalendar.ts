/**
 * Calendar event React Query hooks
 *
 * Provides data fetching and mutation hooks for calendar operations.
 * Optimized for date-range based queries common in calendar views.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { calendarApi } from '../endpoints'
import type { CalendarEvent, CalendarEventCreateInput } from '@/types/models'

// Query key factory
export const calendarKeys = {
  all: ['events'] as const,
  lists: () => [...calendarKeys.all, 'list'] as const,
  list: (startDate: string, endDate: string) => [...calendarKeys.lists(), startDate, endDate] as const,
  details: () => [...calendarKeys.all, 'detail'] as const,
  detail: (id: string) => [...calendarKeys.details(), id] as const,
  today: () => [...calendarKeys.all, 'today'] as const,
}

/**
 * Fetch events within a date range
 *
 * @param startDate - Start of date range (ISO string)
 * @param endDate - End of date range (ISO string)
 * @returns Query result with events array
 *
 * @example
 * // Get events for current week
 * const startOfWeek = startOfWeek(new Date())
 * const endOfWeek = endOfWeek(new Date())
 * const { data: events } = useEvents(startOfWeek.toISOString(), endOfWeek.toISOString())
 */
export function useEvents(startDate: string, endDate: string) {
  return useQuery({
    queryKey: calendarKeys.list(startDate, endDate),
    queryFn: () => calendarApi.list(startDate, endDate),
    staleTime: 60 * 1000, // 1 minute - calendar data changes less frequently
    enabled: !!startDate && !!endDate,
  })
}

/**
 * Fetch today's events
 *
 * Convenience hook for dashboard and quick views.
 * Uses a stable query key that resets at midnight.
 */
export function useTodayEvents() {
  return useQuery({
    queryKey: calendarKeys.today(),
    queryFn: () => calendarApi.getToday(),
    staleTime: 30 * 1000,
  })
}

/**
 * Fetch a single event by ID
 *
 * @param id - Event ID
 * @returns Query result with single event
 */
export function useEvent(id: string) {
  return useQuery({
    queryKey: calendarKeys.detail(id),
    queryFn: () => calendarApi.get(id),
    enabled: !!id,
  })
}

/**
 * Create a new calendar event
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const createEvent = useCreateEvent()
 * createEvent.mutate({
 *   title: 'Team Meeting',
 *   start_time: '2024-01-15T14:00:00Z',
 *   end_time: '2024-01-15T15:00:00Z',
 * })
 */
export function useCreateEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: CalendarEventCreateInput) => calendarApi.create(input),
    onSuccess: () => {
      // Invalidate all event lists to include new event
      queryClient.invalidateQueries({ queryKey: calendarKeys.lists() })
      queryClient.invalidateQueries({ queryKey: calendarKeys.today() })
    },
  })
}

/**
 * Update an existing calendar event
 *
 * Uses optimistic updates for drag-and-drop rescheduling.
 *
 * @returns Mutation object with mutate function
 */
export function useUpdateEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<CalendarEventCreateInput> }) =>
      calendarApi.update(id, input),
    onMutate: async ({ id, input }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: calendarKeys.detail(id) })

      // Snapshot for rollback
      const previousEvent = queryClient.getQueryData<CalendarEvent>(calendarKeys.detail(id))

      // Optimistically update detail
      if (previousEvent) {
        queryClient.setQueryData<CalendarEvent>(calendarKeys.detail(id), {
          ...previousEvent,
          ...input,
          updated_at: new Date().toISOString(),
        })
      }

      return { previousEvent }
    },
    onError: (_error, { id }, context) => {
      if (context?.previousEvent) {
        queryClient.setQueryData(calendarKeys.detail(id), context.previousEvent)
      }
    },
    onSettled: (_data, _error, { id }) => {
      queryClient.invalidateQueries({ queryKey: calendarKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: calendarKeys.lists() })
      queryClient.invalidateQueries({ queryKey: calendarKeys.today() })
    },
  })
}

/**
 * Delete a calendar event
 *
 * @returns Mutation object with mutate function
 */
export function useDeleteEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => calendarApi.delete(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: calendarKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: calendarKeys.lists() })
      queryClient.invalidateQueries({ queryKey: calendarKeys.today() })
    },
  })
}

/**
 * Reschedule an event (update start and end times)
 *
 * Convenience mutation for drag-and-drop operations.
 * Optimized for the common case of only changing times.
 */
export function useRescheduleEvent() {
  const updateEvent = useUpdateEvent()

  return {
    mutate: (id: string, startTime: string, endTime: string) => {
      updateEvent.mutate({
        id,
        input: { start_time: startTime, end_time: endTime },
      })
    },
    isPending: updateEvent.isPending,
    isError: updateEvent.isError,
    error: updateEvent.error,
  }
}
