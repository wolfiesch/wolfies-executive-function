import { useState } from 'react'
import { Loader2, Plus, X } from 'lucide-react'
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
import { useCreateGoal } from '@/api/hooks'
import { LIFE_AREAS, LIFE_AREA_LABELS } from '@/lib/constants'
import type { GoalCreateInput, LifeArea } from '@/types/models'

interface GoalCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Dialog for creating a new goal.
 *
 * Features:
 * - Title field (required)
 * - Description textarea
 * - Target date picker
 * - Life area dropdown
 * - Dynamic milestones list
 */
export function GoalCreateDialog({ open, onOpenChange }: GoalCreateDialogProps) {
  const createGoal = useCreateGoal()

  // Form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [lifeArea, setLifeArea] = useState<LifeArea | ''>('')
  const [milestones, setMilestones] = useState<string[]>([''])

  const resetForm = () => {
    setTitle('')
    setDescription('')
    setTargetDate('')
    setLifeArea('')
    setMilestones([''])
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) return

    const input: GoalCreateInput = {
      title: title.trim(),
    }

    if (description.trim()) input.description = description.trim()
    if (targetDate) input.target_date = targetDate
    if (lifeArea) input.life_area = lifeArea

    // Filter out empty milestones
    const validMilestones = milestones
      .map((m) => m.trim())
      .filter(Boolean)
      .map((title) => ({ title }))
    if (validMilestones.length > 0) {
      input.milestones = validMilestones
    }

    createGoal.mutate(input, {
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

  const addMilestone = () => {
    setMilestones([...milestones, ''])
  }

  const removeMilestone = (index: number) => {
    setMilestones(milestones.filter((_, i) => i !== index))
  }

  const updateMilestone = (index: number, value: string) => {
    const updated = [...milestones]
    updated[index] = value
    setMilestones(updated)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>Create New Goal</DialogTitle>
          <DialogDescription>
            Set a goal with milestones to track your progress.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Title */}
          <div>
            <label
              htmlFor="goal-title"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Goal Title <span className="text-[var(--color-accent-red)]">*</span>
            </label>
            <Input
              id="goal-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What do you want to achieve?"
              autoFocus
              required
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="goal-description"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Description
            </label>
            <textarea
              id="goal-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Why is this goal important? What does success look like?"
              rows={3}
              className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
            />
          </div>

          {/* Target Date and Life Area row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Target Date */}
            <div>
              <label
                htmlFor="goal-target-date"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Target Date
              </label>
              <Input
                id="goal-target-date"
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </div>

            {/* Life Area */}
            <div>
              <label
                htmlFor="goal-life-area"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Life Area
              </label>
              <select
                id="goal-life-area"
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

          {/* Milestones */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-sm font-medium text-[var(--color-text-primary)]">
                Milestones
              </label>
              <button
                type="button"
                onClick={addMilestone}
                className="flex items-center gap-1 text-xs text-[var(--color-accent-blue)] hover:underline"
              >
                <Plus className="h-3 w-3" />
                Add milestone
              </button>
            </div>
            <div className="space-y-2">
              {milestones.map((milestone, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    value={milestone}
                    onChange={(e) => updateMilestone(index, e.target.value)}
                    placeholder={`Milestone ${index + 1}`}
                  />
                  {milestones.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeMilestone(index)}
                      className="rounded p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-accent-red)]"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">
              Break your goal into smaller, achievable steps
            </p>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleClose(false)}
              disabled={createGoal.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!title.trim() || createGoal.isPending}>
              {createGoal.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Goal'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
