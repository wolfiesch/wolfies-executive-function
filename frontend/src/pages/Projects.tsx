import { FolderKanban, Plus, MoreHorizontal, Calendar, CheckSquare } from 'lucide-react'
import { AppShell } from '@/components/layout'

/**
 * Projects - Project management page
 *
 * Features:
 * - Project list with status and progress
 * - Kanban or list view options
 * - Project detail with linked tasks
 *
 * Design pattern: **Container Pattern** - projects group related tasks
 * providing hierarchical organization for complex work.
 */
export function Projects() {
  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Projects</h1>
            <p className="text-[var(--color-text-secondary)]">
              Organize your tasks into focused projects
            </p>
          </div>
          <button className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90">
            <Plus className="h-4 w-4" />
            New Project
          </button>
        </div>

        {/* View toggle and filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button className="rounded-lg bg-[var(--color-bg-active)] px-3 py-1.5 text-sm font-medium text-[var(--color-text-primary)]">
              All Projects
            </button>
            <button className="rounded-lg px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
              Active
            </button>
            <button className="rounded-lg px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
              Completed
            </button>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border-default)]">
            <button className="rounded-l-lg bg-[var(--color-bg-active)] px-3 py-1.5 text-sm text-[var(--color-text-primary)]">
              Grid
            </button>
            <button className="rounded-r-lg px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
              List
            </button>
          </div>
        </div>

        {/* Projects grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <ProjectCard key={i} />
          ))}
        </div>

        {/* Empty state (would show when no projects) */}
        {false && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] py-16 text-center">
            <FolderKanban className="h-12 w-12 text-[var(--color-text-tertiary)]" />
            <h3 className="mt-4 text-lg font-medium text-[var(--color-text-primary)]">
              No projects yet
            </h3>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Create your first project to organize your tasks
            </p>
            <button className="mt-4 flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white">
              <Plus className="h-4 w-4" />
              Create Project
            </button>
          </div>
        )}
      </div>
    </AppShell>
  )
}

// Project card component
function ProjectCard() {
  const taskCount = Math.floor(Math.random() * 15) + 3
  const completedTasks = Math.floor(Math.random() * taskCount)
  const progress = Math.round((completedTasks / taskCount) * 100)

  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5 transition-colors hover:border-[var(--color-border-default)]">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-[var(--color-accent-blue)]/20 p-2">
            <FolderKanban className="h-5 w-5 text-[var(--color-accent-blue)]" />
          </div>
          <div>
            <div className="h-5 w-32 rounded bg-[var(--color-bg-tertiary)]" />
            <span className="mt-1 inline-block rounded bg-[var(--color-bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-text-tertiary)]">
              Active
            </span>
          </div>
        </div>
        <button className="rounded p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-secondary)]">
          <MoreHorizontal className="h-5 w-5" />
        </button>
      </div>

      {/* Description placeholder */}
      <div className="mt-3 space-y-1">
        <div className="h-3 w-full rounded bg-[var(--color-bg-tertiary)]" />
        <div className="h-3 w-2/3 rounded bg-[var(--color-bg-tertiary)]" />
      </div>

      {/* Progress */}
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="text-[var(--color-text-secondary)]">Progress</span>
          <span className="font-medium text-[var(--color-text-primary)]">{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-bg-tertiary)]">
          <div
            className="h-full rounded-full bg-[var(--color-accent-blue)]"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Meta info */}
      <div className="mt-4 flex items-center gap-4 text-xs text-[var(--color-text-tertiary)]">
        <div className="flex items-center gap-1">
          <CheckSquare className="h-3.5 w-3.5" />
          <span>
            {completedTasks}/{taskCount} tasks
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="h-3.5 w-3.5" />
          <span>Due Jan 15</span>
        </div>
      </div>
    </div>
  )
}

export default Projects
