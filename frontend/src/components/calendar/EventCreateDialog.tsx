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
import { useCreateEvent } from '@/api/hooks'
import { EVENT_TYPES } from '@/lib/constants'
import type { CalendarEventCreateInput, EventType } from '@/types/models'

interface EventCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Optional default date for the event */
  defaultDate?: string
}

/**
 * Dialog for creating a new calendar event.
 *
 * Features:
 * - Title field (required)
 * - Description textarea
 * - Start date/time pickers
 * - End date/time pickers
 * - All-day toggle
 * - Location field
 * - Event type dropdown
 */
export function EventCreateDialog({ open, onOpenChange, defaultDate }: EventCreateDialogProps) {
  const createEvent = useCreateEvent()

  // Get default times (now + 1 hour for start, + 2 hours for end)
  const getDefaultDateTime = () => {
    const now = new Date()
    if (defaultDate) {
      now.setFullYear(
        parseInt(defaultDate.slice(0, 4)),
        parseInt(defaultDate.slice(5, 7)) - 1,
        parseInt(defaultDate.slice(8, 10))
      )
    }
    now.setMinutes(0, 0, 0)
    now.setHours(now.getHours() + 1)
    return now
  }

  const formatDate = (date: Date) => date.toISOString().slice(0, 10)
  const formatTime = (date: Date) => date.toTimeString().slice(0, 5)

  const defaultStart = getDefaultDateTime()
  const defaultEnd = new Date(defaultStart.getTime() + 60 * 60 * 1000) // +1 hour

  // Form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [startDate, setStartDate] = useState(formatDate(defaultStart))
  const [startTime, setStartTime] = useState(formatTime(defaultStart))
  const [endDate, setEndDate] = useState(formatDate(defaultEnd))
  const [endTime, setEndTime] = useState(formatTime(defaultEnd))
  const [allDay, setAllDay] = useState(false)
  const [location, setLocation] = useState('')
  const [eventType, setEventType] = useState<EventType>('meeting')

  const resetForm = () => {
    const newStart = getDefaultDateTime()
    const newEnd = new Date(newStart.getTime() + 60 * 60 * 1000)
    setTitle('')
    setDescription('')
    setStartDate(formatDate(newStart))
    setStartTime(formatTime(newStart))
    setEndDate(formatDate(newEnd))
    setEndTime(formatTime(newEnd))
    setAllDay(false)
    setLocation('')
    setEventType('meeting')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) return

    // Construct ISO datetime strings
    const startDateTime = allDay
      ? `${startDate}T00:00:00`
      : `${startDate}T${startTime}:00`
    const endDateTime = allDay
      ? `${endDate}T23:59:59`
      : `${endDate}T${endTime}:00`

    const input: CalendarEventCreateInput = {
      title: title.trim(),
      start_time: startDateTime,
      end_time: endDateTime,
      all_day: allDay,
      event_type: eventType,
    }

    if (description.trim()) input.description = description.trim()
    if (location.trim()) input.location = location.trim()

    createEvent.mutate(input, {
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
          <DialogTitle>Create New Event</DialogTitle>
          <DialogDescription>
            Add a new event to your calendar.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Title */}
          <div>
            <label
              htmlFor="event-title"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Event Title <span className="text-[var(--color-accent-red)]">*</span>
            </label>
            <Input
              id="event-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Meeting with..."
              autoFocus
              required
            />
          </div>

          {/* All-day toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="event-all-day"
              checked={allDay}
              onChange={(e) => setAllDay(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] text-[var(--color-accent-blue)] focus:ring-[var(--color-accent-blue)]"
            />
            <label
              htmlFor="event-all-day"
              className="text-sm text-[var(--color-text-primary)]"
            >
              All-day event
            </label>
          </div>

          {/* Start Date/Time row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="event-start-date"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Start Date
              </label>
              <Input
                id="event-start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>
            {!allDay && (
              <div>
                <label
                  htmlFor="event-start-time"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
                >
                  Start Time
                </label>
                <Input
                  id="event-start-time"
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  required
                />
              </div>
            )}
          </div>

          {/* End Date/Time row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="event-end-date"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                End Date
              </label>
              <Input
                id="event-end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
            {!allDay && (
              <div>
                <label
                  htmlFor="event-end-time"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
                >
                  End Time
                </label>
                <Input
                  id="event-end-time"
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  required
                />
              </div>
            )}
          </div>

          {/* Event Type and Location row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Event Type */}
            <div>
              <label
                htmlFor="event-type"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Event Type
              </label>
              <select
                id="event-type"
                value={eventType}
                onChange={(e) => setEventType(e.target.value as EventType)}
                className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
              >
                {EVENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Location */}
            <div>
              <label
                htmlFor="event-location"
                className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
              >
                Location
              </label>
              <Input
                id="event-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Room / Zoom link"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="event-description"
              className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]"
            >
              Description
            </label>
            <textarea
              id="event-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add notes or agenda..."
              rows={3}
              className="w-full rounded-lg border border-[var(--color-border-default)] bg-[var(--color-bg-tertiary)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent-blue)] focus:outline-none"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleClose(false)}
              disabled={createEvent.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!title.trim() || createEvent.isPending}>
              {createEvent.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Event'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
