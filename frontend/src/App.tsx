import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { router } from '@/routes'

/**
 * QueryClient configuration for React Query.
 *
 * Settings:
 * - staleTime: 5 minutes - data is considered fresh for 5 minutes
 * - refetchOnWindowFocus: false - don't refetch when window regains focus
 * - retry: 1 - retry failed requests once
 *
 * CS concept: **Stale-While-Revalidate** - React Query implements this pattern
 * where stale data is shown immediately while fresh data is fetched in background.
 * This provides instant feedback while keeping data up-to-date.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

/**
 * Root App component.
 *
 * Provides:
 * - QueryClientProvider: React Query for data fetching and caching
 * - RouterProvider: React Router for navigation
 * - Toaster: Toast notifications for user feedback
 *
 * Design pattern: **Provider Composition** - wrapping the app with multiple
 * providers to inject capabilities (routing, data fetching, notifications)
 * throughout the component tree via React Context.
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          // Styling to match our dark theme
          style: {
            background: 'var(--color-bg-tertiary)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border-subtle)',
          },
          // Success toast styling
          success: {
            iconTheme: {
              primary: 'var(--color-accent-green)',
              secondary: 'var(--color-bg-tertiary)',
            },
          },
          // Error toast styling
          error: {
            iconTheme: {
              primary: 'var(--color-accent-red)',
              secondary: 'var(--color-bg-tertiary)',
            },
          },
        }}
      />
    </QueryClientProvider>
  )
}

export default App
