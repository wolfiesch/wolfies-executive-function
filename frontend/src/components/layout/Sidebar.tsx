import * as React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Compass,
  CheckSquare,
  Calendar,
  FileText,
  Target,
  FolderKanban,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/constants'
import { useUIStore } from '@/stores/uiStore'

/**
 * Icon mapping from string names to Lucide components.
 * This allows us to define icons by name in constants and render them dynamically.
 *
 * Design pattern: **Lookup Table / Dictionary Pattern**
 * - Maps string keys to component references
 * - Decouples data (NAV_ITEMS) from rendering (icon components)
 * - Enables serializable configuration
 */
const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  Compass,
  CheckSquare,
  Calendar,
  FileText,
  Target,
  FolderKanban,
}

/**
 * Keyboard shortcut hints for navigation items
 * Maps nav item IDs to their shortcut keys (g + letter)
 */
const shortcutHints: Record<string, string> = {
  today: 'G H',
  tasks: 'G T',
  calendar: 'G C',
  notes: 'G N',
  goals: 'G G',
  projects: 'G P',
}

/**
 * Sidebar navigation component with keyboard navigation support.
 *
 * Features:
 * - Collapsible sidebar with toggle button
 * - Active state highlighting based on current route
 * - Full keyboard navigation (Arrow Up/Down to navigate links)
 * - Settings link at bottom
 * - Accessibility: proper ARIA attributes and focus management
 *
 * CS concept: **Event Delegation** - single keyboard handler on nav element
 * manages focus for all child links, reducing event listener count.
 */
export function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const navRef = React.useRef<HTMLElement>(null)

  /**
   * Keyboard navigation handler for sidebar links.
   * Arrow keys move focus between navigation items.
   *
   * Complexity: O(n) where n = number of links (typically 6-8, so effectively O(1))
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const links = navRef.current?.querySelectorAll<HTMLAnchorElement>('a[role="menuitem"]')
    if (!links || links.length === 0) return

    const currentIndex = Array.from(links).findIndex(
      (link) => link === document.activeElement
    )

    let nextIndex: number | null = null

    switch (e.key) {
      case 'ArrowDown':
      case 'j': // Vim-style navigation
        e.preventDefault()
        nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % links.length
        break
      case 'ArrowUp':
      case 'k': // Vim-style navigation
        e.preventDefault()
        nextIndex = currentIndex <= 0 ? links.length - 1 : currentIndex - 1
        break
      case 'Home':
        e.preventDefault()
        nextIndex = 0
        break
      case 'End':
        e.preventDefault()
        nextIndex = links.length - 1
        break
    }

    if (nextIndex !== null) {
      links[nextIndex]?.focus()
    }
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col',
        'border-r border-border-subtle bg-bg-secondary',
        'transition-[width] duration-[var(--transition-normal)] ease-in-out',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo/Brand */}
      <div
        className={cn(
          'flex h-14 items-center border-b border-border-subtle px-4',
          sidebarCollapsed ? 'justify-center' : 'gap-3'
        )}
      >
        {/* Logo Icon */}
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-accent-blue">
          <Sparkles className="h-5 w-5 text-white" aria-hidden="true" />
        </div>
        {!sidebarCollapsed && (
          <span className="text-lg font-semibold text-text-primary">
            Life Planner
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav
        ref={navRef}
        className="flex-1 overflow-y-auto px-2 py-4"
        role="menu"
        aria-label="Main navigation"
        onKeyDown={handleKeyDown}
      >
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = iconMap[item.icon]
            // Support both exact match and prefix match for nested routes
            const isActive =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path)

            return (
              <li key={item.id}>
                <NavLink
                  to={item.path}
                  role="menuitem"
                  className={cn(
                    'group flex items-center gap-3 rounded-lg px-3 py-2.5',
                    'text-sm font-medium transition-colors duration-[var(--transition-fast)]',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-secondary',
                    isActive
                      ? 'bg-bg-active text-text-primary'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary',
                    sidebarCollapsed && 'justify-center px-2'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  {Icon && (
                    <Icon
                      className={cn(
                        'h-5 w-5 flex-shrink-0',
                        isActive ? 'text-accent-blue' : ''
                      )}
                      aria-hidden="true"
                    />
                  )}
                  {!sidebarCollapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      {shortcutHints[item.id] && (
                        <kbd className="ml-auto rounded bg-bg-tertiary px-1.5 py-0.5 font-mono text-[10px] text-text-tertiary opacity-0 transition-opacity group-hover:opacity-100">
                          {shortcutHints[item.id]}
                        </kbd>
                      )}
                    </>
                  )}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Bottom Section: Settings & Collapse Toggle */}
      <div className="border-t border-border-subtle px-2 py-3">
        {/* Settings Link */}
        <NavLink
          to="/settings"
          role="menuitem"
          className={cn(
            'flex items-center gap-3 rounded-lg px-3 py-2.5',
            'text-sm font-medium transition-colors duration-[var(--transition-fast)]',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue',
            location.pathname === '/settings'
              ? 'bg-bg-active text-text-primary'
              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary',
            sidebarCollapsed && 'justify-center px-2'
          )}
          title={sidebarCollapsed ? 'Settings' : undefined}
        >
          <Settings
            className={cn(
              'h-5 w-5 flex-shrink-0',
              location.pathname === '/settings' ? 'text-accent-blue' : ''
            )}
            aria-hidden="true"
          />
          {!sidebarCollapsed && <span>Settings</span>}
        </NavLink>

        {/* Collapse Toggle Button */}
        <button
          onClick={toggleSidebar}
          className={cn(
            'mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5',
            'text-sm font-medium text-text-tertiary',
            'transition-colors duration-[var(--transition-fast)]',
            'hover:bg-bg-hover hover:text-text-secondary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue',
            sidebarCollapsed && 'justify-center px-2'
          )}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={sidebarCollapsed ? 'Expand' : 'Collapse'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          ) : (
            <>
              <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
