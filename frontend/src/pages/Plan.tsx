import { motion } from 'framer-motion'
import {
  Compass,
  Clock,
  CalendarRange,
  Layers,
  Flag,
  Briefcase,
  HeartPulse,
  Wallet,
  Users,
  GraduationCap,
  Palette,
  Home,
  Sun,
  MoonStar,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'
import { AppShell } from '@/components/layout'

const revealContainer = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      staggerChildren: 0.08,
      duration: 0.4,
      ease: 'easeOut',
    },
  },
}

const revealItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
}

const nowFocus = [
  {
    title: 'Today Focus',
    icon: Clock,
    tag: 'Now',
    items: [
      'Protect 90 minutes of deep work for the main deliverable.',
      'Move the body for 30 minutes and get daylight early.',
      'Clear inboxes and capture loose ends in one sweep.',
      'Reach out to one important person you want to keep close.',
    ],
  },
  {
    title: 'This Week',
    icon: CalendarRange,
    tag: '7 days',
    items: [
      'Ship a working milestone to real users or stakeholders.',
      'Schedule three workouts and one long recovery block.',
      'Close the top three admin tasks that cause drag.',
      'Set a hard stop for context switching after 6pm.',
    ],
  },
  {
    title: 'This Month',
    icon: Flag,
    tag: '30 days',
    items: [
      'Deliver a complete MVP with feedback loops in place.',
      'Hit 12 training sessions and one full rest weekend.',
      'Review budget categories and automate one bill.',
      'Finish one learning sprint with notes and artifacts.',
    ],
  },
]

const lifeAreas = [
  {
    title: 'Personal',
    icon: Compass,
    focus: 'Identity, values, and the way you spend attention.',
    next: 'Write a one-page narrative for the next 90 days.',
    metric: 'Weekly reflection complete by Sunday.',
  },
  {
    title: 'Professional',
    icon: Briefcase,
    focus: 'Build leverage through shipping and relationships.',
    next: 'Define the next visible win and assign owners.',
    metric: 'One shipped milestone per week.',
  },
  {
    title: 'Health',
    icon: HeartPulse,
    focus: 'Energy, sleep, and movement.',
    next: 'Lock a default training schedule and bedtime.',
    metric: '7h sleep average, 3 workouts.',
  },
  {
    title: 'Finance',
    icon: Wallet,
    focus: 'Clarity and control of monthly cash flow.',
    next: 'Review subscriptions and cut one.',
    metric: 'Monthly spend tracked weekly.',
  },
  {
    title: 'Relationships',
    icon: Users,
    focus: 'Keep the inner circle warm and present.',
    next: 'Plan one meaningful connection per week.',
    metric: '4 quality touches per month.',
  },
  {
    title: 'Learning',
    icon: GraduationCap,
    focus: 'Skill growth tied to current priorities.',
    next: 'Schedule two focused learning blocks.',
    metric: '1 publishable note per week.',
  },
  {
    title: 'Creative',
    icon: Palette,
    focus: 'Exploration and personal expression.',
    next: 'Capture ideas and pick one to explore.',
    metric: 'One creative session each weekend.',
  },
  {
    title: 'Home',
    icon: Home,
    focus: 'A calm environment that supports focus.',
    next: 'Define the top two maintenance resets.',
    metric: '15-minute daily reset.',
  },
]

const initiatives = {
  active: [
    'Core product release: ship v1 to real users',
    'Personal operating system: automate capture and review',
    'Health baseline: 30-day consistency streak',
  ],
  next: [
    'Professional visibility: publish a case study',
    'Finance cleanup: consolidate accounts and budgets',
    'Home reset: simplify one cluttered zone',
  ],
  someday: [
    'Plan a long-form creative project',
    'Design a travel or retreat window',
    'Build a personal knowledge base archive',
  ],
}

const systems = [
  {
    title: 'Morning Launch',
    icon: Sun,
    items: [
      'Hydrate, daylight, and a 10-minute plan review.',
      'Choose one critical task before opening messages.',
      'Start the first focus block inside 60 minutes.',
    ],
  },
  {
    title: 'Evening Shutdown',
    icon: MoonStar,
    items: [
      'Capture open loops and clear the desk.',
      'Write the top three for tomorrow.',
      'Power down at a consistent time.',
    ],
  },
  {
    title: 'Weekly Review',
    icon: RefreshCw,
    items: [
      'Score wins and drop anything not aligned.',
      'Update priorities for each life area.',
      'Schedule the next seven days.',
    ],
  },
]

