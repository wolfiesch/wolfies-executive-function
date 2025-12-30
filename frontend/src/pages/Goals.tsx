import { Target, Plus, ChevronRight, TrendingUp, Calendar, MoreHorizontal } from 'lucide-react'
import { AppShell } from '@/components/layout'

/**
 * Goals - Goals dashboard page
 *
 * Features:
 * - Active goals list with progress indicators
 * - Goal detail view with milestones
 * - Progress tracking over time
 * - OKR-style hierarchy (Objectives > Key Results)
 *
 * Design pattern: **Progress Dashboard** - visual indicators and
 * metrics make abstract progress concrete and motivating.
 */
export function Goals() {
  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Goals</h1>
            <p className="text-[var(--color-text-secondary)]">
              Track your objectives and key results
            </p>
          </div>
          <button className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90">
            <Plus className="h-4 w-4" />
            New Goal
          </button>
        </div>

        {/* Overview stats */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            icon={Target}
            label="Active Goals"
            value="4"
            subtext="in progress"
            color="blue"
          />
          <StatCard
            icon={TrendingUp}
            label="Overall Progress"
            value="62%"
            subtext="this quarter"
            color="green"
          />
          <StatCard
            icon={Calendar}
            label="Due Soon"
            value="2"
            subtext="this month"
            color="orange"
          />
        </div>

        {/* Goals list */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <GoalCard key={i} />
          ))}
        </div>

        {/* Empty state (would show when no goals) */}
        {false && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] py-16 text-center">
            <Target className="h-12 w-12 text-[var(--color-text-tertiary)]" />
            <h3 className="mt-4 text-lg font-medium text-[var(--color-text-primary)]">
              No goals yet
            </h3>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Create your first goal to start tracking progress
            </p>
            <button className="mt-4 flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white">
              <Plus className="h-4 w-4" />
              Create Goal
            </button>
          </div>
        )}
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
  color: 'green' | 'blue' | 'orange'
}

function StatCard({ icon: Icon, label, value, subtext, color }: StatCardProps) {
  const colorClasses = {
    green: 'text-[var(--color-accent-green)]',
    blue: 'text-[var(--color-accent-blue)]',
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

// Goal card component
function GoalCard() {
  const progress = Math.floor(Math.random() * 80) + 10 // Random progress 10-90%

  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5 transition-colors hover:border-[var(--color-border-default)]">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-[var(--color-accent-purple)]/20 p-2">
            <Target className="h-5 w-5 text-[var(--color-accent-purple)]" />
          </div>
          <div>
            <div className="h-5 w-48 rounded bg-[var(--color-bg-tertiary)]" />
            <div className="mt-1 flex items-center gap-2">
              <span className="rounded bg-[var(--color-bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-text-tertiary)]">
                Q1 2025
              </span>
              <span className="text-xs text-[var(--color-text-tertiary)]">Personal</span>
            </div>
          </div>
        </div>
        <button className="rounded p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-secondary)]">
          <MoreHorizontal className="h-5 w-5" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="text-[var(--color-text-secondary)]">Progress</span>
          <span className="font-medium text-[var(--color-text-primary)]">{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-bg-tertiary)]">
          <div
            className="h-full rounded-full bg-[var(--color-accent-purple)]"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Key results preview */}
      <div className="mt-4 space-y-2">
        <div className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]">
          Key Results
        </div>
        <div className="space-y-1">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-sm border border-[var(--color-border-default)]" />
              <div className="h-3 flex-1 rounded bg-[var(--color-bg-tertiary)]" />
            </div>
          ))}
        </div>
      </div>

      {/* View details link */}
      <button className="mt-4 flex items-center gap-1 text-sm text-[var(--color-accent-blue)] hover:underline">
        View details <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}

export default Goals
