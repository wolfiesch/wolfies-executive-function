import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type {
  ClientMessage,
  ServerMessage,
  ConnectionState,
  WebSocketConfig,
  Topic,
} from '@/types/websocket'

/**
 * Default WebSocket configuration
 */
const DEFAULT_CONFIG: Required<WebSocketConfig> = {
  url:
    typeof window !== 'undefined'
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
      : 'ws://localhost:8000/ws',
  topics: ['tasks', 'calendar', 'notes', 'goals', 'dashboard'] as Topic[],
  reconnect: true,
  reconnectDelay: 1000,
  maxReconnectAttempts: 0, // infinite
  pingInterval: 30000, // 30 seconds
}

/**
 * useWebSocket - Real-time updates via WebSocket
 *
 * Handles:
 * - Automatic connection management
 * - Reconnection with exponential backoff
 * - Keep-alive pings
 * - React Query cache invalidation on events
 *
 * CS Concept: **Exponential Backoff** - When reconnecting, wait time doubles
 * each attempt (1s, 2s, 4s, 8s...) to avoid overwhelming the server.
 *
 * @example
 * ```tsx
 * function App() {
 *   const { state, isConnected } = useWebSocket({
 *     topics: ['tasks', 'calendar'],
 *   })
 *
 *   return <div>Status: {state}</div>
 * }
 * ```
 */
export function useWebSocket(config: WebSocketConfig = {}) {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const queryClient = useQueryClient()

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  const [state, setState] = useState<ConnectionState>('disconnected')
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null)
  const [error, setError] = useState<Error | null>(null)

  // ============================================================
  // MESSAGE HANDLERS
  // ============================================================

  /**
   * Handle incoming WebSocket messages.
   * Updates React Query cache based on event type.
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: ServerMessage = JSON.parse(event.data)
        setLastMessage(message)

        // Route message to appropriate handler
        switch (message.type) {
          // ──────────────────────────────────────────────────
          // TASK EVENTS
          // ──────────────────────────────────────────────────
          case 'task_created':
            // Invalidate tasks list to refetch
            queryClient.invalidateQueries({ queryKey: ['tasks'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          case 'task_updated':
          case 'task_completed':
            // Invalidate specific task and list
            queryClient.invalidateQueries({ queryKey: ['tasks'] })
            queryClient.invalidateQueries({ queryKey: ['tasks', message.data.id] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          case 'task_deleted':
            queryClient.invalidateQueries({ queryKey: ['tasks'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          // ──────────────────────────────────────────────────
          // CALENDAR EVENTS
          // ──────────────────────────────────────────────────
          case 'event_created':
            queryClient.invalidateQueries({ queryKey: ['calendar'] })
            queryClient.invalidateQueries({ queryKey: ['events'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          case 'event_updated':
            queryClient.invalidateQueries({ queryKey: ['calendar'] })
            queryClient.invalidateQueries({ queryKey: ['events'] })
            queryClient.invalidateQueries({ queryKey: ['events', message.data.id] })
            break

          case 'event_deleted':
            queryClient.invalidateQueries({ queryKey: ['calendar'] })
            queryClient.invalidateQueries({ queryKey: ['events'] })
            break

          // ──────────────────────────────────────────────────
          // NOTE EVENTS
          // ──────────────────────────────────────────────────
          case 'note_created':
            queryClient.invalidateQueries({ queryKey: ['notes'] })
            break

          case 'note_updated':
            queryClient.invalidateQueries({ queryKey: ['notes'] })
            queryClient.invalidateQueries({ queryKey: ['notes', message.data.id] })
            break

          case 'note_deleted':
            queryClient.invalidateQueries({ queryKey: ['notes'] })
            break

          // ──────────────────────────────────────────────────
          // GOAL EVENTS
          // ──────────────────────────────────────────────────
          case 'goal_progress':
            queryClient.invalidateQueries({ queryKey: ['goals'] })
            queryClient.invalidateQueries({ queryKey: ['goals', message.goalId] })
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          case 'goal_updated':
            queryClient.invalidateQueries({ queryKey: ['goals'] })
            queryClient.invalidateQueries({ queryKey: ['goals', message.data.id] })
            break

          // ──────────────────────────────────────────────────
          // DASHBOARD REFRESH
          // ──────────────────────────────────────────────────
          case 'dashboard_refresh':
            queryClient.invalidateQueries({ queryKey: ['dashboard'] })
            break

          // ──────────────────────────────────────────────────
          // SYSTEM MESSAGES
          // ──────────────────────────────────────────────────
          case 'pong':
            // Connection is healthy, nothing to do
            break

          case 'error':
            console.error('[WebSocket] Server error:', message.message)
            setError(new Error(message.message))
            break

          default:
            console.warn('[WebSocket] Unknown message type:', (message as { type: string }).type)
        }
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err)
      }
    },
    [queryClient]
  )

  // ============================================================
  // CONNECTION MANAGEMENT
  // ============================================================

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }

    setState('connecting')

    try {
      const ws = new WebSocket(cfg.url)
      wsRef.current = ws

      ws.onopen = () => {
        setState('connected')
        setError(null)
        reconnectAttemptRef.current = 0

        // Subscribe to topics
        const subscribeMsg: ClientMessage = {
          type: 'subscribe',
          topics: cfg.topics,
        }
        ws.send(JSON.stringify(subscribeMsg))

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            const pingMsg: ClientMessage = {
              type: 'ping',
              timestamp: Date.now(),
            }
            ws.send(JSON.stringify(pingMsg))
          }
        }, cfg.pingInterval)
      }

      ws.onmessage = handleMessage

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event)
        setError(new Error('WebSocket connection error'))
      }

      ws.onclose = (event) => {
        setState('disconnected')

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
        }

        // Attempt reconnection if enabled
        if (cfg.reconnect && !event.wasClean) {
          const maxAttempts = cfg.maxReconnectAttempts
          if (maxAttempts === 0 || reconnectAttemptRef.current < maxAttempts) {
            setState('reconnecting')

            // Exponential backoff: 1s, 2s, 4s, 8s... up to 30s
            const delay = Math.min(
              cfg.reconnectDelay * Math.pow(2, reconnectAttemptRef.current),
              30000
            )

            reconnectAttemptRef.current++

            console.log(
              `[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`
            )

            reconnectTimeoutRef.current = setTimeout(connect, delay)
          }
        }
      }
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err)
      setError(err instanceof Error ? err : new Error('Connection failed'))
      setState('disconnected')
    }
  }, [cfg, handleMessage])

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    setState('disconnected')
  }, [])

  /**
   * Send a message to the server
   */
  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('[WebSocket] Cannot send - not connected')
    }
  }, [])

  // ============================================================
  // LIFECYCLE
  // ============================================================

  useEffect(() => {
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount/unmount

  // ============================================================
  // RETURN VALUE
  // ============================================================

  return {
    /** Current connection state */
    state,
    /** Whether connected */
    isConnected: state === 'connected',
    /** Whether reconnecting */
    isReconnecting: state === 'reconnecting',
    /** Last received message */
    lastMessage,
    /** Last error */
    error,
    /** Manually send a message */
    send,
    /** Manually disconnect */
    disconnect,
    /** Manually reconnect */
    reconnect: connect,
  }
}

export type UseWebSocketReturn = ReturnType<typeof useWebSocket>
