/**
 * UI Component Library
 *
 * Base UI components for the Life Planner React frontend.
 * Built with Radix UI primitives, Tailwind CSS v4, and the Obsidian Command Center design system.
 *
 * @example
 * ```tsx
 * import { Button, Input, Card, Badge } from '@/components/ui'
 *
 * <Card>
 *   <CardHeader>
 *     <CardTitle>New Task</CardTitle>
 *   </CardHeader>
 *   <CardContent>
 *     <Input label="Task name" />
 *   </CardContent>
 *   <CardFooter>
 *     <Button variant="primary">Create</Button>
 *   </CardFooter>
 * </Card>
 * ```
 */

// Button
export { Button, buttonVariants, buttonSizes } from './Button'
export type { ButtonProps } from './Button'

// Input
export { Input } from './Input'
export type { InputProps } from './Input'

// Card
export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './Card'

// Badge
export {
  Badge,
  badgeVariants,
  badgeSizes,
  priorityVariants,
  statusVariants,
} from './Badge'
export type { BadgeProps } from './Badge'

// Dialog
export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './Dialog'

// Dropdown Menu
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
} from './Dropdown'

// Skeleton
export { Skeleton, SkeletonText, SkeletonAvatar, SkeletonCard } from './Skeleton'
export type { SkeletonProps } from './Skeleton'

// Avatar
export {
  Avatar,
  AvatarGroup,
  avatarSizes,
  getInitials,
  getColorFromString,
} from './Avatar'
export type { AvatarProps, AvatarGroupProps } from './Avatar'

// Tooltip
export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  TooltipPortal,
  TooltipArrow,
  SimpleTooltip,
} from './Tooltip'
