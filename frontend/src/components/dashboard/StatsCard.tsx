import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string | number
  icon?: LucideIcon
  /** Optional subtext (e.g., "today", "this week") */
  subtext?: string
  /** Progress bar (0-1 ratio) */
  progress?: number
  /** Progress target for display (e.g., "4h") */
  progressTarget?: string
  trend?: {
    value: number
    label: string
    isPositive: boolean
  }
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'orange'
  className?: string
}

const colorConfig = {
  blue: {
    text: 'text-[var(--color-accent-blue)]',
    bg: 'bg-[var(--color-accent-blue)]/10',
    gradient: 'from-[var(--color-accent-blue)]/5',
    progress: 'bg-[var(--color-accent-blue)]',
  },
  green: {
    text: 'text-[var(--color-accent-green)]',
    bg: 'bg-[var(--color-accent-green)]/10',
    gradient: 'from-[var(--color-accent-green)]/5',
    progress: 'bg-[var(--color-accent-green)]',
  },
  yellow: {
    text: 'text-[var(--color-accent-yellow)]',
    bg: 'bg-[var(--color-accent-yellow)]/10',
    gradient: 'from-[var(--color-accent-yellow)]/5',
    progress: 'bg-[var(--color-accent-yellow)]',
  },
  red: {
    text: 'text-[var(--color-accent-red)]',
    bg: 'bg-[var(--color-accent-red)]/10',
    gradient: 'from-[var(--color-accent-red)]/5',
    progress: 'bg-[var(--color-accent-red)]',
  },
  purple: {
    text: 'text-[var(--color-accent-purple)]',
    bg: 'bg-[var(--color-accent-purple)]/10',
    gradient: 'from-[var(--color-accent-purple)]/5',
    progress: 'bg-[var(--color-accent-purple)]',
  },
  orange: {
    text: 'text-[var(--color-accent-orange)]',
    bg: 'bg-[var(--color-accent-orange)]/10',
    gradient: 'from-[var(--color-accent-orange)]/5',
    progress: 'bg-[var(--color-accent-orange)]',
  },
}

/**
 * Enhanced statistics card for dashboard metrics
 * 
 * Features:
 * - Icon with color-coded background
 * - Optional progress bar
 * - Trend indicator with direction
 * - Subtle gradient hover effect
 */
export function StatsCard({
  title,
  value,
  icon: Icon,
  subtext,
  progress,
  progressTarget,
  trend,
  color = 'blue',
  className,
}: StatsCardProps) {
  const colors = colorConfig[color]

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-4',
        'transition-all hover:border-[var(--color-border-default)] hover:bg-[var(--color-bg-tertiary)]',
        className
      )}
    >
      {/* Subtle gradient background on hover */}
      <div
        className={cn(
          'absolute inset-0 bg-gradient-to-br to-transparent opacity-0 transition-opacity group-hover:opacity-100',
          colors.gradient
        )}
      />

      <div className="relative">
        {/* Header: Icon + Title */}
        <div className="flex items-center gap-2 mb-2">
          {Icon && (
            <div className={cn('rounded-lg p-1.5', colors.bg, colors.text)}>
              <Icon className="h-4 w-4" />
            </div>
          )}
          <span className="text-sm text-[var(--color-text-secondary)]">
            {title}
          </span>
        </div>

        {/* Main Value */}
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-[var(--color-text-primary)]">
            {value}
          </span>
          {subtext && (
            <span className="text-sm text-[var(--color-text-tertiary)]">
              {subtext}
            </span>
          )}
        </div>

        {/* Trend Indicator */}
        {trend && (
          <div className="mt-2 flex items-center gap-1">
            {trend.isPositive ? (
              <TrendingUp className="h-3 w-3 text-[var(--color-accent-green)]" />
            ) : (
              <TrendingDown className="h-3 w-3 text-[var(--color-accent-red)]" />
            )}
            <span
              className={cn(
                'text-xs font-medium',
                trend.isPositive
                  ? 'text-[var(--color-accent-green)]'
                  : 'text-[var(--color-accent-red)]'
              )}
            >
              {trend.isPositive ? '+' : ''}
              {trend.value}%
            </span>
            <span className="text-xs text-[var(--color-text-tertiary)]">
              {trend.label}
            </span>
          </div>
        )}

        {/* Progress Bar */}
        {progress !== undefined && (
          <div className="mt-3">
            <div className="h-1.5 rounded-full bg-[var(--color-bg-primary)] overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-1000',
                  colors.progress
                )}
                style={{ width: `${Math.min(progress * 100, 100)}%` }}
              />
            </div>
            {progressTarget && (
              <div className="mt-1 text-xs text-[var(--color-text-tertiary)]">
                Target: {progressTarget}
              </div>
            )}
          </div>
        )}
      </div>
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
        'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4',
        className
      )}
    >
      {children}
    </div>
  )
}

