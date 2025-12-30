import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string | number
  icon?: LucideIcon
  trend?: {
    value: number
    label: string
    isPositive: boolean
  }
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
  className?: string
}

const colorConfig = {
  blue: 'text-[var(--color-accent-blue)] bg-[var(--color-accent-blue)]/10',
  green: 'text-[var(--color-accent-green)] bg-[var(--color-accent-green)]/10',
  yellow: 'text-[var(--color-accent-yellow)] bg-[var(--color-accent-yellow)]/10',
  red: 'text-[var(--color-accent-red)] bg-[var(--color-accent-red)]/10',
  purple: 'text-[var(--color-accent-purple)] bg-[var(--color-accent-purple)]/10',
}

/**
 * Statistics card for dashboard metrics
 */
export function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'blue',
  className,
}: StatsCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-4',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-[var(--color-text-secondary)]">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-[var(--color-text-primary)]">
            {value}
          </p>
        </div>
        {Icon && (
          <div className={cn('rounded-lg p-2', colorConfig[color])}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      {trend && (
        <div className="mt-2 flex items-center gap-1">
          <span
            className={cn(
              'text-sm font-medium',
              trend.isPositive
                ? 'text-[var(--color-accent-green)]'
                : 'text-[var(--color-accent-red)]'
            )}
          >
            {trend.isPositive ? '+' : ''}{trend.value}%
          </span>
          <span className="text-sm text-[var(--color-text-tertiary)]">
            {trend.label}
          </span>
        </div>
      )}
    </div>
  )
}

/**
 * Stats grid wrapper for consistent layout
 */
interface StatsGridProps {
  children: React.ReactNode
  className?: string
}

export function StatsGrid({ children, className }: StatsGridProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-4 md:grid-cols-4',
        className
      )}
    >
      {children}
    </div>
  )
}
