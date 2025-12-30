import { cn } from '@/lib/utils'

interface ProgressRingProps {
  progress: number // 0-100
  size?: number // diameter in pixels
  strokeWidth?: number
  className?: string
  showPercent?: boolean
  color?: string
}

/**
 * Circular progress ring component
 */
export function ProgressRing({
  progress,
  size = 48,
  strokeWidth = 4,
  className,
  showPercent = true,
  color = 'var(--color-accent-blue)',
}: ProgressRingProps) {
  const normalizedProgress = Math.min(100, Math.max(0, progress))
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDashoffset = circumference - (normalizedProgress / 100) * circumference

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className="-rotate-90 transform"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-bg-tertiary)"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-500 ease-out"
        />
      </svg>
      {showPercent && (
        <span className="absolute text-xs font-medium text-[var(--color-text-primary)]">
          {Math.round(normalizedProgress)}%
        </span>
      )}
    </div>
  )
}

/**
 * Linear progress bar component
 */
interface ProgressBarProps {
  progress: number // 0-100
  className?: string
  color?: string
  height?: number
  showPercent?: boolean
}

export function ProgressBar({
  progress,
  className,
  color = 'var(--color-accent-blue)',
  height = 6,
  showPercent = false,
}: ProgressBarProps) {
  const normalizedProgress = Math.min(100, Math.max(0, progress))

  return (
    <div className={cn('w-full', className)}>
      <div
        className="w-full overflow-hidden rounded-full bg-[var(--color-bg-tertiary)]"
        style={{ height }}
      >
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${normalizedProgress}%`,
            backgroundColor: color,
          }}
        />
      </div>
      {showPercent && (
        <span className="mt-1 block text-right text-xs text-[var(--color-text-secondary)]">
          {Math.round(normalizedProgress)}%
        </span>
      )}
    </div>
  )
}
