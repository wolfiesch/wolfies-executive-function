import { cn } from '@/lib/utils'
import { format, isWithinInterval, setHours, setMinutes, startOfDay } from 'date-fns'

interface TimelineEvent {
    id: string | number
    title: string
    start_time: string
    end_time?: string
    type?: 'event' | 'time-block'
    location?: string
}

interface TimelineProps {
    events: TimelineEvent[]
    className?: string
    /** Starting hour (0-23), default 6 */
    startHour?: number
    /** Ending hour (0-23), default 22 */
    endHour?: number
}

/**
 * Vertical timeline component showing events and time blocks
 * Features:
 * - Time labels on left axis
 * - Current time indicator
 * - Event/time-block visual distinction
 */
export function Timeline({
    events,
    className,
    startHour = 6,
    endHour = 22,
}: TimelineProps) {
    const now = new Date()
    const currentHour = now.getHours()
    const currentMinute = now.getMinutes()

    // Generate hour slots
    const hours = Array.from(
        { length: endHour - startHour + 1 },
        (_, i) => startHour + i
    )

    // Check if current time is within visible range
    const showNowIndicator = currentHour >= startHour && currentHour <= endHour

    // Calculate position for current time indicator (percentage)
    const nowPosition =
        ((currentHour - startHour) * 60 + currentMinute) /
        ((endHour - startHour + 1) * 60)

    // Group events by hour for display
    const getEventsForHour = (hour: number): TimelineEvent[] => {
        const dayStart = startOfDay(now)
        const hourStart = setMinutes(setHours(dayStart, hour), 0)
        const hourEnd = setMinutes(setHours(dayStart, hour), 59)

        return events.filter((event) => {
            const eventStart = new Date(event.start_time)
            return isWithinInterval(eventStart, { start: hourStart, end: hourEnd })
        })
    }

    return (
        <div className={cn('relative', className)}>
            {/* Time axis line */}
            <div className="absolute left-16 top-0 bottom-0 w-px bg-[var(--color-border-subtle)]" />

            {/* Hour slots */}
            <div className="space-y-0">
                {hours.map((hour) => {
                    const hourEvents = getEventsForHour(hour)
                    const isCurrentHour = hour === currentHour

                    return (
                        <div key={hour} className="relative flex gap-4 min-h-[60px]">
                            {/* Time label */}
                            <div
                                className={cn(
                                    'w-12 flex-shrink-0 pt-1 text-right text-sm',
                                    isCurrentHour
                                        ? 'font-medium text-[var(--color-accent-blue)]'
                                        : 'text-[var(--color-text-tertiary)]'
                                )}
                            >
                                {format(setHours(new Date(), hour), 'h a')}
                            </div>

                            {/* Time marker dot */}
                            <div className="relative flex-shrink-0 w-3">
                                <div
                                    className={cn(
                                        'absolute left-1/2 top-2 h-2.5 w-2.5 -translate-x-1/2 rounded-full',
                                        isCurrentHour
                                            ? 'bg-[var(--color-accent-blue)] ring-4 ring-[var(--color-accent-blue)]/20'
                                            : 'bg-[var(--color-border-default)]'
                                    )}
                                />
                            </div>

                            {/* Content area */}
                            <div className="flex-1 pb-4 min-w-0">
                                {hourEvents.length > 0 ? (
                                    <div className="space-y-2">
                                        {hourEvents.map((event) => (
                                            <TimelineItem key={event.id} event={event} />
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-sm text-[var(--color-text-tertiary)] italic pt-1">
                                        Free time
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Current time indicator */}
            {showNowIndicator && (
                <div
                    className="absolute left-0 right-0 flex items-center pointer-events-none z-10"
                    style={{ top: `${nowPosition * 100}%` }}
                >
                    <div className="w-12 pr-2 text-right text-xs font-semibold text-[var(--color-accent-red)]">
                        Now
                    </div>
                    <div className="flex-1 h-0.5 bg-[var(--color-accent-red)]" />
                    <div className="h-3 w-3 rounded-full bg-[var(--color-accent-red)] -ml-1.5" />
                </div>
            )}
        </div>
    )
}

/**
 * Individual timeline item
 */
function TimelineItem({ event }: { event: TimelineEvent }) {
    const startTime = new Date(event.start_time)
    const endTime = event.end_time ? new Date(event.end_time) : null

    const isTimeBlock = event.type === 'time-block'

    return (
        <div
            className={cn(
                'rounded-md border-l-4 px-3 py-2 text-sm',
                isTimeBlock
                    ? 'border-[var(--color-accent-purple)] bg-[var(--color-accent-purple)]/10'
                    : 'border-[var(--color-accent-blue)] bg-[var(--color-accent-blue)]/10'
            )}
        >
            <div className="font-medium text-[var(--color-text-primary)] truncate">
                {event.title}
            </div>
            <div className="text-[var(--color-text-tertiary)]">
                {format(startTime, 'h:mm a')}
                {endTime && ` - ${format(endTime, 'h:mm a')}`}
                {event.location && ` · ${event.location}`}
            </div>
        </div>
    )
}

export default Timeline
