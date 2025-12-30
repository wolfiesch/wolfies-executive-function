import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Button variant styles mapping.
 * Uses design system CSS variables for consistent theming.
 */
const buttonVariants = {
  primary:
    'bg-accent-blue text-white hover:bg-accent-blue/90 active:bg-accent-blue/80',
  secondary:
    'bg-bg-tertiary text-text-primary border border-border-default hover:bg-bg-hover active:bg-bg-active',
  ghost:
    'bg-transparent text-text-primary hover:bg-bg-hover active:bg-bg-active',
  destructive:
    'bg-accent-red text-white hover:bg-accent-red/90 active:bg-accent-red/80',
} as const

/**
 * Button size styles mapping.
 */
const buttonSizes = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
} as const

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: keyof typeof buttonVariants
  /** Size of the button */
  size?: keyof typeof buttonSizes
  /** Show loading spinner and disable interactions */
  loading?: boolean
  /** Render as child element (for composition with Link, etc.) */
  asChild?: boolean
}

/**
 * Button component with multiple variants and loading state.
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md">Click me</Button>
 * <Button variant="ghost" loading>Saving...</Button>
 * <Button asChild><Link to="/home">Go Home</Link></Button>
 * ```
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled,
      asChild = false,
      children,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : 'button'
    const isDisabled = disabled || loading

    return (
      <Comp
        className={cn(
          // Base styles
          'inline-flex items-center justify-center font-medium',
          'rounded-[var(--radius-md)] transition-colors duration-[var(--transition-fast)]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary',
          'disabled:pointer-events-none disabled:opacity-50',
          // Variant and size
          buttonVariants[variant],
          buttonSizes[size],
          className
        )}
        ref={ref}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        {...props}
      >
        {loading && (
          <Loader2
            className="animate-spin"
            size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16}
            aria-hidden="true"
          />
        )}
        {children}
      </Comp>
    )
  }
)

Button.displayName = 'Button'

export { Button, buttonVariants, buttonSizes }
