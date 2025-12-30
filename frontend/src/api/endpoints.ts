/**
 * API endpoint definitions
 *
 * Provides typed API functions for all CRUD operations.
 * Currently returns mock data; designed to easily switch to real API.
 *
 * Pattern: Each API module exports typed functions that handle
 * request/response transformation. The hooks layer uses these
 * functions with React Query for caching and state management.
 */

import { api } from './client'
import {
  mockTasks,
  mockEvents,
  mockNotes,
  mockGoals,
  mockProjects,
  mockDashboardData,
  mockProgressLogs,
  mockParsedInputs,
  simulateDelay,
  cloneDeep,
  createMockTask,
  createMockEvent,
  createMockNote,
  createMockGoal,
} from './mock-data'
import type {
  Task,
  TaskCreateInput,
  TaskUpdateInput,
  TaskFilters,
  CalendarEvent,
  CalendarEventCreateInput,
  Note,
  NoteCreateInput,
  NoteFilters,
  Goal,
  GoalCreateInput,
  GoalFilters,
  Project,
  DashboardData,
  ProgressLog,
  ParsedInput,
} from '@/types/models'

// Flag to toggle between mock and real API
// Set to true when backend is ready
const USE_REAL_API = true

// ============================================================================
// Tasks API
// ============================================================================

