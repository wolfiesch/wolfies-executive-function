import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { AppShell } from '@/components/layout'

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
  // Get current date info for header
  const today = new Date()
  const monthYear = today.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  })

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

            <button className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90">
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
            {Array.from({ length: 7 }, (_, dayIndex) => (
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

                {/* Event placeholder (example) */}
                {dayIndex === 1 && (
                  <div
                    className="absolute left-1 right-1 rounded bg-[var(--color-accent-blue)]/20 border-l-2 border-[var(--color-accent-blue)] p-1"
                    style={{ top: '9rem', height: '4rem' }}
                  >
                    <p className="truncate text-xs font-medium text-[var(--color-accent-blue)]">
                      Team Standup
                    </p>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      9:00 - 10:00
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
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
