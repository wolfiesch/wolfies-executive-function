/**
 * Layout components for the Life Planner application.
 *
 * These components provide the main application structure:
 * - AppShell: Main layout wrapper with all regions
 * - Sidebar: Navigation sidebar (collapsible)
 * - Header: Top bar with page title and actions
 * - RightPanel: Slide-out detail panel
 * - CommandPalette: Global search and quick actions (Cmd+K)
 * - KeyboardProvider: Global keyboard shortcuts and help modal
 * - MobileBottomNav: Mobile bottom navigation bar
 */

export { AppShell } from "./AppShell";
export { Sidebar } from "./Sidebar";
export { Header } from "./Header";
export { RightPanel } from "./RightPanel";
export { CommandPalette } from "./CommandPalette";
export { KeyboardProvider, useKeyboardContext } from "./KeyboardProvider";
export { MobileBottomNav } from "./MobileBottomNav";
