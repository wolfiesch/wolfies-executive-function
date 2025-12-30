import { Wifi, WifiOff, Loader2 } from 'lucide-react'
import { useWebSocketContext } from '@/providers/WebSocketProvider'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip'
import { cn } from '@/lib/utils'

/**
 * ConnectionStatus - Shows WebSocket connection state
 *
 * Use in the header or sidebar to give users visibility
 * into real-time sync status.
 *
 * States:
 * - Connected (green): Real-time sync is active
 * - Reconnecting (yellow): Attempting to reconnect
 * - Disconnected (gray): Offline, changes sync when reconnected
 */
export function ConnectionStatus() {
  const { state, isConnected, isReconnecting } = useWebSocketContext()

  if (isConnected) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'flex items-center gap-1.5',
                'text-accent-green',
                'cursor-default'
              )}
            >
              <Wifi className="h-4 w-4" />
              <span className="hidden text-xs sm:inline">Live</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>Real-time sync active</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  if (isReconnecting) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'flex items-center gap-1.5',
                'text-accent-yellow',
                'cursor-default'
              )}
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="hidden text-xs sm:inline">Syncing</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>Reconnecting...</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex items-center gap-1.5',
              'text-text-tertiary',
              'cursor-default'
            )}
          >
            <WifiOff className="h-4 w-4" />
            <span className="hidden text-xs sm:inline">Offline</span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          Offline - changes will sync when reconnected ({state})
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
