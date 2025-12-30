import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import { AnimatePresence, motion } from 'framer-motion'
import {
  LayoutDashboard,
  CheckSquare,
  Calendar,
  FileText,
  Target,
  FolderKanban,
  Settings,
  Plus,
  Search,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS, KEYBOARD_SHORTCUTS } from '@/lib/constants'
import { useUIStore } from '@/stores/uiStore'

/**
 * Icon mapping for navigation items and actions.
 */
const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  CheckSquare,
  Calendar,
  FileText,
  Target,
  FolderKanban,
  Settings,
  Plus,
  Search,
}

/**
 * Quick action definitions for the command palette.
 *
 * Design pattern: **Command Pattern** - encapsulates actions as data objects
 * that can be searched, displayed, and executed uniformly.
 */
interface QuickAction {
  id: string
  label: string
  icon: string
  shortcut?: string
  action: () => void
  group: 'navigation' | 'create' | 'actions'
}

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
}

const dialogVariants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: -20,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      type: 'spring' as const,
      damping: 25,
      stiffness: 400,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -10,
    transition: {
      duration: 0.15,
    },
  },
}

/**
 * CommandPalette component for quick navigation and actions.
 *
 * Features:
 * - Fuzzy search across all commands
 * - Navigation shortcuts (go to pages)
 * - Quick actions (new task, new note, etc.)
 * - Keyboard navigation (arrow keys, enter to select)
 * - Opens with Cmd+K
 *
 * CS concept: **Fuzzy Matching** - cmdk library uses fuzzy search algorithm
 * to match user input against command labels, allowing for typos and partial matches.
 *
 * Design pattern: **Command Palette / Spotlight** - common in modern productivity apps
 * (VSCode, Slack, Notion) for keyboard-first power users.
 */
