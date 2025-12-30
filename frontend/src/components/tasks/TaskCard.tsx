import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/utils'
import type { Task } from '@/types/models'
import { PriorityBadge } from './PriorityBadge'
import { StatusIcon } from './StatusBadge'
import { Calendar, Clock, Folder, AlertTriangle } from 'lucide-react'

interface TaskCardProps {
  task: Task
  onClick?: () => void
  onStatusChange?: () => void
  selected?: boolean
  className?: string
}

/**
 * Task card component for list views
 */
export function TaskCard({
  task,
  onClick,
  onStatusChange,
  selected,
  className,
}: TaskCardProps) {
  const isOverdue =
    task.due_date &&
    new Date(task.due_date) < new Date() &&
    task.status !== 'done' &&
    task.status !== 'cancelled'

  const handleStatusClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onStatusChange?.()
  }

  return (
    <div
      className={cn(
        'group flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-3 transition-colors',
        'hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-tertiary)]',
        selected && 'border-[var(--color-accent-blue)] bg-[var(--color-bg-tertiary)]',
        isOverdue && 'border-l-2 border-l-[var(--color-accent-red)]',
        className
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      {/* Status checkbox */}
      <button
        onClick={handleStatusClick}
        className="mt-0.5 flex-shrink-0 rounded p-0.5 transition-colors hover:bg-[var(--color-bg-hover)]"
        aria-label={task.status === 'done' ? 'Mark as incomplete' : 'Mark as complete'}
      >
        <StatusIcon status={task.status} size={18} />
      </button>

      {/* Content */}
      <div className="min-w-0 flex-1">
        {/* Title */}
        <h3
          className={cn(
            'text-sm font-medium text-[var(--color-text-primary)]',
            task.status === 'done' && 'text-[var(--color-text-tertiary)] line-through'
          )}
        >
          {task.title}
        </h3>

        {/* Metadata row */}
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
          {/* Project */}
          {task.project_id && (
            <span className="flex items-center gap-1">
              <Folder className="h-3 w-3" />
              <span>Project</span>
            </span>
          )}

          {/* Due date */}
          {task.due_date && (
            <span
              className={cn(
                'flex items-center gap-1',
                isOverdue && 'text-[var(--color-accent-red)]'
              )}
            >
              {isOverdue && <AlertTriangle className="h-3 w-3" />}
              <Calendar className="h-3 w-3" />
              <span>{formatRelativeTime(task.due_date)}</span>
            </span>
          )}

          {/* Time estimate */}
          {task.estimated_minutes && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{task.estimated_minutes}m</span>
            </span>
          )}

          {/* Life area */}
          {task.life_area && (
            <span className="capitalize">{task.life_area}</span>
          )}
        </div>

        {/* Tags */}
        {task.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {task.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 text-xs text-[var(--color-text-secondary)]"
              >
                #{tag}
              </span>
            ))}
            {task.tags.length > 3 && (
              <span className="text-xs text-[var(--color-text-tertiary)]">
                +{task.tags.length - 3}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Priority badge */}
      <PriorityBadge priority={task.priority} className="flex-shrink-0" />
    </div>
  )
}

/**
 * Compact task item for inline lists
 */
interface TaskItemProps {
  task: Task
  onClick?: () => void
  onComplete?: () => void
  className?: string
}

export function TaskItem({ task, onClick, onComplete, className }: TaskItemProps) {
  const isOverdue =
    task.due_date &&
    new Date(task.due_date) < new Date() &&
    task.status !== 'done'

  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors',
        'hover:bg-[var(--color-bg-hover)]',
        className
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
    >
      <button
        onClick={(e) => {
          e.stopPropagation()
          onComplete?.()
        }}
        className="flex-shrink-0"
        aria-label="Toggle complete"
      >
        <StatusIcon status={task.status} size={16} />
      </button>

      <span
        className={cn(
          'flex-1 truncate text-sm',
          task.status === 'done'
            ? 'text-[var(--color-text-tertiary)] line-through'
            : 'text-[var(--color-text-primary)]'
        )}
      >
        {task.title}
      </span>

      {isOverdue && (
        <AlertTriangle className="h-3 w-3 flex-shrink-0 text-[var(--color-accent-red)]" />
      )}

      <PriorityBadge priority={task.priority} size="sm" />
    </div>
  )
}