const guardrails = [
  'Only two major priorities per day.',
  'No meetings inside the first focus block.',
  'If a task is not scheduled, it does not exist.',
  'Protect recovery like a project milestone.',
]

export function Plan() {
  return (
    <AppShell>
      <motion.div
        className="mx-auto max-w-6xl space-y-8"
        variants={revealContainer}
        initial="hidden"
        animate="show"
      >
        <motion.section
          variants={revealItem}
          className="relative overflow-hidden rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-6"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(29,155,240,0.18),_transparent_55%)]" />
          <div className="relative z-10 flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-[var(--color-accent-blue)]/15 p-2">
                  <Compass className="h-6 w-6 text-[var(--color-accent-blue)]" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-text-tertiary)]">
                    Master Plan
                  </p>
                  <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">
                    Life Command Center
                  </h1>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-[var(--color-text-secondary)]">
                <span className="rounded-full border border-[var(--color-border-default)] px-3 py-1">
                  Cycle: Next 12 weeks
                </span>
                <span className="rounded-full border border-[var(--color-border-default)] px-3 py-1">
                  Review: Every Sunday
                </span>
              </div>
            </div>
            <p className="max-w-2xl text-sm text-[var(--color-text-secondary)]">
              This is your unified plan for the present moment. Use it to align daily
              execution with bigger priorities, balance life areas, and keep momentum
              without losing clarity.
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Focus blocks', value: '2 per day' },
                { label: 'Recovery blocks', value: '1 per day' },
                { label: 'Review cadence', value: 'Weekly' },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-tertiary)] px-4 py-3"
                >
                  <p className="text-xs text-[var(--color-text-tertiary)]">{stat.label}</p>
                  <p className="text-lg font-semibold text-[var(--color-text-primary)]">
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        <motion.section variants={revealItem} className="space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-[var(--color-accent-blue)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              Now, Next, Later
            </h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {nowFocus.map((block) => (
              <div
                key={block.title}
                className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5"
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <block.icon className="h-5 w-5 text-[var(--color-accent-blue)]" />
                    <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                      {block.title}
                    </h3>
                  </div>
                  <span className="rounded-full bg-[var(--color-bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]">
                    {block.tag}
                  </span>
                </div>
                <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
                  {block.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--color-accent-blue)]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section variants={revealItem} className="space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-[var(--color-accent-green)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              Focus Guardrails
            </h2>
          </div>
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5">
            <ul className="grid gap-3 text-sm text-[var(--color-text-secondary)] sm:grid-cols-2">
              {guardrails.map((rule) => (
                <li key={rule} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--color-accent-green)]" />
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          </div>
        </motion.section>

        <motion.section variants={revealItem} className="space-y-4">
          <div className="flex items-center gap-2">
            <Compass className="h-5 w-5 text-[var(--color-accent-purple)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              Life Areas
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {lifeAreas.map((area) => (
              <div
                key={area.title}
                className="flex h-full flex-col justify-between rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-4"
              >
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <area.icon className="h-5 w-5 text-[var(--color-accent-purple)]" />
                    <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                      {area.title}
                    </h3>
                  </div>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    {area.focus}
                  </p>
                </div>
                <div className="mt-4 space-y-2 text-xs text-[var(--color-text-tertiary)]">
                  <p>
                    <span className="text-[var(--color-text-secondary)]">Next: </span>
                    {area.next}
                  </p>
                  <p>
                    <span className="text-[var(--color-text-secondary)]">Metric: </span>
                    {area.metric}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section variants={revealItem} className="space-y-4">
          <div className="flex items-center gap-2">
            <Flag className="h-5 w-5 text-[var(--color-accent-orange)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              Initiatives Pipeline
            </h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {[
              { title: 'Active', items: initiatives.active },
              { title: 'Next Up', items: initiatives.next },
              { title: 'Someday', items: initiatives.someday },
            ].map((column) => (
              <div
                key={column.title}
                className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5"
              >
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {column.title}
                </h3>
                <ul className="mt-3 space-y-3 text-sm text-[var(--color-text-secondary)]">
                  {column.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--color-accent-orange)]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section variants={revealItem} className="space-y-4">
          <div className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-[var(--color-accent-blue)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              Systems and Reviews
            </h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {systems.map((system) => (
              <div
                key={system.title}
                className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)] p-5"
              >
                <div className="mb-3 flex items-center gap-2">
                  <system.icon className="h-5 w-5 text-[var(--color-accent-blue)]" />
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
                    {system.title}
                  </h3>
                </div>
                <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
                  {system.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--color-accent-blue)]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </motion.section>
      </motion.div>
    </AppShell>
  )
}

export default Plan
