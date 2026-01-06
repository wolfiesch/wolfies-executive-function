import { NavLink, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    CheckSquare,
    Calendar,
    Target,
    type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
    id: string
    label: string
    path: string
    icon: LucideIcon
}

/**
 * Core navigation items for mobile bottom nav
 * Subset of main nav - only essential items
 */
const mobileNavItems: NavItem[] = [
    { id: 'today', label: 'Today', path: '/', icon: LayoutDashboard },
    { id: 'tasks', label: 'Tasks', path: '/tasks', icon: CheckSquare },
    { id: 'calendar', label: 'Calendar', path: '/calendar', icon: Calendar },
    { id: 'goals', label: 'Goals', path: '/goals', icon: Target },
]

/**
 * Mobile bottom navigation bar
 * 
 * Features:
 * - Fixed to bottom of screen on mobile
 * - Hidden on desktop (lg breakpoint)
 * - 5 core navigation items
 * - Safe area padding for notched phones
 */
export function MobileBottomNav() {
    const location = useLocation()

    return (
        <nav
            className={cn(
                'fixed bottom-0 left-0 right-0 z-50 lg:hidden',
                'border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]',
                'pb-safe' // Safe area for notched phones
            )}
            aria-label="Mobile navigation"
        >
            <div className="flex items-center justify-around px-2 py-2">
                {mobileNavItems.map((item) => {
                    const Icon = item.icon
                    const isActive =
                        item.path === '/'
                            ? location.pathname === '/'
                            : location.pathname.startsWith(item.path)

                    return (
                        <NavLink
                            key={item.id}
                            to={item.path}
                            className={cn(
                                'flex flex-col items-center gap-1 px-3 py-1.5 rounded-lg min-w-[64px]',
                                'transition-colors touch-manipulation',
                                isActive
                                    ? 'text-[var(--color-accent-blue)]'
                                    : 'text-[var(--color-text-tertiary)]'
                            )}
                            aria-current={isActive ? 'page' : undefined}
                        >
                            <Icon
                                className={cn(
                                    'h-6 w-6',
                                    isActive && 'text-[var(--color-accent-blue)]'
                                )}
                                aria-hidden="true"
                            />
                            <span className="text-[10px] font-medium">{item.label}</span>
                        </NavLink>
                    )
                })}
            </div>
        </nav>
    )
}

export default MobileBottomNav
