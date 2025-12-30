import { useCallback } from 'react'
import { useHotkeys, type Options } from 'react-hotkeys-hook'

/**
 * Keyboard shortcut configuration
 */
interface ShortcutConfig {
  key: string
  callback: () => void
  description?: string
  enabled?: boolean
  options?: Options
}

/**
 * Hook for registering a single keyboard shortcut
 */
export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  options?: Options
): void {
  useHotkeys(key, callback, options)
}

/**
 * Hook for registering multiple keyboard shortcuts
 */
export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]): void {
  shortcuts.forEach(({ key, callback, enabled = true, options }) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useHotkeys(key, callback, { enabled, ...options })
  })
}

/**
 * Hook for navigation shortcuts (g + letter pattern)
 */
export function useNavigationShortcuts(navigate: (path: string) => void): void {
  const goTo = useCallback(
    (path: string) => {
      navigate(path)
    },
    [navigate]
  )

  // g h - go home/dashboard
  useHotkeys('g h', () => goTo('/'), { enableOnFormTags: false })

  // g t - go to tasks
  useHotkeys('g t', () => goTo('/tasks'), { enableOnFormTags: false })

  // g c - go to calendar
  useHotkeys('g c', () => goTo('/calendar'), { enableOnFormTags: false })

  // g n - go to notes
  useHotkeys('g n', () => goTo('/notes'), { enableOnFormTags: false })

  // g g - go to goals
  useHotkeys('g g', () => goTo('/goals'), { enableOnFormTags: false })

  // g p - go to projects
  useHotkeys('g p', () => goTo('/projects'), { enableOnFormTags: false })

  // g s - go to settings
  useHotkeys('g s', () => goTo('/settings'), { enableOnFormTags: false })
}

/**
 * Hook for list navigation shortcuts (j/k/x/e/d)
 */
export function useListNavigationShortcuts(handlers: {
  onMoveDown?: () => void
  onMoveUp?: () => void
  onSelect?: () => void
  onEdit?: () => void
  onMarkDone?: () => void
  onEscape?: () => void
}): void {
  useHotkeys('j', () => handlers.onMoveDown?.(), { enableOnFormTags: false })
  useHotkeys('k', () => handlers.onMoveUp?.(), { enableOnFormTags: false })
  useHotkeys('x', () => handlers.onSelect?.(), { enableOnFormTags: false })
  useHotkeys('e', () => handlers.onEdit?.(), { enableOnFormTags: false })
  useHotkeys('d', () => handlers.onMarkDone?.(), { enableOnFormTags: false })
  useHotkeys('Escape', () => handlers.onEscape?.())
}

/**
 * Hook for global shortcuts
 */
export function useGlobalShortcuts(handlers: {
  onCommandPalette?: () => void
  onNewTask?: () => void
  onNewNote?: () => void
  onNewEvent?: () => void
  onSearch?: () => void
}): void {
  // Command palette
  useHotkeys('mod+k', (e) => {
    e.preventDefault()
    handlers.onCommandPalette?.()
  })

  // New task
  useHotkeys('mod+n', (e) => {
    e.preventDefault()
    handlers.onNewTask?.()
  })

  // New note
  useHotkeys('mod+shift+n', (e) => {
    e.preventDefault()
    handlers.onNewNote?.()
  })

  // New event
  useHotkeys('mod+e', (e) => {
    e.preventDefault()
    handlers.onNewEvent?.()
  })

  // Focus search
  useHotkeys('/', (e) => {
    // Only if not in an input field
    if (
      document.activeElement?.tagName !== 'INPUT' &&
      document.activeElement?.tagName !== 'TEXTAREA'
    ) {
      e.preventDefault()
      handlers.onSearch?.()
    }
  })
}
