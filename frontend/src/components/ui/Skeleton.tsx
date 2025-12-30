import * as React from 'react'
import { cn } from '@/lib/utils'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Width of the skeleton (supports Tailwind or CSS values) */
  width?: string
  /** Height of the skeleton (supports Tailwind or CSS values) */
  height?: string
  /** Make skeleton circular */
  circle?: boolean
}

/**
 * Skeleton loading placeholder component.
 *
 * @example
 * ```tsx
 * // Basic usage
 * <Skeleton className="h-4 w-48" />
 *
 * // Avatar placeholder
 * <Skeleton circle className="h-10 w-10" />
 *
 * // Card placeholder
 * <div className="space-y-2">
 *   <Skeleton className="h-4 w-full" />
 *   <Skeleton className="h-4 w-3/4" />
 * </div>
 * ```
 */
const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, width, height, circle = false, style, ...props }, ref) => {
    // Build inline style if width/height provided
    const computedStyle: React.CSSProperties = {
      ...style,
      ...(width && { width }),
      ...(height && { height }),
    }

    return (
      <div
        ref={ref}
        className={cn(
          'animate-pulse bg-bg-tertiary',
          circle ? 'rounded-full' : 'rounded-[var(--radius-md)]',
          className
        )}
        style={Object.keys(computedStyle).length > 0 ? computedStyle : undefined}
        aria-hidden="true"
        {...props}
      />
    )
  }
)

Skeleton.displayName = 'Skeleton'

/**
 * Pre-built skeleton for text lines.
 */
const SkeletonText = React.forwardRef<
  HTMLDivElement,
  Omit<SkeletonProps, 'circle'> & { lines?: number }
>(({ className, lines = 1, ...props }, ref) => (
  <div ref={ref} className={cn('space-y-2', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        className={cn('h-4', i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full')}
        {...props}
      />
    ))}
  </div>
))

SkeletonText.displayName = 'SkeletonText'

/**
 * Pre-built skeleton for avatar.
 */
const SkeletonAvatar = React.forwardRef<
  HTMLDivElement,
  Omit<SkeletonProps, 'circle'> & { size?: 'sm' | 'md' | 'lg' }
>(({ className, size = 'md', ...props }, ref) => {
  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  }

  return (
    <Skeleton
      ref={ref}
      circle
      className={cn(sizeClasses[size], className)}
      {...props}
    />
  )
})

SkeletonAvatar.displayName = 'SkeletonAvatar'

/**
 * Pre-built skeleton for card.
 */
const SkeletonCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-[var(--radius-lg)] border border-border-subtle bg-bg-secondary p-4',
      className
    )}
    {...props}
  >
    <div className="flex items-center gap-3">
      <SkeletonAvatar />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
    <div className="mt-4 space-y-2">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-4/6" />
    </div>
  </div>
))

SkeletonCard.displayName = 'SkeletonCard'

export { Skeleton, SkeletonText, SkeletonAvatar, SkeletonCard }
