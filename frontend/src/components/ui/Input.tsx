import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Optional label displayed above the input */
  label?: string
  /** Error message - displays in red below input */
  error?: string
  /** Helper text - displays in muted color below input */
  helperText?: string
  /** Left icon/element inside the input */
  leftIcon?: React.ReactNode
  /** Right icon/element inside the input */
  rightIcon?: React.ReactNode
}

/**
 * Input component with label, error state, and helper text.
 *
 * @example
 * ```tsx
 * <Input label="Email" placeholder="you@example.com" />
 * <Input label="Password" type="password" error="Password is required" />
 * <Input leftIcon={<SearchIcon />} placeholder="Search..." />
 * ```
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = 'text',
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    // Generate stable ID for accessibility if not provided
    const inputId = id || React.useId()
    const errorId = `${inputId}-error`
    const helperId = `${inputId}-helper`

    const hasError = Boolean(error)

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              'text-sm font-medium text-text-primary',
              disabled && 'opacity-50'
            )}
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
              {leftIcon}
            </div>
          )}

          <input
            type={type}
            id={inputId}
            ref={ref}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              hasError ? errorId : helperText ? helperId : undefined
            }
            className={cn(
              // Base styles
              'flex h-10 w-full rounded-[var(--radius-md)] px-3 py-2',
              'bg-bg-secondary text-text-primary placeholder:text-text-tertiary',
              'border transition-colors duration-[var(--transition-fast)]',
              // Border states
              hasError
                ? 'border-accent-red focus:border-accent-red focus:ring-accent-red/20'
                : 'border-border-default hover:border-border-strong focus:border-accent-blue',
              // Focus styles
              'focus:outline-none focus:ring-2 focus:ring-accent-blue/20',
              // Disabled styles
              'disabled:cursor-not-allowed disabled:opacity-50',
              // Icon padding
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              className
            )}
            {...props}
          />

          {rightIcon && (
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary">
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p id={errorId} className="text-sm text-accent-red" role="alert">
            {error}
          </p>
        )}

        {helperText && !error && (
          <p id={helperId} className="text-sm text-text-secondary">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export { Input }
