import { Link } from 'react-router-dom'
import { Home, ArrowLeft } from 'lucide-react'
import { AppShell } from '@/components/layout'

/**
 * NotFound - 404 error page
 *
 * Displayed when user navigates to a non-existent route.
 * Provides clear navigation back to valid pages.
 */
export function NotFound() {
  return (
    <AppShell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        {/* 404 illustration */}
        <div className="mb-8">
          <p className="text-8xl font-bold text-[var(--color-text-tertiary)]">404</p>
        </div>

        {/* Message */}
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Page not found</h1>
        <p className="mt-2 max-w-md text-[var(--color-text-secondary)]">
          Sorry, we couldn't find the page you're looking for. It might have been moved or
          doesn't exist.
        </p>

        {/* Actions */}
        <div className="mt-8 flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 rounded-lg bg-[var(--color-accent-blue)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90"
          >
            <Home className="h-4 w-4" />
            Go to Dashboard
          </Link>
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-2 rounded-lg border border-[var(--color-border-default)] px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </button>
        </div>

        {/* Help text */}
        <p className="mt-8 text-sm text-[var(--color-text-tertiary)]">
          If you think this is an error, please{' '}
          <a href="#" className="text-[var(--color-accent-blue)] hover:underline">
            contact support
          </a>
          .
        </p>
      </div>
    </AppShell>
  )
}

export default NotFound
