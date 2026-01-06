import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationShortcuts, useGlobalShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useUIStore } from '@/stores/uiStore'

interface KeyboardContextValue {
    /** All registered shortcuts for display in help modal */
    shortcuts: ShortcutInfo[]
    /** Whether shortcuts help modal is open */
    isHelpOpen: boolean
    /** Toggle help modal */
    toggleHelp: () => void
}

export interface ShortcutInfo {
    keys: string
    description: string
    category: 'navigation' | 'global' | 'list' | 'page'
}

const KeyboardContext = React.createContext<KeyboardContextValue | null>(null)

/**
 * Global keyboard shortcuts provider
 * 
 * Registers global shortcuts and provides context for page-specific shortcuts.
 * Wraps the entire app to ensure shortcuts work everywhere.
 */
export function KeyboardProvider({ children }: { children: React.ReactNode }) {
    const navigate = useNavigate()
    const { toggleCommandPalette } = useUIStore()
    const [isHelpOpen, setIsHelpOpen] = React.useState(false)

    // Register navigation shortcuts (g + letter)
    useNavigationShortcuts(navigate)

    // Register global shortcuts
    useGlobalShortcuts({
        onCommandPalette: toggleCommandPalette,
        onNewTask: () => {
            navigate('/tasks')
            // Could trigger new task modal here
        },
        onNewNote: () => {
            navigate('/notes')
        },
        onNewEvent: () => {
            navigate('/calendar')
        },
        onSearch: toggleCommandPalette,
    })

    // ? opens keyboard shortcuts help
    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (
                e.key === '?' &&
                !e.metaKey &&
                !e.ctrlKey &&
                document.activeElement?.tagName !== 'INPUT' &&
                document.activeElement?.tagName !== 'TEXTAREA'
            ) {
                e.preventDefault()
                setIsHelpOpen((prev) => !prev)
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [])

    // All registered shortcuts for help display
    const shortcuts: ShortcutInfo[] = React.useMemo(
        () => [
            // Global
            { keys: '⌘ K', description: 'Open command palette', category: 'global' },
            { keys: '⌘ N', description: 'New task', category: 'global' },
            { keys: '⌘ ⇧ N', description: 'New note', category: 'global' },
            { keys: '⌘ E', description: 'New event', category: 'global' },
            { keys: '/', description: 'Focus search', category: 'global' },
            { keys: '?', description: 'Show keyboard shortcuts', category: 'global' },

            // Navigation
            { keys: 'G H', description: 'Go to Dashboard', category: 'navigation' },
            { keys: 'G T', description: 'Go to Tasks', category: 'navigation' },
            { keys: 'G C', description: 'Go to Calendar', category: 'navigation' },
            { keys: 'G N', description: 'Go to Notes', category: 'navigation' },
            { keys: 'G G', description: 'Go to Goals', category: 'navigation' },
            { keys: 'G P', description: 'Go to Projects', category: 'navigation' },
            { keys: 'G S', description: 'Go to Settings', category: 'navigation' },

            // List navigation
            { keys: 'J', description: 'Move down', category: 'list' },
            { keys: 'K', description: 'Move up', category: 'list' },
            { keys: 'X', description: 'Toggle selection', category: 'list' },
            { keys: 'E', description: 'Edit selected', category: 'list' },
            { keys: 'D', description: 'Mark done', category: 'list' },
            { keys: 'Esc', description: 'Clear selection', category: 'list' },
        ],
        []
    )

    const toggleHelp = React.useCallback(() => setIsHelpOpen((prev) => !prev), [])

    const value = React.useMemo(
        () => ({ shortcuts, isHelpOpen, toggleHelp }),
        [shortcuts, isHelpOpen, toggleHelp]
    )

    return (
        <KeyboardContext.Provider value={value}>
            {children}
            {isHelpOpen && <KeyboardShortcutsModal onClose={() => setIsHelpOpen(false)} />}
        </KeyboardContext.Provider>
    )
}

export function useKeyboardContext() {
    const context = React.useContext(KeyboardContext)
    if (!context) {
        throw new Error('useKeyboardContext must be used within KeyboardProvider')
    }
    return context
}

/**
 * Modal showing all keyboard shortcuts
 */
function KeyboardShortcutsModal({ onClose }: { onClose: () => void }) {
    const { shortcuts } = useKeyboardContext()

    // Group shortcuts by category
    const grouped = React.useMemo(() => {
        const groups: Record<string, ShortcutInfo[]> = {}
        shortcuts.forEach((s) => {
            if (!groups[s.category]) groups[s.category] = []
            groups[s.category].push(s)
        })
        return groups
    }, [shortcuts])

    const categoryLabels: Record<string, string> = {
        global: 'Global',
        navigation: 'Navigation',
        list: 'List Navigation',
        page: 'Page Specific',
    }

    // Close on Escape
    React.useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose()
        }
        window.addEventListener('keydown', handleEscape)
        return () => window.removeEventListener('keydown', handleEscape)
    }, [onClose])

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Modal */}
            <div
                className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-6 shadow-xl"
                role="dialog"
                aria-modal="true"
                aria-labelledby="shortcuts-title"
            >
                <h2
                    id="shortcuts-title"
                    className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]"
                >
                    Keyboard Shortcuts
                </h2>

                <div className="max-h-96 space-y-6 overflow-y-auto">
                    {Object.entries(grouped).map(([category, items]) => (
                        <div key={category}>
                            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]">
                                {categoryLabels[category] || category}
                            </h3>
                            <div className="space-y-1">
                                {items.map((shortcut) => (
                                    <div
                                        key={shortcut.keys}
                                        className="flex items-center justify-between py-1"
                                    >
                                        <span className="text-sm text-[var(--color-text-secondary)]">
                                            {shortcut.description}
                                        </span>
                                        <kbd className="rounded bg-[var(--color-bg-tertiary)] px-2 py-0.5 font-mono text-xs text-[var(--color-text-primary)]">
                                            {shortcut.keys}
                                        </kbd>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-4 flex justify-end">
                    <button
                        onClick={onClose}
                        className="rounded-lg bg-[var(--color-bg-tertiary)] px-4 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
                    >
                        Close <kbd className="ml-2 text-xs opacity-60">Esc</kbd>
                    </button>
                </div>
            </div>
        </>
    )
}

export default KeyboardProvider
