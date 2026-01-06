import { motion } from 'framer-motion'
import { Plus, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  /** Preset variant for illustrated empty states */
  variant?: 'tasks' | 'calendar' | 'notes' | 'goals' | 'search'
  /** Search query for "no results" states */
  searchQuery?: string
  className?: string
}

/**
 * Enhanced empty state component with illustrations
 * 
 * Features:
 * - Optional SVG illustrations per variant
 * - Animated entrance
 * - Clear CTA button with icon
 * - Backward compatible with simple icon-based usage
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant,
  searchQuery,
  className,
}: EmptyStateProps) {
  // Get variant-specific illustration if available
  const Illustration = variant ? illustrations[variant] : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
    >
      {/* Illustration (if variant provided) */}
      {Illustration && (
        <div className="mb-4">
          <Illustration />
        </div>
      )}

      {/* Icon badge (if icon provided and no illustration) */}
      {Icon && !Illustration && (
        <div className="mb-4 rounded-full bg-[var(--color-bg-tertiary)] p-4">
          <Icon
            className="h-8 w-8 text-[var(--color-text-tertiary)]"
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </div>
      )}

      {/* Title */}
      <h3 className="text-lg font-medium text-[var(--color-text-primary)]">
        {variant === 'search' && searchQuery
          ? `No results for "${searchQuery}"`
          : title}
      </h3>

      {/* Description */}
      {description && (
        <p className="mt-2 max-w-sm text-sm text-[var(--color-text-secondary)]">
          {description}
        </p>
      )}

      {/* Action button */}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-6 flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90"
        >
          <Plus className="h-4 w-4" />
          {action.label}
        </button>
      )}
    </motion.div>
  )
}

// ============================================================
// ILLUSTRATIONS
// ============================================================

const illustrations: Record<string, React.FC> = {
  tasks: TasksIllustration,
  calendar: CalendarIllustration,
  notes: NotesIllustration,
  goals: GoalsIllustration,
  search: SearchIllustration,
}

function TasksIllustration() {
  return (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none" aria-hidden="true">
      {/* Checkbox stack */}
      <rect x="30" y="20" width="60" height="16" rx="4" fill="var(--color-bg-tertiary)" opacity="0.5" />
      <rect x="25" y="40" width="70" height="16" rx="4" fill="var(--color-bg-tertiary)" opacity="0.7" />
      <rect x="20" y="60" width="80" height="16" rx="4" fill="var(--color-bg-tertiary)" />
      {/* Checkmark accent */}
      <circle cx="90" cy="68" r="8" fill="var(--color-accent-green)" opacity="0.2" />
      <path d="M87 68L89 70L93 66" stroke="var(--color-accent-green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CalendarIllustration() {
  return (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none" aria-hidden="true">
      <rect x="20" y="20" width="80" height="60" rx="8" fill="var(--color-bg-tertiary)" />
      <rect x="20" y="20" width="80" height="16" rx="8" fill="var(--color-accent-blue)" opacity="0.3" />
      {/* Grid dots */}
      {[0, 1, 2, 3].map((row) =>
        [0, 1, 2, 3, 4, 5].map((col) => (
          <circle key={`${row}-${col}`} cx={32 + col * 11} cy={46 + row * 9} r="2" fill="var(--color-text-tertiary)" opacity="0.3" />
        ))
      )}
      <circle cx="54" cy="55" r="6" fill="var(--color-accent-blue)" opacity="0.5" />
    </svg>
  )
}

function NotesIllustration() {
  return (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none" aria-hidden="true">
      <rect x="25" y="15" width="70" height="70" rx="4" fill="var(--color-bg-tertiary)" />
      <rect x="35" y="30" width="50" height="4" rx="2" fill="var(--color-text-tertiary)" opacity="0.3" />
      <rect x="35" y="42" width="40" height="4" rx="2" fill="var(--color-text-tertiary)" opacity="0.3" />
      <rect x="35" y="54" width="45" height="4" rx="2" fill="var(--color-text-tertiary)" opacity="0.3" />
      <rect x="35" y="66" width="30" height="4" rx="2" fill="var(--color-text-tertiary)" opacity="0.3" />
      {/* Link highlight */}
      <rect x="55" y="42" width="20" height="4" rx="2" fill="var(--color-accent-purple)" opacity="0.5" />
    </svg>
  )
}

function GoalsIllustration() {
  return (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none" aria-hidden="true">
      <circle cx="60" cy="50" r="35" fill="none" stroke="var(--color-bg-tertiary)" strokeWidth="8" />
      <circle cx="60" cy="50" r="25" fill="none" stroke="var(--color-accent-orange)" strokeWidth="6" opacity="0.3" />
      <circle cx="60" cy="50" r="15" fill="none" stroke="var(--color-accent-orange)" strokeWidth="4" opacity="0.5" />
      <circle cx="60" cy="50" r="6" fill="var(--color-accent-orange)" />
      <path d="M60 15 A35 35 0 0 1 95 50" fill="none" stroke="var(--color-accent-orange)" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
    </svg>
  )
}

function SearchIllustration() {
  return (
    <svg width="120" height="100" viewBox="0 0 120 100" fill="none" aria-hidden="true">
      <circle cx="55" cy="45" r="20" fill="none" stroke="var(--color-text-tertiary)" strokeWidth="4" opacity="0.5" />
      <line x1="70" y1="60" x2="85" y2="75" stroke="var(--color-text-tertiary)" strokeWidth="4" strokeLinecap="round" opacity="0.5" />
      <text x="55" y="52" textAnchor="middle" fontSize="18" fill="var(--color-text-tertiary)" opacity="0.5">?</text>
    </svg>
  )
}

export default EmptyState
