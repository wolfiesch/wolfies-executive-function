import { useState } from 'react'
import { Search, Plus, FileText, Hash, Clock, AlertCircle, Loader2 } from 'lucide-react'
import { AppShell } from '@/components/layout'
import { useNotes } from '@/api/hooks'
import type { Note } from '@/types/models'
import { formatRelativeTime } from '@/lib/utils'

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
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch notes from API
  const { data: notes, isLoading, error } = useNotes(
    searchQuery ? { search: searchQuery } : undefined
  )
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
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] py-2 pl-10 pr-4 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              />
            </div>
          </div>

          {/* Error state */}
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-[var(--color-accent-red)]/30 bg-[var(--color-accent-red)]/10 p-3">
              <AlertCircle className="h-4 w-4 text-[var(--color-accent-red)]" />
              <p className="text-xs text-[var(--color-accent-red)]">Failed to load notes</p>
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--color-accent-blue)]" />
            </div>
          )}

          {/* Note items */}
          {!isLoading && notes && notes.length > 0 && (
            <div className="space-y-2">
              {notes.map((note) => (
                <NoteListItemReal
                  key={note.id}
                  note={note}
                  selected={selectedNote?.id === note.id}
                  onClick={() => setSelectedNote(note)}
                />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && (!notes || notes.length === 0) && (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--color-text-secondary)]">
                {searchQuery ? 'No notes match your search' : 'No notes yet'}
              </p>
            </div>
          )}
        </div>

        {/* Note editor/viewer */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="mx-auto max-w-3xl">
            {selectedNote ? (
              <>
                {/* Note header */}
                <div className="mb-6">
                  <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {selectedNote.title}
                  </h1>
                  <div className="mt-2 flex items-center gap-4 text-sm text-[var(--color-text-secondary)]">
                    <span className="capitalize">{selectedNote.note_type}</span>
                    <span>·</span>
                    <span>{formatRelativeTime(selectedNote.updated_at)}</span>
                    <span>·</span>
                    <span>{selectedNote.word_count} words</span>
                  </div>
                </div>

                {/* Note tags */}
                {selectedNote.tags.length > 0 && (
                  <div className="mb-4 flex flex-wrap gap-2">
                    {selectedNote.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-[var(--color-bg-tertiary)] px-3 py-1 text-sm text-[var(--color-text-secondary)]"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Note content */}
                <div className="prose prose-sm max-w-none text-[var(--color-text-primary)]">
                  <p className="whitespace-pre-wrap">{selectedNote.content}</p>
                </div>
              </>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-[var(--color-text-secondary)]">
                  Select a note to view its contents
                </p>
              </div>
            )}
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

// Real note list item component
function NoteListItemReal({
  note,
  selected,
  onClick,
}: {
  note: Note
  selected?: boolean
  onClick?: () => void
}) {
  // Truncate content for preview
  const preview = note.content?.slice(0, 100) || ''

  return (
    <button
      onClick={onClick}
      className={`w-full rounded-lg border p-3 text-left transition-colors ${
        selected
          ? 'border-[var(--color-accent-blue)] bg-[var(--color-bg-tertiary)]'
          : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-hover)]'
      }`}
    >
      <div className="flex items-start justify-between">
        <h3 className="font-medium text-[var(--color-text-primary)] line-clamp-1">
          {note.title}
        </h3>
        {note.is_pinned && (
          <span className="text-xs text-[var(--color-accent-orange)]">📌</span>
        )}
      </div>
      {preview && (
        <p className="mt-1 text-sm text-[var(--color-text-secondary)] line-clamp-2">
          {preview}
        </p>
      )}
      <div className="mt-2 flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
        <span className="capitalize">{note.note_type}</span>
        <span>·</span>
        <span>{formatRelativeTime(note.updated_at)}</span>
      </div>
    </button>
  )
}

export default Notes
