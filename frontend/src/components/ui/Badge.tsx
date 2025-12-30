import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Badge variant styles - semantic colors for different use cases.
 */
const badgeVariants = {
  default: 'bg-bg-tertiary text-text-primary border-border-default',
  blue: 'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
  green: 'bg-accent-green/10 text-accent-green border-accent-green/20',
  yellow: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20',
  red: 'bg-accent-red/10 text-accent-red border-accent-red/20',
  purple: 'bg-accent-purple/10 text-accent-purple border-accent-purple/20',
  orange: 'bg-accent-orange/10 text-accent-orange border-accent-orange/20',
} as const

/**
 * Badge size styles.
 */
const badgeSizes = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-0.5 text-xs',
  lg: 'px-2.5 py-1 text-sm',
} as const

/**
 * Priority to variant mapping for convenience.
 */
const priorityVariants: Record<number, keyof typeof badgeVariants> = {
  5: 'red',
  4: 'orange',
  3: 'yellow',
  2: 'default',
  1: 'default',
}

/**
 * Status to variant mapping for convenience.
 */
const statusVariants: Record<string, keyof typeof badgeVariants> = {
  done: 'green',
  in_progress: 'blue',
  waiting: 'yellow',
  todo: 'default',
  cancelled: 'default',
  overdue: 'red',
}

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Visual style variant */
  variant?: keyof typeof badgeVariants
  /** Size of the badge */
  size?: keyof typeof badgeSizes
  /** Priority level (1-5) - auto-selects variant */
  priority?: 1 | 2 | 3 | 4 | 5
  /** Status string - auto-selects variant */
  status?: 'done' | 'in_progress' | 'waiting' | 'todo' | 'cancelled' | 'overdue'
}

/**
 * Badge component for status, priority, and tags.
 *
 * @example
 * ```tsx
 * <Badge variant="blue">Active</Badge>
 * <Badge priority={5}>Critical</Badge>
 * <Badge status="done">Completed</Badge>
 * <Badge variant="purple" size="lg">Tag</Badge>
 * ```
 */
const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant: variantProp,
      size = 'md',
      priority,
      status,
      ...props
    },
    ref
  ) => {
    // Determine variant based on props priority: explicit variant > priority > status > default
    let variant: keyof typeof badgeVariants = 'default'
    if (variantProp) {
      variant = variantProp
    } else if (priority !== undefined) {
      variant = priorityVariants[priority] ?? 'default'
    } else if (status) {
      variant = statusVariants[status] ?? 'default'
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium',
          'rounded-[var(--radius-sm)] border',
          'whitespace-nowrap',
          badgeVariants[variant],
          badgeSizes[size],
          className
        )}
        {...props}
      />
    )
  }
)

Badge.displayName = 'Badge'

export { Badge, badgeVariants, badgeSizes, priorityVariants, statusVariants }
