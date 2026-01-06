import { cn } from '@/lib/utils'

interface TaskCardSkeletonProps {
    className?: string
}

/**
 * Loading skeleton for TaskCard component
 * Matches the layout of TaskCard for seamless loading states
 */
export function TaskCardSkeleton({ className }: TaskCardSkeletonProps) {
    return (
        <div
            className={cn(
                'animate-pulse rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-3',
                className
            )}
        >
            <div className="flex items-start gap-3">
                {/* Checkbox skeleton */}
                <div className="mt-0.5 h-5 w-5 flex-shrink-0 rounded bg-[var(--color-bg-hover)]" />

                {/* Content skeleton */}
                <div className="flex-1 space-y-2">
                    {/* Title */}
                    <div className="h-4 w-3/4 rounded bg-[var(--color-bg-hover)]" />

                    {/* Metadata row */}
                    <div className="flex items-center gap-3">
                        <div className="h-3 w-16 rounded bg-[var(--color-bg-hover)]" />
                        <div className="h-3 w-20 rounded bg-[var(--color-bg-hover)]" />
                    </div>

                    {/* Tags */}
                    <div className="flex gap-1">
                        <div className="h-5 w-12 rounded bg-[var(--color-bg-hover)]" />
                        <div className="h-5 w-16 rounded bg-[var(--color-bg-hover)]" />
                    </div>
                </div>

                {/* Priority badge skeleton */}
                <div className="h-5 w-5 flex-shrink-0 rounded-full bg-[var(--color-bg-hover)]" />
            </div>
        </div>
    )
}

/**
 * Multiple skeleton cards for list loading state
 */
interface TaskCardSkeletonListProps {
    count?: number
    className?: string
}

export function TaskCardSkeletonList({
    count = 3,
    className,
}: TaskCardSkeletonListProps) {
    return (
        <div className={cn('space-y-3', className)}>
            {Array.from({ length: count }).map((_, i) => (
                <TaskCardSkeleton key={i} />
            ))}
        </div>
    )
}
