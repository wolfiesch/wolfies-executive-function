import { useState } from 'react'
import { Search, Filter, Plus, ChevronDown, AlertCircle, Loader2 } from 'lucide-react'
import { AppShell } from '@/components/layout'
import { useTasks, useToggleTaskComplete } from '@/api/hooks'
import { TaskCard } from '@/components/tasks/TaskCard'
import type { Task } from '@/types/models'

/**
 * Tasks - Task management page
 *
 * Features:
 * - Search bar for filtering tasks
 * - Filter dropdowns (status, priority, life area, date range)
 * - Task list with selection and keyboard navigation
 * - Detail panel for selected task
 *
 * Design pattern: **Master-Detail Pattern** - list on left, details on right
 * allows quick browsing while maintaining access to full information.
 */
export function Tasks() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch tasks from API
  const { data: tasks, isLoading, error } = useTasks()
  const toggleComplete = useToggleTaskComplete()

  // Filter tasks by search query
  const filteredTasks = tasks?.filter((task) => {
    if (!searchQuery) return true
    const search = searchQuery.toLowerCase()
    return (
      task.title.toLowerCase().includes(search) ||
      task.description?.toLowerCase().includes(search) ||
      task.tags.some((tag) => tag.toLowerCase().includes(search))
    )
  })

  const handleStatusChange = (task: Task, newStatus: Task['status']) => {
    if (newStatus === 'done') {
      toggleComplete.mutate({ ...task, status: task.status === 'done' ? 'todo' : task.status })
    }
  }

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-theme(spacing.20))] flex-col">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Tasks</h1>
          <button className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90">
            <Plus className="h-4 w-4" />
            New Task
          </button>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-4 flex items-center gap-3 rounded-lg border border-[var(--color-accent-red)]/30 bg-[var(--color-accent-red)]/10 p-4">
            <AlertCircle className="h-5 w-5 text-[var(--color-accent-red)]" />
            <p className="text-sm text-[var(--color-accent-red)]">
              Failed to load tasks. Please try refreshing.
            </p>
          </div>
        )}

        {/* Search and filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] py-2 pl-10 pr-4 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
            />
          </div>

          {/* Filter buttons */}
          <FilterButton label="Status" />
          <FilterButton label="Priority" />
          <FilterButton label="Life Area" />
          <FilterButton label="Due Date" />

          <button className="flex items-center gap-2 rounded-lg border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
            <Filter className="h-4 w-4" />
            More Filters
          </button>
        </div>

        {/* Task list and detail panel */}
        <div className="flex flex-1 gap-4 overflow-hidden">
          {/* Task list */}
          <div className="flex-1 overflow-y-auto rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]">
            {/* List header */}
            <div className="sticky top-0 z-10 flex items-center border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] px-4 py-3">
              <span className="text-sm font-medium text-[var(--color-text-secondary)]">
                All Tasks
              </span>
              <span className="ml-2 rounded-full bg-[var(--color-bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-text-tertiary)]">
                {filteredTasks?.length ?? 0}
              </span>
            </div>

            {/* Loading state */}
            {isLoading && (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-[var(--color-accent-blue)]" />
              </div>
            )}

            {/* Task items */}
            {!isLoading && filteredTasks && filteredTasks.length > 0 && (
              <div className="space-y-2 p-3">
                {filteredTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    selected={selectedTask?.id === task.id}
                    onClick={() => setSelectedTask(task)}
                    onStatusChange={(status) => handleStatusChange(task, status)}
                  />
                ))}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && (!filteredTasks || filteredTasks.length === 0) && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-lg font-medium text-[var(--color-text-primary)]">
                  {searchQuery ? 'No tasks match your search' : 'No tasks yet'}
                </p>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                  {searchQuery ? 'Try a different search term' : 'Create a new task to get started'}
                </p>
              </div>
            )}
          </div>

          {/* Detail panel */}
          <div className="hidden w-96 overflow-y-auto rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] lg:block">
            {selectedTask ? (
              <TaskDetailPanel task={selectedTask} />
            ) : (
              <div className="flex h-full flex-col items-center justify-center p-6 text-center">
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Select a task to view details
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}

// Task detail panel component
function TaskDetailPanel({ task }: { task: Task }) {
  return (
    <div className="p-5">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        {task.title}
      </h2>
      {task.description && (
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          {task.description}
        </p>
      )}
      <div className="mt-4 space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-[var(--color-text-tertiary)]">Status</span>
          <span className="capitalize text-[var(--color-text-primary)]">{task.status}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[var(--color-text-tertiary)]">Priority</span>
          <span className="text-[var(--color-text-primary)]">P{task.priority}</span>
        </div>
        {task.due_date && (
          <div className="flex justify-between">
            <span className="text-[var(--color-text-tertiary)]">Due Date</span>
            <span className="text-[var(--color-text-primary)]">
              {new Date(task.due_date).toLocaleDateString()}
            </span>
          </div>
        )}
        {task.estimated_minutes && (
          <div className="flex justify-between">
            <span className="text-[var(--color-text-tertiary)]">Estimate</span>
            <span className="text-[var(--color-text-primary)]">{task.estimated_minutes} min</span>
          </div>
        )}
        {task.tags.length > 0 && (
          <div>
            <span className="text-[var(--color-text-tertiary)]">Tags</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {task.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-[var(--color-bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Filter button component
function FilterButton({ label }: { label: string }) {
  return (
    <button className="flex items-center gap-1 rounded-lg border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
      {label}
      <ChevronDown className="h-4 w-4" />
    </button>
  )
}

export default Tasks
