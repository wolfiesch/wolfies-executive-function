import { useLocation } from 'react-router-dom'
import { Search, Command, Bell, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/constants'
import { useUIStore } from '@/stores/uiStore'

/**
 * Get page title and breadcrumb info from current path.
 * Returns the nav item label for the current route.
 *
 * Design pattern: **Derived State** - computes display data from route state
 * rather than storing it separately.
 */
function getPageInfo(pathname: string): { title: string; breadcrumbs: string[] } {
  // Find matching nav item
  const navItem = NAV_ITEMS.find((item) =>
    item.path === '/' ? pathname === '/' : pathname.startsWith(item.path)
  )

  if (navItem) {
    return {
      title: navItem.label,
      breadcrumbs: [navItem.label],
    }
  }

  // Handle settings page
  if (pathname === '/settings') {
    return { title: 'Settings', breadcrumbs: ['Settings'] }
  }

  // Default fallback
  return { title: 'Life Planner', breadcrumbs: [] }
}

interface HeaderProps {
  /** Optional page title override */
  title?: string
  /** Optional breadcrumb items */
  breadcrumbs?: string[]
}

/**
 * Header component with command palette trigger and user actions.
 *
 * Features:
 * - Dynamic page title from route
 * - Optional breadcrumbs
 * - Command palette trigger (Cmd+K)
 * - Notification bell with badge
 * - User avatar/menu placeholder
 *
 * The header is fixed and adjusts its left position based on sidebar state.
 */
export function Header({ title: titleProp, breadcrumbs: breadcrumbsProp }: HeaderProps) {
  const location = useLocation()
  const { sidebarCollapsed, setCommandPaletteOpen } = useUIStore()

  // Derive page info from route if not provided
  const pageInfo = getPageInfo(location.pathname)
  const title = titleProp ?? pageInfo.title
  const breadcrumbs = breadcrumbsProp ?? pageInfo.breadcrumbs

  return (
    <header
      className={cn(
        'fixed right-0 top-0 z-30 flex h-14 items-center gap-4',
        'border-b border-border-subtle bg-bg-secondary px-4',
        'transition-[left] duration-[var(--transition-normal)] ease-in-out',
        sidebarCollapsed ? 'left-16' : 'left-64'
      )}
    >
      {/* Page Title & Breadcrumbs */}
      <div className="flex items-center gap-2">
        {breadcrumbs.length > 1 ? (
          // Show breadcrumbs when there's a hierarchy
          <nav aria-label="Breadcrumb" className="flex items-center gap-1">
            {breadcrumbs.map((crumb, index) => (
              <span key={crumb} className="flex items-center gap-1">
                {index > 0 && (
                  <ChevronRight
                    className="h-4 w-4 text-text-tertiary"
                    aria-hidden="true"
                  />
                )}
                <span
                  className={cn(
                    'text-sm',
                    index === breadcrumbs.length - 1
                      ? 'font-semibold text-text-primary'
                      : 'text-text-secondary'
                  )}
                >
                  {crumb}
                </span>
              </span>
            ))}
          </nav>
        ) : (
          // Just show title
          <h1 className="text-lg font-semibold text-text-primary">{title}</h1>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search / Command Palette Trigger */}
      <button
        onClick={() => setCommandPaletteOpen(true)}
        className={cn(
          'flex items-center gap-2 rounded-lg px-3 py-1.5',
          'bg-bg-tertiary text-sm text-text-secondary',
          'transition-colors duration-[var(--transition-fast)]',
          'hover:bg-bg-hover hover:text-text-primary',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue'
        )}
        aria-label="Open command palette"
      >
        <Search className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Search or jump to...</span>
        <kbd
          className={cn(
            'ml-2 hidden items-center gap-0.5 rounded px-1.5 py-0.5',
            'bg-bg-secondary text-xs text-text-tertiary',
            'sm:flex'
          )}
        >
          <Command className="h-3 w-3" aria-hidden="true" />
          <span>K</span>
        </kbd>
      </button>

      {/* Right side actions */}
      <div className="flex items-center gap-1">
        {/* Notifications */}
        <button
          className={cn(
            'relative rounded-lg p-2 text-text-secondary',
            'transition-colors duration-[var(--transition-fast)]',
            'hover:bg-bg-hover hover:text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue'
          )}
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" aria-hidden="true" />
          {/* Notification badge - shows unread count indicator */}
          <span
            className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-red"
            aria-label="Unread notifications"
          />
        </button>

        {/* User menu */}
        <button
          className={cn(
            'flex items-center gap-2 rounded-lg p-2 text-text-secondary',
            'transition-colors duration-[var(--transition-fast)]',
            'hover:bg-bg-hover hover:text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue'
          )}
          aria-label="User menu"
          aria-haspopup="menu"
        >
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-purple text-xs font-medium text-white">
            U
          </div>
        </button>
      </div>
    </header>
  )
}
