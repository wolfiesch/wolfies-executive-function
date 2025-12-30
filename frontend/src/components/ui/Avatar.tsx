import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Avatar size styles.
 */
const avatarSizes = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg',
} as const

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Image source URL */
  src?: string | null
  /** Alt text for the image */
  alt?: string
  /** User's name for generating initials fallback */
  name?: string
  /** Size of the avatar */
  size?: keyof typeof avatarSizes
  /** Custom fallback element (overrides initials) */
  fallback?: React.ReactNode
}

/**
 * Get initials from a name.
 * "John Doe" -> "JD"
 * "Alice" -> "A"
 */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase()
  }
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

/**
 * Generate a consistent background color from a string.
 * Uses a hash to pick from a predefined palette.
 */
function getColorFromString(str: string): string {
  const colors = [
    'bg-accent-blue',
    'bg-accent-green',
    'bg-accent-yellow',
    'bg-accent-purple',
    'bg-accent-orange',
    'bg-accent-red',
  ]

  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

/**
 * Avatar component with image support and initials fallback.
 *
 * @example
 * ```tsx
 * // With image
 * <Avatar src="/user.jpg" alt="John Doe" />
 *
 * // With initials fallback
 * <Avatar name="John Doe" size="lg" />
 *
 * // Custom fallback
 * <Avatar fallback={<UserIcon />} />
 * ```
 */
const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  (
    { className, src, alt, name, size = 'md', fallback, ...props },
    ref
  ) => {
    const [imageError, setImageError] = React.useState(false)

    // Reset error state when src changes
    React.useEffect(() => {
      setImageError(false)
    }, [src])

    const showImage = src && !imageError
    const initials = name ? getInitials(name) : null
    const bgColor = name ? getColorFromString(name) : 'bg-bg-tertiary'

    return (
      <div
        ref={ref}
        className={cn(
          'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full',
          'font-medium text-white',
          avatarSizes[size],
          !showImage && bgColor,
          className
        )}
        {...props}
      >
        {showImage ? (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className="h-full w-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : fallback ? (
          fallback
        ) : initials ? (
          <span aria-hidden="true">{initials}</span>
        ) : (
          // Default fallback: generic user icon
          <svg
            className="h-1/2 w-1/2"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
              clipRule="evenodd"
            />
          </svg>
        )}

        {/* Screenreader text */}
        {(alt || name) && (
          <span className="sr-only">{alt || name}</span>
        )}
      </div>
    )
  }
)

Avatar.displayName = 'Avatar'

/**
 * Avatar group - displays multiple avatars with overlap.
 */
export interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Maximum number of avatars to show */
  max?: number
  /** Size of avatars */
  size?: keyof typeof avatarSizes
  children: React.ReactNode
}

const AvatarGroup = React.forwardRef<HTMLDivElement, AvatarGroupProps>(
  ({ className, max = 4, size = 'md', children, ...props }, ref) => {
    const childArray = React.Children.toArray(children)
    const visibleChildren = childArray.slice(0, max)
    const remainingCount = childArray.length - max

    return (
      <div
        ref={ref}
        className={cn('flex -space-x-2', className)}
        {...props}
      >
        {visibleChildren.map((child, index) => (
          <div
            key={index}
            className="ring-2 ring-bg-primary rounded-full"
          >
            {React.isValidElement<AvatarProps>(child)
              ? React.cloneElement(child, { size })
              : child}
          </div>
        ))}

        {remainingCount > 0 && (
          <div
            className={cn(
              'inline-flex items-center justify-center rounded-full',
              'bg-bg-tertiary font-medium text-text-secondary ring-2 ring-bg-primary',
              avatarSizes[size]
            )}
          >
            +{remainingCount}
          </div>
        )}
      </div>
    )
  }
)

AvatarGroup.displayName = 'AvatarGroup'

export { Avatar, AvatarGroup, avatarSizes, getInitials, getColorFromString }