export const taskApi = {
  /**
   * List tasks with optional filters
   */
  async list(filters?: TaskFilters): Promise<Task[]> {
    if (USE_REAL_API) {
      const response = await api.get<{ tasks: Task[]; total: number }>('/tasks', filters as Record<string, unknown>)
      return response.tasks
    }

    await simulateDelay()
    let tasks = cloneDeep(mockTasks)

    if (filters) {
      if (filters.status?.length) {
        tasks = tasks.filter((t) => filters.status!.includes(t.status))
      }
      if (filters.priority?.length) {
        tasks = tasks.filter((t) => filters.priority!.includes(t.priority))
      }
      if (filters.life_area?.length) {
        tasks = tasks.filter((t) => t.life_area && filters.life_area!.includes(t.life_area))
      }
      if (filters.project_id) {
        tasks = tasks.filter((t) => t.project_id === filters.project_id)
      }
      if (filters.has_due_date) {
        tasks = tasks.filter((t) => !!t.due_date)
      }
      if (filters.overdue_only) {
        const now = new Date()
        tasks = tasks.filter((t) => t.due_date && new Date(t.due_date) < now && t.status !== 'done')
      }
      if (filters.search) {
        const search = filters.search.toLowerCase()
        tasks = tasks.filter(
          (t) =>
            t.title.toLowerCase().includes(search) ||
            t.description?.toLowerCase().includes(search) ||
            t.tags.some((tag) => tag.toLowerCase().includes(search))
        )
      }
    }

    return tasks
  },

  /**
   * Get a single task by ID
   */
  async get(id: string): Promise<Task> {
    if (USE_REAL_API) {
      return api.get<Task>(`/tasks/${id}`)
    }

    await simulateDelay()
    const task = mockTasks.find((t) => t.id === id)
    if (!task) {
      throw new Error(`Task not found: ${id}`)
    }
    return cloneDeep(task)
  },

  /**
   * Create a new task
   */
  async create(input: TaskCreateInput): Promise<Task> {
    if (USE_REAL_API) {
      return api.post<Task>('/tasks', input)
    }

    await simulateDelay()
    const newTask = createMockTask({
      ...input,
      status: 'todo',
      tags: input.tags || [],
    })
    mockTasks.push(newTask)
    return cloneDeep(newTask)
  },

  /**
   * Update an existing task
   */
  async update(id: string, input: TaskUpdateInput): Promise<Task> {
    if (USE_REAL_API) {
      return api.patch<Task>(`/tasks/${id}`, input)
    }

    await simulateDelay()
    const index = mockTasks.findIndex((t) => t.id === id)
    if (index === -1) {
      throw new Error(`Task not found: ${id}`)
    }

    const updatedTask = {
      ...mockTasks[index],
      ...input,
      updated_at: new Date().toISOString(),
    }
    mockTasks[index] = updatedTask
    return cloneDeep(updatedTask)
  },

  /**
   * Delete a task
   */
  async delete(id: string): Promise<void> {
    if (USE_REAL_API) {
      return api.delete(`/tasks/${id}`)
    }

    await simulateDelay()
    const index = mockTasks.findIndex((t) => t.id === id)
    if (index !== -1) {
      mockTasks.splice(index, 1)
    }
  },

  /**
   * Mark a task as complete
   */
  async complete(id: string): Promise<Task> {
    if (USE_REAL_API) {
      // Backend returns AgentResponse, extract the task from data
      const response = await api.patch<{ success: boolean; message: string; data?: { task?: Task } }>(`/tasks/${id}/complete`)
      if (response.data?.task) {
        return response.data.task
      }
      // If no task in response, fetch it
      return this.get(id)
    }

    await simulateDelay()
    const index = mockTasks.findIndex((t) => t.id === id)
    if (index === -1) {
      throw new Error(`Task not found: ${id}`)
    }

    mockTasks[index] = {
      ...mockTasks[index],
      status: 'done',
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    return cloneDeep(mockTasks[index])
  },

  /**
   * Reopen a completed task
   */
  async reopen(id: string): Promise<Task> {
    if (USE_REAL_API) {
      return api.post<Task>(`/tasks/${id}/reopen`)
    }

    await simulateDelay()
    const index = mockTasks.findIndex((t) => t.id === id)
    if (index === -1) {
      throw new Error(`Task not found: ${id}`)
    }

    mockTasks[index] = {
      ...mockTasks[index],
      status: 'todo',
      completed_at: undefined,
      updated_at: new Date().toISOString(),
    }
    return cloneDeep(mockTasks[index])
  },

  /**
   * Get subtasks for a parent task
   */
  async getSubtasks(parentId: string): Promise<Task[]> {
    if (USE_REAL_API) {
      return api.get<Task[]>(`/tasks/${parentId}/subtasks`)
    }

    await simulateDelay()
    return cloneDeep(mockTasks.filter((t) => t.parent_id === parentId))
  },
}

// ============================================================================
// Calendar Events API
// ============================================================================

export const calendarApi = {
  /**
   * List events within a date range
   */
  async list(startDate: string, endDate: string): Promise<CalendarEvent[]> {
    if (USE_REAL_API) {
      const response = await api.get<{ events: CalendarEvent[]; total: number }>('/events', { days_ahead: 7 })
      return response.events
    }

    await simulateDelay()
    const start = new Date(startDate)
    const end = new Date(endDate)

    return cloneDeep(
      mockEvents.filter((e) => {
        const eventStart = new Date(e.start_time)
        return eventStart >= start && eventStart <= end
      })
    )
  },

  /**
   * Get a single event by ID
   */
  async get(id: string): Promise<CalendarEvent> {
    if (USE_REAL_API) {
      return api.get<CalendarEvent>(`/events/${id}`)
    }

    await simulateDelay()
    const event = mockEvents.find((e) => e.id === id)
    if (!event) {
      throw new Error(`Event not found: ${id}`)
    }
    return cloneDeep(event)
  },

  /**
   * Create a new event
   */
  async create(input: CalendarEventCreateInput): Promise<CalendarEvent> {
    if (USE_REAL_API) {
      return api.post<CalendarEvent>('/events', input)
    }

    await simulateDelay()
    const newEvent = createMockEvent({
      ...input,
      all_day: input.all_day ?? false,
      event_type: input.event_type ?? 'meeting',
    })
    mockEvents.push(newEvent)
    return cloneDeep(newEvent)
  },

  /**
   * Update an existing event
   */
  async update(id: string, input: Partial<CalendarEventCreateInput>): Promise<CalendarEvent> {
    if (USE_REAL_API) {
      return api.patch<CalendarEvent>(`/events/${id}`, input)
    }

    await simulateDelay()
    const index = mockEvents.findIndex((e) => e.id === id)
    if (index === -1) {
      throw new Error(`Event not found: ${id}`)
    }

    const updatedEvent = {
      ...mockEvents[index],
      ...input,
      updated_at: new Date().toISOString(),
    }
    mockEvents[index] = updatedEvent
    return cloneDeep(updatedEvent)
  },

  /**
   * Delete an event
   */
  async delete(id: string): Promise<void> {
    if (USE_REAL_API) {
      return api.delete(`/events/${id}`)
    }

    await simulateDelay()
    const index = mockEvents.findIndex((e) => e.id === id)
    if (index !== -1) {
      mockEvents.splice(index, 1)
    }
  },

  /**
   * Get today's events
   */
  async getToday(): Promise<CalendarEvent[]> {
    const today = new Date()
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    const end = new Date(start.getTime() + 24 * 60 * 60 * 1000 - 1)
    return this.list(start.toISOString(), end.toISOString())
  },
}

// ============================================================================
// Notes API
// ============================================================================

export const noteApi = {
  /**
   * List notes with optional filters
   */
  async list(filters?: NoteFilters): Promise<Note[]> {
    if (USE_REAL_API) {
      const response = await api.get<{ notes: Note[]; total: number }>('/notes', filters as Record<string, unknown>)
      return response.notes
    }

    await simulateDelay()
    let notes = cloneDeep(mockNotes)

    if (filters) {
      if (filters.note_type?.length) {
        notes = notes.filter((n) => filters.note_type!.includes(n.note_type))
      }
      if (filters.life_area?.length) {
        notes = notes.filter((n) => n.life_area && filters.life_area!.includes(n.life_area))
      }
      if (filters.tags?.length) {
        notes = notes.filter((n) => filters.tags!.some((tag) => n.tags.includes(tag)))
      }
      if (filters.search) {
        const search = filters.search.toLowerCase()
        notes = notes.filter(
          (n) =>
            n.title.toLowerCase().includes(search) ||
            n.content.toLowerCase().includes(search) ||
            n.tags.some((tag) => tag.toLowerCase().includes(search))
        )
      }
    }

    // Sort by pinned first, then by updated_at
    return notes.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1
      }
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    })
  },

  /**
   * Get a single note by ID
   */
  async get(id: string): Promise<Note> {
    if (USE_REAL_API) {
      return api.get<Note>(`/notes/${id}`)
    }

    await simulateDelay()
    const note = mockNotes.find((n) => n.id === id)
    if (!note) {
      throw new Error(`Note not found: ${id}`)
    }
    return cloneDeep(note)
  },

  /**
   * Create a new note
   */
  async create(input: NoteCreateInput): Promise<Note> {
    if (USE_REAL_API) {
      return api.post<Note>('/notes', input)
    }

    await simulateDelay()
    const newNote = createMockNote({
      ...input,
      note_type: input.note_type ?? 'note',
      tags: input.tags || [],
    })
    mockNotes.push(newNote)
    return cloneDeep(newNote)
  },

  /**
   * Update an existing note
   */
  async update(id: string, input: Partial<NoteCreateInput> & { is_pinned?: boolean }): Promise<Note> {
    if (USE_REAL_API) {
      return api.patch<Note>(`/notes/${id}`, input)
    }

    await simulateDelay()
    const index = mockNotes.findIndex((n) => n.id === id)
    if (index === -1) {
      throw new Error(`Note not found: ${id}`)
    }

    const content = input.content ?? mockNotes[index].content
    const updatedNote = {
      ...mockNotes[index],
      ...input,
      word_count: content.split(/\s+/).filter(Boolean).length,
      updated_at: new Date().toISOString(),
    }
    mockNotes[index] = updatedNote
    return cloneDeep(updatedNote)
  },

  /**
   * Delete a note
   */
  async delete(id: string): Promise<void> {
    if (USE_REAL_API) {
      return api.delete(`/notes/${id}`)
    }

    await simulateDelay()
    const index = mockNotes.findIndex((n) => n.id === id)
    if (index !== -1) {
      mockNotes.splice(index, 1)
    }
  },

  /**
   * Get backlinks for a note (notes that link to this note)
   */
  async getBacklinks(noteId: string): Promise<Note[]> {
    if (USE_REAL_API) {
      return api.get<Note[]>(`/notes/${noteId}/backlinks`)
    }

    await simulateDelay()
    const note = mockNotes.find((n) => n.id === noteId)
    if (!note) {
      throw new Error(`Note not found: ${noteId}`)
    }

    return cloneDeep(mockNotes.filter((n) => n.backlinks.includes(noteId)))
  },

  /**
   * Toggle pin status
   */
  async togglePin(id: string): Promise<Note> {
    if (USE_REAL_API) {
      return api.post<Note>(`/notes/${id}/toggle-pin`)
    }

    await simulateDelay()
    const index = mockNotes.findIndex((n) => n.id === id)
    if (index === -1) {
      throw new Error(`Note not found: ${id}`)
    }

    mockNotes[index] = {
      ...mockNotes[index],
      is_pinned: !mockNotes[index].is_pinned,
      updated_at: new Date().toISOString(),
    }
    return cloneDeep(mockNotes[index])
  },
}

