import * as React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    CheckSquare,
    Calendar,
    Target,
    Keyboard,
    ChevronRight,
    ChevronLeft,
    Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface OnboardingModalProps {
    open: boolean
    onComplete: () => void
}

interface Step {
    icon: React.ElementType
    title: string
    description: string
    color: string
}

const steps: Step[] = [
    {
        icon: Sparkles,
        title: 'Welcome to Life Planner',
        description:
            'Your AI-powered command center for managing tasks, events, notes, and goals — all in one place.',
        color: 'var(--color-accent-blue)',
    },
    {
        icon: CheckSquare,
        title: 'Capture Everything',
        description:
            'Quickly add tasks with natural language. Use #tags, @mentions, and due dates like "tomorrow" or "next Monday".',
        color: 'var(--color-accent-green)',
    },
    {
        icon: Calendar,
        title: 'Plan Your Time',
        description:
            'Drag events on the calendar, block focus time, and see your day at a glance. Never miss a deadline.',
        color: 'var(--color-accent-purple)',
    },
    {
        icon: Keyboard,
        title: 'Keyboard First',
        description:
            'Power users love shortcuts. Press ⌘K for command palette, G+T for tasks, or ? to see all shortcuts.',
        color: 'var(--color-accent-orange)',
    },
]

/**
 * Onboarding welcome modal - 4-step wizard for first-time users
 * 
 * Features:
 * - Step-by-step introduction to key features
 * - Animated transitions between steps
 * - Progress indicator
 * - Skip and navigation controls
 */
export function OnboardingModal({ open, onComplete }: OnboardingModalProps) {
    const [currentStep, setCurrentStep] = React.useState(0)

    const isLastStep = currentStep === steps.length - 1
    const step = steps[currentStep]
    const Icon = step.icon

    const handleNext = () => {
        if (isLastStep) {
            onComplete()
        } else {
            setCurrentStep((prev) => prev + 1)
        }
    }

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep((prev) => prev - 1)
        }
    }

    const handleSkip = () => {
        onComplete()
    }

    return (
        <AnimatePresence>
            {open && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
                        aria-hidden="true"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-8 shadow-2xl"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="onboarding-title"
                    >
                        {/* Skip button */}
                        <button
                            onClick={handleSkip}
                            className="absolute right-4 top-4 text-sm text-[var(--color-text-tertiary)] transition-colors hover:text-[var(--color-text-secondary)]"
                        >
                            Skip
                        </button>

                        {/* Step content */}
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={currentStep}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ duration: 0.2 }}
                                className="flex flex-col items-center text-center"
                            >
                                {/* Icon */}
                                <div
                                    className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl"
                                    style={{ backgroundColor: `${step.color}20` }}
                                >
                                    <Icon
                                        className="h-10 w-10"
                                        style={{ color: step.color }}
                                        aria-hidden="true"
                                    />
                                </div>

                                {/* Title */}
                                <h2
                                    id="onboarding-title"
                                    className="mb-3 text-xl font-semibold text-[var(--color-text-primary)]"
                                >
                                    {step.title}
                                </h2>

                                {/* Description */}
                                <p className="mb-8 text-[var(--color-text-secondary)]">
                                    {step.description}
                                </p>
                            </motion.div>
                        </AnimatePresence>

                        {/* Progress dots */}
                        <div className="mb-6 flex justify-center gap-2">
                            {steps.map((_, index) => (
                                <button
                                    key={index}
                                    onClick={() => setCurrentStep(index)}
                                    className={cn(
                                        'h-2 rounded-full transition-all',
                                        index === currentStep
                                            ? 'w-6 bg-[var(--color-accent-blue)]'
                                            : 'w-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-text-tertiary)]'
                                    )}
                                    aria-label={`Go to step ${index + 1}`}
                                />
                            ))}
                        </div>

                        {/* Navigation buttons */}
                        <div className="flex items-center justify-between">
                            <button
                                onClick={handlePrev}
                                disabled={currentStep === 0}
                                className={cn(
                                    'flex items-center gap-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                                    currentStep === 0
                                        ? 'cursor-not-allowed text-[var(--color-text-tertiary)]'
                                        : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]'
                                )}
                            >
                                <ChevronLeft className="h-4 w-4" />
                                Back
                            </button>

                            <button
                                onClick={handleNext}
                                className="flex items-center gap-1 rounded-lg bg-[var(--color-accent-blue)] px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-accent-blue)]/90"
                            >
                                {isLastStep ? "Let's Go!" : 'Next'}
                                {!isLastStep && <ChevronRight className="h-4 w-4" />}
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}

export default OnboardingModal
