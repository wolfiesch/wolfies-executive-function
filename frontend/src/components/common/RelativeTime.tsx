import { useState, useEffect } from 'react'
import { formatRelativeTime } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface RelativeTimeProps {
  date: Date | string
  className?: string
  updateInterval?: number // in milliseconds, 0 to disable auto-update
}

/**
 * Component that displays a relative time (e.g., "2 hours ago", "in 3 days")
 * Automatically updates based on the update interval
 */
export function RelativeTime({
  date,
  className,
  updateInterval = 60000, // Update every minute by default
}: RelativeTimeProps) {
  const [relativeTime, setRelativeTime] = useState(() => formatRelativeTime(date))

  useEffect(() => {
    if (updateInterval === 0) return

    const timer = setInterval(() => {
      setRelativeTime(formatRelativeTime(date))
    }, updateInterval)

    return () => clearInterval(timer)
  }, [date, updateInterval])

  // Update immediately when date changes
  useEffect(() => {
    setRelativeTime(formatRelativeTime(date))
  }, [date])

  const d = typeof date === 'string' ? new Date(date) : date
  const isPast = d.getTime() < Date.now()
  const isOverdue = isPast && d.getTime() < Date.now() - 1000 * 60 * 60 * 24 // More than a day ago

  return (
    <time
      dateTime={d.toISOString()}
      title={d.toLocaleString()}
      className={cn(
        'text-sm',
        isOverdue ? 'text-[var(--color-accent-red)]' : 'text-[var(--color-text-secondary)]',
        className
      )}
    >
      {relativeTime}
    </time>
  )
}
