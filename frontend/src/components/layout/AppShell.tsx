import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { RightPanel } from './RightPanel'
import { KeyboardProvider } from './KeyboardProvider'
import { MobileBottomNav } from './MobileBottomNav'
import { useUIStore, type RightPanelContent } from '@/stores/uiStore'

// ============================================================
// LAZY-LOADED COMMAND PALETTE
// ============================================================
// CommandPalette imports cmdk and framer-motion (together ~95KB).
// By lazy loading, we defer this chunk until the user presses ⌘K.
//
// CS Concept: **Deferred Loading** - Load expensive components only
// when needed, reducing initial page load time.
// ============================================================
const CommandPalette = lazy(() => import('./CommandPalette'))

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
 * - Global command palette (Cmd+K) - lazy loaded
 * - Responsive layout adjustments
 *
 * Design pattern: **Layout Component** - acts as a container that manages
 * the overall page structure and coordinates between layout regions.
 *
 * Performance: CommandPalette is lazy-loaded to reduce initial bundle size.
 * The chunk is only downloaded when the user first opens the palette (⌘K).
 */
export function AppShell({
  children,
  pageTitle,
  breadcrumbs,
  renderPanelContent,
}: AppShellProps) {
  const { sidebarCollapsed, commandPaletteOpen } = useUIStore()

  // ============================================================
  // LAZY COMMAND PALETTE MOUNTING
  // ============================================================
  // Only mount CommandPalette after it's been opened once.
  // This prevents loading the chunk (~95KB) until actually needed.
  //
  // Pattern: **Mount on First Use** - component stays mounted after
  // first open for instant subsequent opens (no re-load delay).
  // ============================================================
  const [hasOpenedPalette, setHasOpenedPalette] = useState(false)

  useEffect(() => {
    if (commandPaletteOpen && !hasOpenedPalette) {
      setHasOpenedPalette(true)
    }
  }, [commandPaletteOpen, hasOpenedPalette])

  return (
    <KeyboardProvider>
      <div className="min-h-screen bg-bg-primary">
        {/* Fixed Sidebar - hidden on mobile */}
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        {/* Fixed Header */}
        <Header title={pageTitle} breadcrumbs={breadcrumbs} />

        {/* Main content area - adjusts based on sidebar state */}
        <main
          className={cn(
            'min-h-screen pt-14 pb-16 lg:pb-0',
            'transition-[padding] duration-[var(--transition-normal)] ease-in-out',
            sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
          )}
        >
          <div className="p-4 lg:p-6">{children}</div>
        </main>

        {/* Right Panel Overlay - for task/event/note details */}
        <RightPanel renderContent={renderPanelContent} />

        {/* Mobile Bottom Navigation - visible only on mobile */}
        <MobileBottomNav />

        {/*
          Global Command Palette - Lazy Loaded

          Only loads the CommandPalette chunk after the first ⌘K press.
          Suspense fallback is null since the palette has its own animations.
          After first load, stays mounted for instant subsequent opens.
        */}
        {hasOpenedPalette && (
          <Suspense fallback={null}>
            <CommandPalette />
          </Suspense>
        )}
      </div>
    </KeyboardProvider>
  )
}
