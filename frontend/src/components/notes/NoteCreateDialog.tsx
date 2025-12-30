import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useCreateNote } from '@/api/hooks'
import { NOTE_TYPES, LIFE_AREAS, LIFE_AREA_LABELS } from '@/lib/constants'
import type { NoteCreateInput, NoteType, LifeArea } from '@/types/models'

interface NoteCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Dialog for creating a new note.
 *
 * Features:
 * - Title field (required)
 * - Content textarea with markdown support hint
 * - Note type dropdown (note, journal, meeting, reference)
 * - Life area dropdown
 * - Tags input
 */
export function NoteCreateDialog({ open, onOpenChange }: NoteCreateDialogProps) {
  const createNote = useCreateNote()

  // Form state
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [noteType, setNoteType] = useState<NoteType>('note')
  const [lifeArea, setLifeArea] = useState<LifeArea | ''>('')
  const [tags, setTags] = useState('')

  const resetForm = () => {
    setTitle('')
    setContent('')
    setNoteType('note')
    setLifeArea('')
    setTags('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) return

    const input: NoteCreateInput = {
      title: title.trim(),
      note_type: noteType,
    }

    if (content.trim()) input.content = content.trim()
    if (lifeArea) input.life_area = lifeArea
    if (tags.trim()) {
      input.tags = tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
    }

    createNote.mutate(input, {
      onSuccess: () => {
        resetForm()
        onOpenChange(false)
      },
    })
  }

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      resetForm()
    }
    onOpenChange(isOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Create New Note</DialogTitle>
          <DialogDescription>
            Add a new note to your knowledge base. Supports markdown.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Title */}
          <div>
            <label
              htmlFor="note-title"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Title <span className="text-[var(--color-accent-red)]">*</span>
            </label>
            <Input
              id="note-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Note title..."
              autoFocus
              required
            />
          </div>

          {/* Content */}
          <div>
            <label
              htmlFor="note-content"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Content
            </label>
            <textarea
              id="note-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your note... (markdown supported)"
              rows={6}
              className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none font-mono"
            />
          </div>

          {/* Note Type and Life Area row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Note Type */}
            <div>
              <label
                htmlFor="note-type"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Note Type
              </label>
              <select
                id="note-type"
                value={noteType}
                onChange={(e) => setNoteType(e.target.value as NoteType)}
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              >
                {NOTE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Life Area */}
            <div>
              <label
                htmlFor="note-life-area"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Life Area
              </label>
              <select
                id="note-life-area"
                value={lifeArea}
                onChange={(e) => setLifeArea(e.target.value as LifeArea | '')}
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              >
                <option value="">Select...</option>
                {LIFE_AREAS.map((area) => (
                  <option key={area} value={area}>
                    {LIFE_AREA_LABELS[area]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Tags */}
          <div>
            <label
              htmlFor="note-tags"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Tags
            </label>
            <Input
              id="note-tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="work, ideas, reference (comma-separated)"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleClose(false)}
              disabled={createNote.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!title.trim() || createNote.isPending}>
              {createNote.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Note'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
