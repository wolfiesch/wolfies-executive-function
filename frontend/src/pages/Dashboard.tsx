import {
  CheckCircle2,
  Clock,
  Target,
  Calendar,
  Plus,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'
import { AppShell } from '@/components/layout'
import { useDashboardData } from '@/api/hooks'
import { TaskCard } from '@/components/tasks/TaskCard'
import { format, parseISO } from 'date-fns'

// Local type for calendar event (matches API response)
interface DashboardEvent {
  id: number | string
  title: string
  start_time: string
  end_time?: string
  all_day?: boolean
  location?: string
}

/**
 * Dashboard - Today view (landing page)
 *
 * This is the main entry point showing the user's day at a glance:
 * - Overview stats (tasks done, upcoming events, active goals)
 * - Priority tasks for today
 * - Upcoming events
 * - Quick capture input
 *
 * Design pattern: **Dashboard Pattern** - aggregates key metrics and
 * actionable items from multiple domains into a single view.
 *
 * CS concept: **React Query** - handles caching, background refetching,
 * and loading states automatically. Data stays fresh without manual refresh.
 */
export function Dashboard() {
  // Fetch dashboard data from API
  const { data: dashboardData, isLoading, error } = useDashboardData()

  // Get current hour to personalize greeting
  const hour = new Date().getHours()
  const greeting =
    hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  // Extract stats from API response or use defaults
  const stats = dashboardData?.stats ?? {
    tasks_today: 0,
    tasks_overdue: 0,
    completion_rate: 0,
    streak_days: 0,
  }

  // Calculate tasks done from completion rate
  const tasksDone = Math.round((stats.completion_rate / 100) * stats.tasks_today)
  const tasksTotal = stats.tasks_today

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Header with greeting and quick capture */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
              {greeting}!
            </h1>
            <p className="text-[var(--color-text-secondary)]">
              Here's what's on your plate today
            </p>
          </div>

          {/* Quick capture button */}
          <button className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90">
            <Plus className="h-4 w-4" />
            Quick Capture
          </button>
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-3 rounded-lg border border-[var(--color-accent-red)]/30 bg-[var(--color-accent-red)]/10 p-4">
            <AlertCircle className="h-5 w-5 text-[var(--color-accent-red)]" />
            <p className="text-sm text-[var(--color-accent-red)]">
              Failed to load dashboard data. Please try refreshing.
            </p>
          </div>
        )}

        {/* Stats cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={CheckCircle2}
            label="Tasks Done"
            value={isLoading ? '...' : `${tasksDone}/${tasksTotal}`}
            subtext="today"
            color="green"
          />
          <StatCard
            icon={Clock}
            label="Overdue"
            value={isLoading ? '...' : String(stats.tasks_overdue)}
            subtext="tasks"
            color={stats.tasks_overdue > 0 ? 'orange' : 'blue'}
          />
          <StatCard
            icon={Target}
            label="Goals"
            value={isLoading ? '...' : String(dashboardData?.goal_summaries?.length ?? 0)}
            subtext="in progress"
            color="purple"
          />
          <StatCard
            icon={Calendar}
            label="Events"
            value={isLoading ? '...' : String(dashboardData?.upcoming_events?.length ?? 0)}
            subtext="upcoming"
            color="blue"
          />
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Priority tasks */}
          <section className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
                Priority Tasks
              </h2>
              <button className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                View all <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Task list - real data or loading state */}
            <div className="space-y-3">
              {isLoading ? (
                <>
                  <TaskPlaceholder />
                  <TaskPlaceholder />
                  <TaskPlaceholder />
                </>
              ) : dashboardData?.priority_tasks?.length ? (
                dashboardData.priority_tasks.slice(0, 5).map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))
              ) : (
                <p className="py-4 text-center text-sm text-[var(--color-text-tertiary)]">
                  No priority tasks for today. Great job! 🎉
                </p>
              )}
            </div>
          </section>

          {/* Upcoming events */}
          <section className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
                Upcoming Events
              </h2>
              <button className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
                View calendar <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Events list - real data or loading state */}
            <div className="space-y-3">
              {isLoading ? (
                <>
                  <EventPlaceholder />
                  <EventPlaceholder />
                </>
              ) : dashboardData?.upcoming_events?.length ? (
                dashboardData.upcoming_events.slice(0, 5).map((event) => (
                  <EventItem key={event.id} event={event} />
                ))
              ) : (
                <p className="py-4 text-center text-sm text-[var(--color-text-tertiary)]">
                  No upcoming events. Enjoy your free time!
                </p>
              )}
            </div>
          </section>
        </div>

        {/* Quick capture input (alternative location) */}
        <section className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5">
          <h2 className="mb-3 text-lg font-semibold text-[var(--color-text-primary)]">
            Quick Capture
          </h2>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="What's on your mind? Press Enter to add a task..."
              className="flex-1 rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-4 py-2.5 text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
            />
            <button className="rounded-lg bg-[var(--color-accent-blue)] px-4 py-2.5 font-medium text-white hover:bg-[var(--color-accent-blue)]/90">
              Add
            </button>
          </div>
          <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">
            Tip: Use natural language like "Call mom tomorrow at 3pm" or "Buy groceries #shopping"
          </p>
        </section>
      </div>
    </AppShell>
  )
}