export function CommandPalette() {
  const navigate = useNavigate()
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore()
  const [search, setSearch] = React.useState('')
  const inputRef = React.useRef<HTMLInputElement>(null)

  /**
   * Build quick actions dynamically from NAV_ITEMS and other sources.
   * Memoized to avoid recreating on every render.
   */
  const quickActions = React.useMemo<QuickAction[]>(() => {
    // Navigation actions from NAV_ITEMS
    const navActions: QuickAction[] = NAV_ITEMS.map((item) => ({
      id: `nav-${item.id}`,
      label: `Go to ${item.label}`,
      icon: item.icon,
      shortcut: KEYBOARD_SHORTCUTS[`go${item.label.replace(/\s/g, '')}` as keyof typeof KEYBOARD_SHORTCUTS] as string | undefined,
      action: () => {
        navigate(item.path)
        setCommandPaletteOpen(false)
      },
      group: 'navigation' as const,
    }))

    // Settings navigation
    navActions.push({
      id: 'nav-settings',
      label: 'Go to Settings',
      icon: 'Settings',
      shortcut: KEYBOARD_SHORTCUTS.goSettings,
      action: () => {
        navigate('/settings')
        setCommandPaletteOpen(false)
      },
      group: 'navigation' as const,
    })

    // Create actions
    const createActions: QuickAction[] = [
      {
        id: 'create-task',
        label: 'New Task',
        icon: 'Plus',
        shortcut: KEYBOARD_SHORTCUTS.newTask,
        action: () => {
          // TODO: Open new task modal
          setCommandPaletteOpen(false)
          console.log('Create new task')
        },
        group: 'create' as const,
      },
      {
        id: 'create-note',
        label: 'New Note',
        icon: 'Plus',
        shortcut: KEYBOARD_SHORTCUTS.newNote,
        action: () => {
          // TODO: Open new note modal
          setCommandPaletteOpen(false)
          console.log('Create new note')
        },
        group: 'create' as const,
      },
      {
        id: 'create-event',
        label: 'New Event',
        icon: 'Plus',
        shortcut: KEYBOARD_SHORTCUTS.newEvent,
        action: () => {
          // TODO: Open new event modal
          setCommandPaletteOpen(false)
          console.log('Create new event')
        },
        group: 'create' as const,
      },
    ]

    return [...createActions, ...navActions]
  }, [navigate, setCommandPaletteOpen])

  /**
   * Global keyboard shortcut to open command palette.
   * Uses Cmd+K on Mac, Ctrl+K on Windows/Linux.
   */
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  /**
   * Focus input when palette opens.
   */
  React.useEffect(() => {
    if (commandPaletteOpen) {
      // Small delay to ensure the dialog is rendered
      setTimeout(() => inputRef.current?.focus(), 0)
    } else {
      setSearch('')
    }
  }, [commandPaletteOpen])

  /**
   * Handle item selection.
   */
  const handleSelect = (actionId: string) => {
    const action = quickActions.find((a) => a.id === actionId)
    if (action) {
      action.action()
    }
  }

  /**
   * Group actions by their group property.
   */
  const groupedActions = React.useMemo(() => {
    const groups: Record<string, QuickAction[]> = {
      create: [],
      navigation: [],
      actions: [],
    }

    for (const action of quickActions) {
      groups[action.group].push(action)
    }

    return groups
  }, [quickActions])

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={() => setCommandPaletteOpen(false)}
            aria-hidden="true"
          />

          {/* Command Dialog */}
          <motion.div
            variants={dialogVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2"
          >
            <Command
              className={cn(
                'overflow-hidden rounded-xl border border-border-default',
                'bg-bg-secondary shadow-lg'
              )}
              onKeyDown={(e) => {
                // Close on Escape
                if (e.key === 'Escape') {
                  setCommandPaletteOpen(false)
                }
              }}
            >
              {/* Search Input */}
              <div className="flex items-center border-b border-border-subtle px-4">
                <Search className="h-4 w-4 text-text-tertiary" aria-hidden="true" />
                <Command.Input
                  ref={inputRef}
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Type a command or search..."
                  className={cn(
                    'flex-1 bg-transparent px-3 py-4 text-sm text-text-primary',
                    'placeholder:text-text-tertiary',
                    'focus:outline-none'
                  )}
                />
                <kbd className="rounded bg-bg-tertiary px-1.5 py-0.5 text-xs text-text-tertiary">
                  ESC
                </kbd>
              </div>

              {/* Command List */}
              <Command.List className="max-h-80 overflow-y-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-text-secondary">
                  No results found.
                </Command.Empty>

                {/* Create Group */}
                {groupedActions.create.length > 0 && (
                  <Command.Group
                    heading="Create"
                    className="mb-2 px-2 text-xs font-medium text-text-tertiary"
                  >
                    {groupedActions.create.map((action) => (
                      <CommandItem
                        key={action.id}
                        action={action}
                        onSelect={handleSelect}
                      />
                    ))}
                  </Command.Group>
                )}

                {/* Navigation Group */}
                {groupedActions.navigation.length > 0 && (
                  <Command.Group
                    heading="Navigation"
                    className="mb-2 px-2 text-xs font-medium text-text-tertiary"
                  >
                    {groupedActions.navigation.map((action) => (
                      <CommandItem
                        key={action.id}
                        action={action}
                        onSelect={handleSelect}
                      />
                    ))}
                  </Command.Group>
                )}
              </Command.List>

              {/* Footer with hints */}
              <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2 text-xs text-text-tertiary">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="rounded bg-bg-tertiary px-1 py-0.5">↑↓</kbd>
                    navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="rounded bg-bg-tertiary px-1 py-0.5">↵</kbd>
                    select
                  </span>
                </div>
                <span>Cmd+K to toggle</span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

/**
 * Individual command item component.
 */
interface CommandItemProps {
  action: QuickAction
  onSelect: (id: string) => void
}

function CommandItem({ action, onSelect }: CommandItemProps) {
  const Icon = iconMap[action.icon]

  return (
    <Command.Item
      value={action.label}
      onSelect={() => onSelect(action.id)}
      className={cn(
        'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2',
        'text-sm text-text-secondary',
        'data-[selected=true]:bg-bg-hover data-[selected=true]:text-text-primary',
        'transition-colors duration-[var(--transition-fast)]'
      )}
    >
      {Icon && <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />}
      <span className="flex-1">{action.label}</span>
      {action.shortcut && (
        <kbd className="rounded bg-bg-tertiary px-1.5 py-0.5 text-xs text-text-tertiary">
          {action.shortcut}
        </kbd>
      )}
    </Command.Item>
  )
}
