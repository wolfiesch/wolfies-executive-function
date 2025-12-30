import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { RightPanel } from './RightPanel'
import { CommandPalette } from './CommandPalette'
import { useUIStore, type RightPanelContent } from '@/stores/uiStore'

interface AppShellProps {
  /** Main page content */
  children: ReactNode
  /** Optional page title override for header */
  pageTitle?: string
  /** Optional breadcrumb items for header */
  breadcrumbs?: string[]
  /** Custom render function for right panel content */
  renderPanelContent?: (content: RightPanelContent) => ReactNode
}

/**
 * AppShell provides the main application layout structure.
 *
 * Layout:
 * ```
 * ┌─────────┬────────────────────────┬──────────┐
 * │ Sidebar │     Header             │          │
 * │         ├────────────────────────┤  Right   │
 * │  Nav    │                        │  Panel   │
 * │  Links  │     Main Content       │ (detail) │
 * │         │                        │          │
 * └─────────┴────────────────────────┴──────────┘
 * ```
 *
 * Features:
 * - Collapsible sidebar (state persisted to localStorage)
 * - Fixed header with command palette trigger
 * - Slide-out right panel for detail views
 * - Global command palette (Cmd+K)
 * - Responsive layout adjustments
 *
 * Design pattern: **Layout Component** - acts as a container that manages
 * the overall page structure and coordinates between layout regions.
 */
export function AppShell({
  children,
  pageTitle,
  breadcrumbs,
  renderPanelContent,
}: AppShellProps) {
  const { sidebarCollapsed } = useUIStore()

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Fixed Sidebar */}
      <Sidebar />

      {/* Fixed Header */}
      <Header title={pageTitle} breadcrumbs={breadcrumbs} />

      {/* Main content area - adjusts based on sidebar state */}
      <main
        className={cn(
          'min-h-screen pt-14',
          'transition-[padding] duration-[var(--transition-normal)] ease-in-out',
          sidebarCollapsed ? 'pl-16' : 'pl-64'
        )}
      >
        <div className="p-6">{children}</div>
      </main>

      {/* Right Panel Overlay - for task/event/note details */}
      <RightPanel renderContent={renderPanelContent} />

      {/* Global Command Palette */}
      <CommandPalette />
    </div>
  )
}
