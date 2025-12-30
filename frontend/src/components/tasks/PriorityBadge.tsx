import { cn } from '@/lib/utils'
import { PRIORITY_LABELS, type Priority } from '@/lib/constants'

interface PriorityBadgeProps {
  priority: Priority
  size?: 'sm' | 'md'
  showLabel?: boolean
  className?: string
}

const priorityConfig: Record<Priority, { color: string; bg: string }> = {
  5: { color: 'text-[var(--color-priority-5)]', bg: 'bg-[var(--color-priority-5)]/10' },
  4: { color: 'text-[var(--color-priority-4)]', bg: 'bg-[var(--color-priority-4)]/10' },
  3: { color: 'text-[var(--color-priority-3)]', bg: 'bg-[var(--color-priority-3)]/10' },
  2: { color: 'text-[var(--color-priority-2)]', bg: 'bg-[var(--color-priority-2)]/10' },
  1: { color: 'text-[var(--color-priority-1)]', bg: 'bg-[var(--color-priority-1)]/10' },
}

/**
 * Priority badge component for tasks
 * Shows priority level with color coding (P1-P5)
 */
export function PriorityBadge({
  priority,
  size = 'sm',
  showLabel = false,
  className,
}: PriorityBadgeProps) {
  const config = priorityConfig[priority]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded font-medium',
        config.color,
        config.bg,
        size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm',
        className
      )}
    >
      <span>P{priority}</span>
      {showLabel && <span className="hidden sm:inline">- {PRIORITY_LABELS[priority]}</span>}
    </span>
  )
}

/**
 * Priority dots indicator (visual representation)
 */
interface PriorityDotsProps {
  priority: Priority
  className?: string
}

export function PriorityDots({ priority, className }: PriorityDotsProps) {
  return (
    <div className={cn('flex items-center gap-0.5', className)}>
      {[1, 2, 3, 4, 5].map((level) => (
        <span
          key={level}
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            level <= priority
              ? priorityConfig[priority].color.replace('text-', 'bg-').replace('/10', '')
              : 'bg-[var(--color-bg-tertiary)]'
          )}
        />
      ))}
    </div>
  )
}