// ============================================================================
// Goals API
// ============================================================================

export const goalApi = {
  /**
   * List goals with optional filters
   */
  async list(filters?: GoalFilters): Promise<Goal[]> {
    if (USE_REAL_API) {
      const response = await api.get<{ goals: Goal[]; total: number }>('/goals', filters as Record<string, unknown>)
      return response.goals
    }

    await simulateDelay()
    let goals = cloneDeep(mockGoals)

    if (filters) {
      if (filters.status?.length) {
        goals = goals.filter((g) => filters.status!.includes(g.status))
      }
      if (filters.life_area?.length) {
        goals = goals.filter((g) => g.life_area && filters.life_area!.includes(g.life_area))
      }
    }

    return goals
  },

  /**
   * Get a single goal by ID
   */
  async get(id: string): Promise<Goal> {
    if (USE_REAL_API) {
      return api.get<Goal>(`/goals/${id}`)
    }

    await simulateDelay()
    const goal = mockGoals.find((g) => g.id === id)
    if (!goal) {
      throw new Error(`Goal not found: ${id}`)
    }
    return cloneDeep(goal)
  },

  /**
   * Create a new goal
   */
  async create(input: GoalCreateInput): Promise<Goal> {
    if (USE_REAL_API) {
      return api.post<Goal>('/goals', input)
    }

    await simulateDelay()
    const newGoal = createMockGoal({
      ...input,
      milestones:
        input.milestones?.map((m, i) => ({
          id: `m${i + 1}`,
          title: m.title,
          completed: false,
        })) || [],
    })
    mockGoals.push(newGoal)
    return cloneDeep(newGoal)
  },

  /**
   * Update an existing goal
   */
  async update(id: string, input: Partial<GoalCreateInput> & { status?: string; progress?: number }): Promise<Goal> {
    if (USE_REAL_API) {
      return api.patch<Goal>(`/goals/${id}`, input)
    }

    await simulateDelay()
    const index = mockGoals.findIndex((g) => g.id === id)
    if (index === -1) {
      throw new Error(`Goal not found: ${id}`)
    }

    const updatedGoal = {
      ...mockGoals[index],
      ...input,
      updated_at: new Date().toISOString(),
    }
    mockGoals[index] = updatedGoal as Goal
    return cloneDeep(updatedGoal as Goal)
  },

  /**
   * Delete a goal
   */
  async delete(id: string): Promise<void> {
    if (USE_REAL_API) {
      return api.delete(`/goals/${id}`)
    }

    await simulateDelay()
    const index = mockGoals.findIndex((g) => g.id === id)
    if (index !== -1) {
      mockGoals.splice(index, 1)
    }
  },

  /**
   * Log progress on a goal
   */
  async logProgress(goalId: string, delta: number, note?: string): Promise<ProgressLog> {
    if (USE_REAL_API) {
      return api.post<ProgressLog>(`/goals/${goalId}/progress`, { delta, note })
    }

    await simulateDelay()
    const goalIndex = mockGoals.findIndex((g) => g.id === goalId)
    if (goalIndex === -1) {
      throw new Error(`Goal not found: ${goalId}`)
    }

    // Update goal progress
    const newProgress = Math.min(100, Math.max(0, mockGoals[goalIndex].progress + delta))
    mockGoals[goalIndex] = {
      ...mockGoals[goalIndex],
      progress: newProgress,
      updated_at: new Date().toISOString(),
    }

    // Create progress log
    const progressLog: ProgressLog = {
      id: `log-${Date.now()}`,
      goal_id: goalId,
      progress_delta: delta,
      note,
      logged_at: new Date().toISOString(),
    }
    mockProgressLogs.push(progressLog)

    return progressLog
  },

  /**
   * Get progress history for a goal
   */
  async getProgressHistory(goalId: string): Promise<ProgressLog[]> {
    if (USE_REAL_API) {
      return api.get<ProgressLog[]>(`/goals/${goalId}/progress`)
    }

    await simulateDelay()
    return cloneDeep(mockProgressLogs.filter((l) => l.goal_id === goalId))
  },

  /**
   * Update a milestone
   */
  async updateMilestone(goalId: string, milestoneId: string, completed: boolean): Promise<Goal> {
    if (USE_REAL_API) {
      return api.patch<Goal>(`/goals/${goalId}/milestones/${milestoneId}`, { completed })
    }

    await simulateDelay()
    const goalIndex = mockGoals.findIndex((g) => g.id === goalId)
    if (goalIndex === -1) {
      throw new Error(`Goal not found: ${goalId}`)
    }

    const goal = mockGoals[goalIndex]
    const milestoneIndex = goal.milestones.findIndex((m) => m.id === milestoneId)
    if (milestoneIndex === -1) {
      throw new Error(`Milestone not found: ${milestoneId}`)
    }

    goal.milestones[milestoneIndex] = {
      ...goal.milestones[milestoneIndex],
      completed,
      completed_at: completed ? new Date().toISOString() : undefined,
    }

    // Recalculate progress based on milestones
    const completedCount = goal.milestones.filter((m) => m.completed).length
    goal.progress = Math.round((completedCount / goal.milestones.length) * 100)
    goal.updated_at = new Date().toISOString()

    return cloneDeep(goal)
  },
}

