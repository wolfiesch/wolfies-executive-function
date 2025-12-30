import { useState } from 'react'
import { ChevronLeft, ChevronRight, Plus, Loader2 } from 'lucide-react'
import { AppShell } from '@/components/layout'
import { useTodayEvents } from '@/api/hooks'
import { EventCreateDialog } from '@/components/calendar/EventCreateDialog'
import { format, parseISO, startOfWeek, addDays } from 'date-fns'
import type { CalendarEvent } from '@/types/models'

/**
 * Calendar - Calendar view page
 *
 * Features:
 * - Day/Week/Month view toggle
 * - Navigation between time periods
 * - Event display on calendar grid
 * - Time blocking support
 *
 * Design pattern: **Time-Based Grid Pattern** - visual representation
 * of events on a time axis enables quick comprehension of schedule.
 */
export function Calendar() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false)

  // Fetch events from API
  const { data: events, isLoading } = useTodayEvents()

  // Get current date info for header
  const today = new Date()
  const weekStart = startOfWeek(today, { weekStartsOn: 0 })
  const monthYear = today.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  })

  // Get events for each day of the week
  const getEventsForDay = (dayIndex: number): CalendarEvent[] => {
    if (!events) return []
    const dayDate = addDays(weekStart, dayIndex)
    return events.filter((event) => {
      const eventDate = parseISO(event.start_time)
      return format(eventDate, 'yyyy-MM-dd') === format(dayDate, 'yyyy-MM-dd')
    })
  }

  // Calculate top position and height for an event on the grid
  const getEventPosition = (event: CalendarEvent) => {
    const startDate = parseISO(event.start_time)
    const endDate = parseISO(event.end_time)
    const startHour = startDate.getHours() + startDate.getMinutes() / 60
    const endHour = endDate.getHours() + endDate.getMinutes() / 60
    const duration = endHour - startHour
    return {
      top: `${startHour * 3}rem`,
      height: `${Math.max(duration, 0.5) * 3}rem`,
    }
  }

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-theme(spacing.20))] flex-col">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
              Calendar
            </h1>

            {/* Date navigation */}
            <div className="flex items-center gap-2">
              <button className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]">
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="min-w-[200px] text-center font-medium text-[var(--color-text-primary)]">
                {monthYear}
              </span>
              <button className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]">
                <ChevronRight className="h-5 w-5" />
              </button>
              <button className="ml-2 rounded-lg border border-[var(--color-border-default)] px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
                Today
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* View toggle */}
            <div className="flex rounded-lg border border-[var(--color-border-default)]">
              <ViewButton label="Day" active={false} />
              <ViewButton label="Week" active={true} />
              <ViewButton label="Month" active={false} />
            </div>

            <button
              onClick={() => setCreateDialogOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90"
            >
              <Plus className="h-4 w-4" />
              New Event
            </button>
          </div>
        </div>

        {/* Calendar grid */}
        <div className="flex-1 overflow-hidden rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]">
          {/* Week view header */}
          <div className="grid grid-cols-8 border-b border-[var(--color-border-subtle)]">
            {/* Time column header */}
            <div className="border-r border-[var(--color-border-subtle)] p-2" />

            {/* Day headers */}
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
              <div
                key={day}
                className="border-r border-[var(--color-border-subtle)] p-3 text-center last:border-r-0"
              >
                <p className="text-xs text-[var(--color-text-secondary)]">{day}</p>
                <p
                  className={`mt-1 text-lg font-semibold ${
                    i === today.getDay()
                      ? 'rounded-full bg-[var(--color-accent-blue)] px-2 text-white'
                      : 'text-[var(--color-text-primary)]'
                  }`}
                >
                  {new Date(
                    today.getTime() + (i - today.getDay()) * 24 * 60 * 60 * 1000
                  ).getDate()}
                </p>
              </div>
            ))}
          </div>

          {/* Time grid */}
          <div className="grid h-[calc(100%-60px)] grid-cols-8 overflow-y-auto">
            {/* Time labels */}
            <div className="border-r border-[var(--color-border-subtle)]">
              {Array.from({ length: 24 }, (_, i) => (
                <div
                  key={i}
                  className="h-12 border-b border-[var(--color-border-subtle)] px-2 py-1 text-right text-xs text-[var(--color-text-tertiary)]"
                >
                  {i === 0
                    ? '12 AM'
                    : i < 12
                      ? `${i} AM`
                      : i === 12
                        ? '12 PM'
                        : `${i - 12} PM`}
                </div>
              ))}
            </div>

            {/* Day columns */}
            {Array.from({ length: 7 }, (_, dayIndex) => {
              const dayEvents = getEventsForDay(dayIndex)
              return (
                <div
                  key={dayIndex}
                  className="relative border-r border-[var(--color-border-subtle)] last:border-r-0"
                >
                  {/* Hour grid lines */}
                  {Array.from({ length: 24 }, (_, hourIndex) => (
                    <div
                      key={hourIndex}
                      className="h-12 border-b border-[var(--color-border-subtle)]"
                    />
                  ))}

                  {/* Loading indicator for today's column */}
                  {isLoading && dayIndex === today.getDay() && (
                    <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-bg-secondary)]/50">
                      <Loader2 className="h-5 w-5 animate-spin text-[var(--color-accent-blue)]" />
                    </div>
                  )}

                  {/* Real events from API */}
                  {dayEvents.map((event) => {
                    const pos = getEventPosition(event)
                    return (
                      <div
                        key={event.id}
                        className="absolute left-1 right-1 cursor-pointer rounded border-l-2 border-[var(--color-accent-blue)] bg-[var(--color-accent-blue)]/20 p-1 transition-colors hover:bg-[var(--color-accent-blue)]/30"
                        style={{ top: pos.top, height: pos.height }}
                        title={event.title}
                      >
                        <p className="truncate text-xs font-medium text-[var(--color-accent-blue)]">
                          {event.title}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)]">
                          {event.all_day
                            ? 'All day'
                            : `${format(parseISO(event.start_time), 'h:mm a')} - ${format(parseISO(event.end_time), 'h:mm a')}`}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Create event dialog */}
      <EventCreateDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
    </AppShell>
  )
}

// View toggle button
function ViewButton({ label, active }: { label: string; active: boolean }) {
  return (
    <button
      className={`px-3 py-1.5 text-sm transition-colors first:rounded-l-lg last:rounded-r-lg ${
        active
          ? 'bg-[var(--color-bg-active)] text-[var(--color-text-primary)]'
          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
      }`}
    >
      {label}
    </button>
  )
}

export default Calendar
