import * as React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { cn } from '@/lib/utils'

/**
 * Tooltip provider - wrap your app or feature area with this.
 * Controls global tooltip behavior like delay.
 */
const TooltipProvider = TooltipPrimitive.Provider

/**
 * Tooltip root - controls open state for a single tooltip.
 */
const Tooltip = TooltipPrimitive.Root

/**
 * Tooltip trigger - element that shows the tooltip on hover/focus.
 */
const TooltipTrigger = TooltipPrimitive.Trigger

/**
 * Tooltip portal - renders tooltip in a portal.
 */
const TooltipPortal = TooltipPrimitive.Portal

/**
 * Tooltip content - the actual tooltip popup.
 */
const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      'z-50 overflow-hidden rounded-[var(--radius-md)] px-3 py-1.5',
      'bg-bg-tertiary text-xs text-text-primary',
      'border border-border-default shadow-[var(--shadow-md)]',
      'animate-in fade-in-0 zoom-in-95',
      'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
      'data-[side=bottom]:slide-in-from-top-2',
      'data-[side=left]:slide-in-from-right-2',
      'data-[side=right]:slide-in-from-left-2',
      'data-[side=top]:slide-in-from-bottom-2',
      className
    )}
    {...props}
  />
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

/**
 * Tooltip arrow - optional arrow pointing to trigger.
 */
const TooltipArrow = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Arrow>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Arrow>
>(({ className, ...props }, ref) => (
  <TooltipPrimitive.Arrow
    ref={ref}
    className={cn('fill-bg-tertiary', className)}
    {...props}
  />
))
TooltipArrow.displayName = TooltipPrimitive.Arrow.displayName

/**
 * Simple tooltip component for quick usage.
 *
 * @example
 * ```tsx
 * <SimpleTooltip content="This is a tooltip">
 *   <Button>Hover me</Button>
 * </SimpleTooltip>
 * ```
 */
interface SimpleTooltipProps {
  /** Tooltip content */
  content: React.ReactNode
  /** Element that triggers the tooltip */
  children: React.ReactNode
  /** Side where tooltip appears */
  side?: 'top' | 'right' | 'bottom' | 'left'
  /** Alignment of tooltip */
  align?: 'start' | 'center' | 'end'
  /** Delay before showing (ms) */
  delayDuration?: number
  /** Show arrow pointing to trigger */
  showArrow?: boolean
}

const SimpleTooltip: React.FC<SimpleTooltipProps> = ({
  content,
  children,
  side = 'top',
  align = 'center',
  delayDuration = 200,
  showArrow = false,
}) => (
  <TooltipProvider delayDuration={delayDuration}>
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipPortal>
        <TooltipContent side={side} align={align}>
          {content}
          {showArrow && <TooltipArrow />}
        </TooltipContent>
      </TooltipPortal>
    </Tooltip>
  </TooltipProvider>
)

SimpleTooltip.displayName = 'SimpleTooltip'

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  TooltipPortal,
  TooltipArrow,
  SimpleTooltip,
}
