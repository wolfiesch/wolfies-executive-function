import { Search, Filter, Plus, MoreHorizontal, ChevronDown } from 'lucide-react'
import { AppShell } from '@/components/layout'

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

        {/* Search and filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
            <input
              type="text"
              placeholder="Search tasks..."
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
                0
              </span>
            </div>

            {/* Task items placeholder */}
            <div className="divide-y divide-[var(--color-border-subtle)]">
              {[1, 2, 3, 4, 5].map((i) => (
                <TaskRowPlaceholder key={i} />
              ))}
            </div>

            {/* Empty state (would show when no tasks) */}
            {false && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-lg font-medium text-[var(--color-text-primary)]">
                  No tasks found
                </p>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                  Create a new task or adjust your filters
                </p>
              </div>
            )}
          </div>

          {/* Detail panel placeholder */}
          <div className="hidden w-96 overflow-y-auto rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] lg:block">
            <div className="flex h-full flex-col items-center justify-center p-6 text-center">
              <p className="text-sm text-[var(--color-text-secondary)]">
                Select a task to view details
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
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

// Task row placeholder
function TaskRowPlaceholder() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-bg-hover)]">
      {/* Checkbox placeholder */}
      <div className="h-5 w-5 rounded border-2 border-[var(--color-border-default)]" />

      {/* Task content */}
      <div className="flex-1">
        <div className="h-4 w-2/3 rounded bg-[var(--color-bg-tertiary)]" />
        <div className="mt-1 flex items-center gap-2">
          <div className="h-3 w-16 rounded bg-[var(--color-bg-tertiary)]" />
          <div className="h-3 w-20 rounded bg-[var(--color-bg-tertiary)]" />
        </div>
      </div>

      {/* Priority indicator */}
      <div className="h-2 w-2 rounded-full bg-[var(--color-priority-3)]" />

      {/* More actions */}
      <button className="rounded p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-active)] hover:text-[var(--color-text-secondary)]">
        <MoreHorizontal className="h-4 w-4" />
      </button>
    </div>
  )
}

export default Tasks
