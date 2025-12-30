import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/globals.css'
import App from './App'

/**
 * Application entry point.
 *
 * Renders the App component wrapped in StrictMode.
 *
 * StrictMode helps identify potential problems by:
 * - Detecting unsafe lifecycle methods
 * - Warning about deprecated API usage
 * - Identifying side effects in render phase (by double-invoking)
 *
 * Note: In development, StrictMode causes components to render twice
 * to help detect side effects. This is normal and doesn't happen in production.
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
