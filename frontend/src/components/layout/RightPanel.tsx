import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore, type RightPanelContent } from '@/stores/uiStore'

/**
 * Animation configuration for the slide-in panel.
 *
 * CS concept: **Spring Animation** - uses physics-based motion for natural feel.
 * Framer Motion calculates intermediate frames based on spring physics.
 */
const panelVariants = {
  hidden: {
    x: '100%',
    opacity: 0,
  },
  visible: {
    x: 0,
    opacity: 1,
    transition: {
      type: 'spring' as const,
      damping: 25,
      stiffness: 300,
    },
  },
  exit: {
    x: '100%',
    opacity: 0,
    transition: {
      duration: 0.2,
    },
  },
}

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
}

interface RightPanelProps {
  /** Width of the panel */
  width?: string
  /** Optional children to render instead of default content */
  children?: React.ReactNode
  /** Custom render function for panel content based on content type */
  renderContent?: (content: RightPanelContent) => React.ReactNode
}

/**
 * Slide-out detail panel on the right side of the screen.
 *
 * Features:
 * - Animated slide-in/out with spring physics
 * - Close on Escape key
 * - Close on backdrop click
 * - Renders different content based on type (task, event, note, goal)
 * - Focus trap for accessibility
 *
 * Design pattern: **Compound Component** - can render default content or custom children.
 *
 * Usage:
 * ```tsx
 * // Default content rendering
 * <RightPanel />
 *
 * // Custom content based on type
 * <RightPanel renderContent={(content) => <TaskDetail id={content.id} />} />
 *
 * // Fully custom children
 * <RightPanel>
 *   <MyCustomContent />
 * </RightPanel>
 * ```
 */
export function RightPanel({ width = 'w-96', children, renderContent }: RightPanelProps) {
  const { rightPanelOpen, rightPanelContent, closeRightPanel } = useUIStore()
  const panelRef = React.useRef<HTMLDivElement>(null)

  /**
   * Close panel on Escape key.
   * Using useEffect to add global event listener.
   */
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && rightPanelOpen) {
        closeRightPanel()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [rightPanelOpen, closeRightPanel])

  /**
   * Focus trap: focus the panel when it opens.
   * This ensures keyboard users can immediately interact with the panel.
   */
  React.useEffect(() => {
    if (rightPanelOpen && panelRef.current) {
      // Find first focusable element
      const focusable = panelRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      focusable?.focus()
    }
  }, [rightPanelOpen])

  /**
   * Render content based on type.
   * Default implementation shows placeholder content.
   */
  const defaultRenderContent = (content: RightPanelContent) => {
    const typeLabels: Record<RightPanelContent['type'], string> = {
      task: 'Task Details',
      event: 'Event Details',
      note: 'Note Details',
      goal: 'Goal Details',
    }

    return (
      <div className="p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">
          {typeLabels[content.type]}
        </h2>
        <p className="text-sm text-text-secondary">
          Loading {content.type} with ID: {content.id}
        </p>
        {/* Placeholder for actual content - will be replaced with real components */}
        <div className="mt-6 space-y-4">
          <div className="h-4 w-3/4 animate-pulse rounded bg-bg-tertiary" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-bg-tertiary" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-bg-tertiary" />
        </div>
      </div>
    )
  }

  return (
    <AnimatePresence>
      {rightPanelOpen && (
        <>
          {/* Backdrop - click to close */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            onClick={closeRightPanel}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            ref={panelRef}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              'fixed right-0 top-0 z-50 h-screen',
              'flex flex-col bg-bg-secondary',
              'border-l border-border-subtle shadow-lg',
              width
            )}
            role="dialog"
            aria-modal="true"
            aria-label="Detail panel"
          >
            {/* Panel Header with Close Button */}
            <div className="flex h-14 items-center justify-between border-b border-border-subtle px-4">
              <span className="text-sm font-medium text-text-secondary">
                {rightPanelContent?.type
                  ? `${rightPanelContent.type.charAt(0).toUpperCase()}${rightPanelContent.type.slice(1)}`
                  : 'Details'}
              </span>
              <button
                onClick={closeRightPanel}
                className={cn(
                  'rounded-lg p-1.5 text-text-secondary',
                  'transition-colors duration-[var(--transition-fast)]',
                  'hover:bg-bg-hover hover:text-text-primary',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue'
                )}
                aria-label="Close panel"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-y-auto">
              {children
                ? children
                : rightPanelContent
                  ? (renderContent ?? defaultRenderContent)(rightPanelContent)
                  : null}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
