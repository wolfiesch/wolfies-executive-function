/**
 * Notes React Query hooks
 *
 * Provides data fetching and mutation hooks for note operations.
 * Supports the PKM (Personal Knowledge Management) features like backlinks.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { noteApi } from '../endpoints'
import type { Note, NoteCreateInput, NoteFilters } from '@/types/models'

// Query key factory
export const noteKeys = {
  all: ['notes'] as const,
  lists: () => [...noteKeys.all, 'list'] as const,
  list: (filters?: NoteFilters) => [...noteKeys.lists(), filters] as const,
  details: () => [...noteKeys.all, 'detail'] as const,
  detail: (id: string) => [...noteKeys.details(), id] as const,
  backlinks: (id: string) => [...noteKeys.all, 'backlinks', id] as const,
}

/**
 * Fetch notes with optional filtering
 *
 * @param filters - Optional filters for note_type, life_area, tags, search
 * @returns Query result with notes array
 *
 * @example
 * // Get all notes
 * const { data: notes } = useNotes()
 *
 * // Get journal entries only
 * const { data: journals } = useNotes({ note_type: ['journal'] })
 *
 * // Search notes
 * const { data: results } = useNotes({ search: 'architecture' })
 */
export function useNotes(filters?: NoteFilters) {
  return useQuery({
    queryKey: noteKeys.list(filters),
    queryFn: () => noteApi.list(filters),
    staleTime: 30 * 1000,
  })
}

/**
 * Fetch a single note by ID
 *
 * @param id - Note ID
 * @returns Query result with single note
 */
export function useNote(id: string) {
  return useQuery({
    queryKey: noteKeys.detail(id),
    queryFn: () => noteApi.get(id),
    enabled: !!id,
  })
}

/**
 * Fetch backlinks for a note
 *
 * Returns notes that link TO the given note.
 * Essential for PKM bi-directional linking feature.
 *
 * @param noteId - Note ID to find backlinks for
 * @returns Query result with array of linking notes
 */
export function useBacklinks(noteId: string) {
  return useQuery({
    queryKey: noteKeys.backlinks(noteId),
    queryFn: () => noteApi.getBacklinks(noteId),
    enabled: !!noteId,
    // Backlinks change less frequently
    staleTime: 60 * 1000,
  })
}

/**
 * Create a new note
 *
 * @returns Mutation object with mutate function
 *
 * @example
 * const createNote = useCreateNote()
 * createNote.mutate({
 *   title: 'Meeting Notes',
 *   content: '# Meeting with team...',
 *   note_type: 'meeting',
 * })
 */
export function useCreateNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: NoteCreateInput) => noteApi.create(input),
    onSuccess: (newNote) => {
      // Invalidate lists to include new note
      queryClient.invalidateQueries({ queryKey: noteKeys.lists() })

      // Pre-populate the detail cache for immediate access
      queryClient.setQueryData(noteKeys.detail(newNote.id), newNote)
    },
  })
}

/**
 * Update an existing note
 *
 * Uses optimistic updates for smooth editing experience.
 *
 * @returns Mutation object with mutate function
 */
export function useUpdateNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<NoteCreateInput> & { is_pinned?: boolean } }) =>
      noteApi.update(id, input),
    onMutate: async ({ id, input }) => {
      await queryClient.cancelQueries({ queryKey: noteKeys.detail(id) })

      const previousNote = queryClient.getQueryData<Note>(noteKeys.detail(id))

      if (previousNote) {
        const content = input.content ?? previousNote.content
        queryClient.setQueryData<Note>(noteKeys.detail(id), {
          ...previousNote,
          ...input,
          word_count: content.split(/\s+/).filter(Boolean).length,
          updated_at: new Date().toISOString(),
        })
      }

      return { previousNote }
    },
    onError: (_error, { id }, context) => {
      if (context?.previousNote) {
        queryClient.setQueryData(noteKeys.detail(id), context.previousNote)
      }
    },
    onSettled: (_data, _error, { id }) => {
      queryClient.invalidateQueries({ queryKey: noteKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: noteKeys.lists() })
      // Backlinks might have changed if content includes [[links]]
      queryClient.invalidateQueries({ queryKey: ['notes', 'backlinks'] })
    },
  })
}

/**
 * Delete a note
 *
 * @returns Mutation object with mutate function
 */
export function useDeleteNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => noteApi.delete(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: noteKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: noteKeys.lists() })
      // Other notes might have had backlinks to this note
      queryClient.invalidateQueries({ queryKey: ['notes', 'backlinks'] })
    },
  })
}

/**
 * Toggle note pin status
 *
 * Pinned notes appear at the top of lists.
 *
 * @returns Mutation object with mutate function
 */
export function useToggleNotePin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => noteApi.togglePin(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: noteKeys.detail(id) })

      const previousNote = queryClient.getQueryData<Note>(noteKeys.detail(id))

      if (previousNote) {
        queryClient.setQueryData<Note>(noteKeys.detail(id), {
          ...previousNote,
          is_pinned: !previousNote.is_pinned,
          updated_at: new Date().toISOString(),
        })
      }

      // Also update in list caches
      queryClient.setQueriesData<Note[]>({ queryKey: noteKeys.lists() }, (old) => {
        if (!old) return old
        return old.map((note) =>
          note.id === id
            ? {
                ...note,
                is_pinned: !note.is_pinned,
                updated_at: new Date().toISOString(),
              }
            : note
        )
      })

      return { previousNote }
    },
    onError: (_error, id, context) => {
      if (context?.previousNote) {
        queryClient.setQueryData(noteKeys.detail(id), context.previousNote)
      }
      queryClient.invalidateQueries({ queryKey: noteKeys.lists() })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.lists() })
    },
  })
}

/**
 * Search notes by content
 *
 * Convenience hook that wraps useNotes with search filter.
 *
 * @param query - Search query string
 * @returns Query result with matching notes
 */
export function useSearchNotes(query: string) {
  return useNotes(query ? { search: query } : undefined)
}
