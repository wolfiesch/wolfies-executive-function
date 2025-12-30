import { useState } from 'react'
import { Sparkles, Plus, Calendar, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

interface QuickCaptureProps {
  onSubmit?: (input: string, type: 'task' | 'event' | 'note') => void
  className?: string
}

/**
 * Quick capture input for rapid task/event/note creation
 * Parses natural language input and shows preview
 */
export function QuickCapture({ onSubmit, className }: QuickCaptureProps) {
  const [input, setInput] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      // Default to task, but could be determined by NLP parsing
      onSubmit?.(input.trim(), 'task')
      setInput('')
    }
  }

  const handleQuickAction = (type: 'task' | 'event' | 'note') => {
    if (input.trim()) {
      onSubmit?.(input.trim(), type)
      setInput('')
    }
  }

  return (
    <div
      className={cn(
        'rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] transition-colors',
        isFocused && 'border-[var(--color-accent-blue)]',
        className
      )}
    >
      <form onSubmit={handleSubmit}>
        <div className="flex items-center gap-3 px-4 py-3">
          <Sparkles className="h-5 w-5 flex-shrink-0 text-[var(--color-accent-blue)]" />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Add task, event, or note..."
            className="flex-1 bg-transparent text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none"
          />
        </div>

        {/* Quick action buttons shown when focused or has input */}
        {(isFocused || input) && (
          <div className="flex items-center gap-2 border-t border-[var(--color-border-subtle)] px-4 py-2">
            <span className="text-xs text-[var(--color-text-tertiary)]">
              Quick add:
            </span>
            <button
              type="button"
              onClick={() => handleQuickAction('task')}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
            >
              <Plus className="h-3 w-3" />
              Task
            </button>
            <button
              type="button"
              onClick={() => handleQuickAction('event')}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
            >
              <Calendar className="h-3 w-3" />
              Event
            </button>
            <button
              type="button"
              onClick={() => handleQuickAction('note')}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
            >
              <FileText className="h-3 w-3" />
              Note
            </button>
            <div className="ml-auto">
              <kbd className="rounded bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 text-xs text-[var(--color-text-tertiary)]">
                Enter
              </kbd>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
