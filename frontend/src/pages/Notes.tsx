import { Search, Plus, FileText, Hash, Clock, MoreHorizontal } from 'lucide-react'
import { AppShell } from '@/components/layout'

/**
 * Notes - Notes list and editor page
 *
 * Features:
 * - Sidebar with recent notes, tags, and search
 * - Note list with previews
 * - Note editor/viewer panel
 *
 * Design pattern: **Three-Panel Layout** - navigation > list > detail
 * for efficient browsing of hierarchical content.
 */
export function Notes() {
  return (
    <AppShell>
      <div className="flex h-[calc(100vh-theme(spacing.20))]">
        {/* Sidebar with tags and filters */}
        <div className="w-56 shrink-0 overflow-y-auto border-r border-[var(--color-border-subtle)] pr-4">
          <div className="mb-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Notes</h1>
            <button className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]">
              <Plus className="h-5 w-5" />
            </button>
          </div>

          {/* Quick filters */}
          <div className="mb-4 space-y-1">
            <SidebarItem icon={Clock} label="Recent" count={12} active />
            <SidebarItem icon={FileText} label="All Notes" count={47} />
          </div>

          {/* Tags section */}
          <div className="mb-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
              Tags
            </h3>
            <div className="space-y-1">
              <SidebarItem icon={Hash} label="work" count={15} />
              <SidebarItem icon={Hash} label="personal" count={8} />
              <SidebarItem icon={Hash} label="ideas" count={12} />
              <SidebarItem icon={Hash} label="meeting-notes" count={9} />
              <SidebarItem icon={Hash} label="reference" count={3} />
            </div>
          </div>

          {/* Note types */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)]">
              Types
            </h3>
            <div className="space-y-1">
              <SidebarItem icon={FileText} label="Notes" count={35} />
              <SidebarItem icon={FileText} label="Journal" count={7} />
              <SidebarItem icon={FileText} label="Meetings" count={5} />
            </div>
          </div>
        </div>

        {/* Notes list */}
        <div className="w-80 shrink-0 overflow-y-auto border-r border-[var(--color-border-subtle)] px-4">
          {/* Search */}
          <div className="sticky top-0 z-10 bg-[var(--color-bg-primary)] pb-4 pt-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
              <input
                type="text"
                placeholder="Search notes..."
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] py-2 pl-10 pr-4 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              />
            </div>
          </div>

          {/* Note items */}
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <NoteListItem key={i} selected={i === 1} />
            ))}
          </div>
        </div>

        {/* Note editor/viewer */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="mx-auto max-w-3xl">
            {/* Note header placeholder */}
            <div className="mb-6">
              <div className="h-8 w-2/3 rounded bg-[var(--color-bg-tertiary)]" />
              <div className="mt-2 flex items-center gap-4">
                <div className="h-4 w-24 rounded bg-[var(--color-bg-tertiary)]" />
                <div className="h-4 w-32 rounded bg-[var(--color-bg-tertiary)]" />
              </div>
            </div>

            {/* Note content placeholder */}
            <div className="space-y-4">
              <div className="h-4 w-full rounded bg-[var(--color-bg-tertiary)]" />
              <div className="h-4 w-5/6 rounded bg-[var(--color-bg-tertiary)]" />
              <div className="h-4 w-4/5 rounded bg-[var(--color-bg-tertiary)]" />
              <div className="h-4 w-3/4 rounded bg-[var(--color-bg-tertiary)]" />
              <div className="h-4 w-full rounded bg-[var(--color-bg-tertiary)]" />
              <div className="h-4 w-2/3 rounded bg-[var(--color-bg-tertiary)]" />
            </div>

            {/* Placeholder message */}
            <div className="mt-12 text-center">
              <p className="text-[var(--color-text-secondary)]">
                Note editor will be implemented here
              </p>
              <p className="mt-1 text-sm text-[var(--color-text-tertiary)]">
                Markdown support with bi-directional linking
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}

// Sidebar item component
interface SidebarItemProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  count?: number
  active?: boolean
}

function SidebarItem({ icon: Icon, label, count, active }: SidebarItemProps) {
  return (
    <button
      className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors ${
        active
          ? 'bg-[var(--color-bg-active)] text-[var(--color-text-primary)]'
          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]'
      }`}
    >
      <Icon className="h-4 w-4" />
      <span className="flex-1 text-left">{label}</span>
      {count !== undefined && (
        <span className="text-xs text-[var(--color-text-tertiary)]">{count}</span>
      )}
    </button>
  )
}

// Note list item placeholder
function NoteListItem({ selected }: { selected?: boolean }) {
  return (
    <button
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        selected
          ? 'border-[var(--color-accent-blue)] bg-[var(--color-bg-tertiary)]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-hover)]'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="h-4 w-3/4 rounded bg-[var(--color-bg-hover)]" />
        <MoreHorizontal className="h-4 w-4 text-[var(--color-text-tertiary)]" />
      </div>
      <div className="mt-2 space-y-1">
        <div className="h-3 w-full rounded bg-[var(--color-bg-hover)]" />
        <div className="h-3 w-2/3 rounded bg-[var(--color-bg-hover)]" />
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div className="h-2 w-12 rounded bg-[var(--color-bg-hover)]" />
        <div className="h-2 w-16 rounded bg-[var(--color-bg-hover)]" />
      </div>
    </button>
  )
}

export default Notes