// Stat card component
interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  subtext: string
  color: 'green' | 'blue' | 'purple' | 'orange'
}

function StatCard({ icon: Icon, label, value, subtext, color }: StatCardProps) {
  const colorClasses = {
    green: 'text-[var(--color-accent-green)]',
    blue: 'text-[var(--color-accent-blue)]',
    purple: 'text-[var(--color-accent-purple)]',
    orange: 'text-[var(--color-accent-orange)]',
  }

  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-4">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg bg-[var(--color-bg-tertiary)] p-2 ${colorClasses[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-[var(--color-text-secondary)]">{label}</p>
          <p className="text-xl font-semibold text-[var(--color-text-primary)]">
            {value}{' '}
            <span className="text-sm font-normal text-[var(--color-text-tertiary)]">
              {subtext}
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}

// Placeholder components for tasks and events
function TaskPlaceholder() {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-tertiary)] p-3">
      <div className="h-5 w-5 rounded border-2 border-[var(--color-border-default)]" />
      <div className="flex-1">
        <div className="h-4 w-3/4 rounded bg-[var(--color-bg-hover)]" />
        <div className="mt-1 h-3 w-1/3 rounded bg-[var(--color-bg-hover)]" />
      </div>
    </div>
  )
}

function EventPlaceholder() {
  return (
    <div className="flex gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-tertiary)] p-3">
      <div className="flex flex-col items-center rounded bg-[var(--color-bg-hover)] px-3 py-2">
        <span className="text-xs text-[var(--color-text-tertiary)]">---</span>
        <span className="font-semibold text-[var(--color-text-primary)]">--</span>
      </div>
      <div className="flex-1">
        <div className="h-4 w-1/2 rounded bg-[var(--color-bg-hover)]" />
        <div className="mt-1 h-3 w-1/4 rounded bg-[var(--color-bg-hover)]" />
      </div>
    </div>
  )
}

// Event item component for displaying calendar events
function EventItem({ event }: { event: DashboardEvent }) {
  // Parse the event start time
  const startDate = event.start_time ? parseISO(event.start_time) : new Date()
  const dayName = format(startDate, 'EEE')
  const dayNum = format(startDate, 'd')
  const timeStr = event.all_day ? 'All day' : format(startDate, 'h:mm a')

  return (
    <div className="flex gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-tertiary)] p-3">
      <div className="flex flex-col items-center rounded bg-[var(--color-accent-blue)]/10 px-3 py-2">
        <span className="text-xs text-[var(--color-accent-blue)]">{dayName}</span>
        <span className="font-semibold text-[var(--color-text-primary)]">{dayNum}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="truncate font-medium text-[var(--color-text-primary)]">
          {event.title}
        </p>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {timeStr}
          {event.location && ` · ${event.location}`}
        </p>
      </div>
    </div>
  )
}

export default Dashboard