// ============================================================================
// Projects API
// ============================================================================

export const projectApi = {
  /**
   * List all projects
   */
  async list(): Promise<Project[]> {
    if (USE_REAL_API) {
      return api.get<Project[]>('/projects')
    }

    await simulateDelay()
    return cloneDeep(mockProjects)
  },

  /**
   * Get a single project by ID
   */
  async get(id: string): Promise<Project> {
    if (USE_REAL_API) {
      return api.get<Project>(`/projects/${id}`)
    }

    await simulateDelay()
    const project = mockProjects.find((p) => p.id === id)
    if (!project) {
      throw new Error(`Project not found: ${id}`)
    }
    return cloneDeep(project)
  },
}

// ============================================================================
// Dashboard API
// ============================================================================

export const dashboardApi = {
  /**
   * Get all dashboard data in one request
   */
  async getData(): Promise<DashboardData> {
    if (USE_REAL_API) {
      return api.get<DashboardData>('/dashboard/today')
    }

    await simulateDelay(300) // Slightly longer for dashboard
    return cloneDeep(mockDashboardData)
  },
}

// ============================================================================
// NLP Parsing API
// ============================================================================

export const nlpApi = {
  /**
   * Parse natural language input into structured data
   */
  async parse(input: string): Promise<ParsedInput> {
    if (USE_REAL_API) {
      return api.post<ParsedInput>('/nlp/parse', { input })
    }

    await simulateDelay(150)

    // Check if we have a mock for this exact input
    const mockResult = mockParsedInputs[input.toLowerCase()]
    if (mockResult) {
      return cloneDeep(mockResult)
    }

    // Simple heuristic parsing for demo purposes
    const lowerInput = input.toLowerCase()
    let type: 'task' | 'event' | 'note' = 'task'

    if (lowerInput.includes('meeting') || lowerInput.includes('schedule') || lowerInput.includes('appointment')) {
      type = 'event'
    } else if (lowerInput.includes('note') || lowerInput.includes('remember that')) {
      type = 'note'
    }

    return {
      type,
      title: input.replace(/^(remind me to|schedule a|note about)\s*/i, ''),
      raw_input: input,
    }
  },
}
