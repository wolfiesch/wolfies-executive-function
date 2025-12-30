import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * UI state store for managing layout and visual state.
 * Uses Zustand for lightweight, efficient state management.
 *
 * Key patterns:
 * - Sidebar collapsed state persisted to localStorage
 * - Right panel state managed in memory (resets on refresh)
 * - Command palette state for global search/actions
 */

export interface RightPanelContent {
  type: 'task' | 'event' | 'note' | 'goal'
  id: string
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void

  // Right Panel
  rightPanelOpen: boolean
  rightPanelContent: RightPanelContent | null
  openRightPanel: (content: RightPanelContent) => void
  closeRightPanel: () => void

  // Command Palette
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
  toggleCommandPalette: () => void

  // Mobile menu (for responsive)
  mobileMenuOpen: boolean
  setMobileMenuOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar - persisted
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),

      // Right Panel - not persisted
      rightPanelOpen: false,
      rightPanelContent: null,
      openRightPanel: (content) =>
        set({ rightPanelOpen: true, rightPanelContent: content }),
      closeRightPanel: () =>
        set({ rightPanelOpen: false, rightPanelContent: null }),

      // Command Palette - not persisted
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      toggleCommandPalette: () =>
        set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

      // Mobile menu - not persisted
      mobileMenuOpen: false,
      setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
    }),
    {
      name: 'life-planner-ui',
      // Only persist sidebar state
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)
