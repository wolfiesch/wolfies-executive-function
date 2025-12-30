import { createContext, useContext, type ReactNode } from 'react'
import { useWebSocket, type UseWebSocketReturn } from '@/hooks/useWebSocket'
import type { Topic } from '@/types/websocket'

type WebSocketContextType = UseWebSocketReturn

const WebSocketContext = createContext<WebSocketContextType | null>(null)

interface WebSocketProviderProps {
  children: ReactNode
  /** Topics to subscribe to */
  topics?: Topic[]
}

/**
 * WebSocketProvider - Provides WebSocket connection to the app
 *
 * Wrap your app with this provider to enable real-time updates.
 *
 * CS Concept: **React Context** - Allows data to be passed through the
 * component tree without prop drilling. The WebSocket connection state
 * becomes available to any component that calls useWebSocketContext().
 *
 * @example
 * ```tsx
 * <WebSocketProvider topics={['tasks', 'calendar']}>
 *   <App />
 * </WebSocketProvider>
 * ```
 */
export function WebSocketProvider({ children, topics }: WebSocketProviderProps) {
  const ws = useWebSocket({ topics })

  return <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>
}

/**
 * useWebSocketContext - Access WebSocket connection from any component
 *
 * @throws Error if used outside of WebSocketProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isConnected, lastMessage } = useWebSocketContext()
 *   return <div>{isConnected ? 'Online' : 'Offline'}</div>
 * }
 * ```
 */
export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}
