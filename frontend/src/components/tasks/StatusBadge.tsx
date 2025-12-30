import { cn } from '@/lib/utils'
import type { TaskStatus } from '@/lib/constants'
import {
  Circle,
  CircleDot,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react'

interface StatusBadgeProps {
  status: TaskStatus
  size?: 'sm' | 'md'
  showLabel?: boolean
  className?: string
}

const statusConfig: Record<
  TaskStatus,
  { label: string; color: string; bg: string; Icon: React.ElementType }
> = {
  todo: {
    label: 'To Do',
    color: 'text-[var(--color-text-secondary)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    Icon: Circle,
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-[var(--color-accent-blue)]',
    bg: 'bg-[var(--color-accent-blue)]/10',
    Icon: CircleDot,
  },
  waiting: {
    label: 'Waiting',
    color: 'text-[var(--color-accent-yellow)]',
    bg: 'bg-[var(--color-accent-yellow)]/10',
    Icon: Clock,
  },
  done: {
    label: 'Done',
    color: 'text-[var(--color-accent-green)]',
    bg: 'bg-[var(--color-accent-green)]/10',
    Icon: CheckCircle2,
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-[var(--color-text-tertiary)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    Icon: XCircle,
  },
}

/**
 * Status badge component for tasks
 */
export function StatusBadge({
  status,
  size = 'sm',
  showLabel = true,
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status]
  const Icon = config.Icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded font-medium',
        config.color,
        config.bg,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        className
      )}
    >
      <Icon className={size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'} />
      {showLabel && <span>{config.label}</span>}
    </span>
  )
}

/**
 * Status icon only (for compact displays)
 */
interface StatusIconProps {
  status: TaskStatus
  size?: number
  className?: string
}

export function StatusIcon({ status, size = 16, className }: StatusIconProps) {
  const config = statusConfig[status]
  const Icon = config.Icon

  return (
    <Icon
      size={size}
      className={cn(config.color, className)}
      aria-label={config.label}
    />
  )
}
