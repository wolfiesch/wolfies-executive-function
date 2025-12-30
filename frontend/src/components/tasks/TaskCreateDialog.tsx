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
import { useCreateTask } from '@/api/hooks'
import type { TaskCreateInput, Priority } from '@/types/models'

interface TaskCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Dialog for creating a new task.
 *
 * Features:
 * - Title field (required)
 * - Description textarea
 * - Priority dropdown (1-5)
 * - Due date picker
 * - Estimated time input
 * - Tags input
 *
 * Uses optimistic updates via React Query for instant feedback.
 */
export function TaskCreateDialog({ open, onOpenChange }: TaskCreateDialogProps) {
  const createTask = useCreateTask()

  // Form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>(3)
  const [dueDate, setDueDate] = useState('')
  const [estimatedMinutes, setEstimatedMinutes] = useState('')
  const [tags, setTags] = useState('')

  const resetForm = () => {
    setTitle('')
    setDescription('')
    setPriority(3)
    setDueDate('')
    setEstimatedMinutes('')
    setTags('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) return

    const input: TaskCreateInput = {
      title: title.trim(),
      priority,
    }

    // Only add optional fields if they have values
    if (description.trim()) input.description = description.trim()
    if (dueDate) input.due_date = dueDate
    if (estimatedMinutes) input.estimated_minutes = parseInt(estimatedMinutes, 10)
    if (tags.trim()) {
      input.tags = tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
    }

    createTask.mutate(input, {
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
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
          <DialogDescription>
            Add a new task to your list. Fill in the details below.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Title - required */}
          <div>
            <label
              htmlFor="title"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Title <span className="text-[var(--color-accent-red)]">*</span>
            </label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs to be done?"
              autoFocus
              required
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="description"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add more details..."
              rows={3}
              className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
            />
          </div>

          {/* Priority and Due Date row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Priority */}
            <div>
              <label
                htmlFor="priority"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Priority
              </label>
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value, 10) as Priority)}
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              >
                <option value={5}>P5 - Critical</option>
                <option value={4}>P4 - High</option>
                <option value={3}>P3 - Normal</option>
                <option value={2}>P2 - Low</option>
                <option value={1}>P1 - Optional</option>
              </select>
            </div>

            {/* Due Date */}
            <div>
              <label
                htmlFor="dueDate"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Due Date
              </label>
              <Input
                id="dueDate"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
          </div>

          {/* Estimated time */}
          <div>
            <label
              htmlFor="estimatedMinutes"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Estimated Time (minutes)
            </label>
            <Input
              id="estimatedMinutes"
              type="number"
              min={1}
              value={estimatedMinutes}
              onChange={(e) => setEstimatedMinutes(e.target.value)}
              placeholder="30"
            />
          </div>

          {/* Tags */}
          <div>
            <label
              htmlFor="tags"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Tags
            </label>
            <Input
              id="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="work, urgent, email (comma-separated)"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleClose(false)}
              disabled={createTask.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!title.trim() || createTask.isPending}>
              {createTask.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Task'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
