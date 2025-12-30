/**
 * Mock data for development
 *
 * Provides realistic sample data for all entities while the backend API
 * is still being developed. This allows frontend development to proceed
 * independently.
 *
 * [*TO-DO*] - Remove mock data and switch to real API when backend is ready
 */

import type {
  Task,
  CalendarEvent,
  Note,
  Goal,
  Project,
  DashboardData,
  DashboardStats,
  GoalSummary,
  ActivityItem,
  ProgressLog,
  ParsedInput,
} from '@/types/models'
import type { Priority, TaskStatus, GoalStatus, NoteType, EventType } from '@/lib/constants'

// Helper to generate ISO date strings
const now = new Date()
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000)
const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)
const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)

function toISOString(date: Date): string {
  return date.toISOString()
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

// ============================================================================
// Projects
// ============================================================================

export const mockProjects: Project[] = [
  {
    id: 'proj-1',
    name: 'Life Planner App',
    description: 'Building a comprehensive AI-powered life planning system',
    status: 'active',
    life_area: 'professional',
    color: '#3B82F6',
    icon: 'code',
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'proj-2',
    name: 'Health Goals 2025',
    description: 'Track and achieve health goals for the year',
    status: 'active',
    life_area: 'health',
    color: '#10B981',
    icon: 'heart',
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'proj-3',
    name: 'Home Renovation',
    description: 'Kitchen and bathroom updates',
    status: 'active',
    life_area: 'home',
    color: '#F59E0B',
    icon: 'home',
    due_date: toISOString(nextWeek),
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
]

// ============================================================================
// Tasks
// ============================================================================

export const mockTasks: Task[] = [
  // Today's high priority tasks
  {
    id: 'task-1',
    title: 'Review API design for Life Planner',
    description: 'Finalize the REST API endpoints and data models',
    status: 'in_progress',
    priority: 5,
    due_date: toISOString(today),
    due_time: '14:00',
    estimated_minutes: 60,
    life_area: 'professional',
    project_id: 'proj-1',
    tags: ['api', 'planning'],
    created_at: toISOString(yesterday),
    updated_at: toISOString(now),
  },
  {
    id: 'task-2',
    title: 'Set up React Query hooks',
    description: 'Create custom hooks for data fetching with optimistic updates',
    status: 'todo',
    priority: 4,
    due_date: toISOString(today),
    estimated_minutes: 90,
    life_area: 'professional',
    project_id: 'proj-1',
    tags: ['react', 'frontend'],
    created_at: toISOString(yesterday),
    updated_at: toISOString(now),
  },
  {
    id: 'task-3',
    title: 'Morning workout - 30 min cardio',
    status: 'done',
    priority: 3,
    due_date: toISOString(today),
    due_time: '07:00',
    estimated_minutes: 30,
    actual_minutes: 35,
    life_area: 'health',
    project_id: 'proj-2',
    tags: ['exercise'],
    completed_at: toISOString(new Date(today.getTime() + 7 * 60 * 60 * 1000)),
    created_at: toISOString(yesterday),
    updated_at: toISOString(now),
  },
  // Tomorrow's tasks
  {
    id: 'task-4',
    title: 'Call contractor about kitchen cabinets',
    description: 'Discuss timeline and material options',
    status: 'todo',
    priority: 4,
    due_date: toISOString(tomorrow),
    due_time: '10:00',
    estimated_minutes: 30,
    life_area: 'home',
    project_id: 'proj-3',
    tags: ['renovation', 'call'],
    created_at: toISOString(now),
    updated_at: toISOString(now),
  },
  {
    id: 'task-5',
    title: 'Prepare weekly team meeting agenda',
    status: 'todo',
    priority: 3,
    due_date: toISOString(tomorrow),
    estimated_minutes: 20,
    life_area: 'professional',
    tags: ['meeting', 'planning'],
    created_at: toISOString(now),
    updated_at: toISOString(now),
  },
  // Waiting tasks
  {
    id: 'task-6',
    title: 'Waiting for design review feedback',
    description: 'Sent to Sarah for review on Monday',
    status: 'waiting',
    priority: 3,
    life_area: 'professional',
    project_id: 'proj-1',
    tags: ['design', 'review'],
    waiting_for: 'Sarah',
    waiting_since: toISOString(lastWeek),
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  // Overdue task
  {
    id: 'task-7',
    title: 'Schedule dentist appointment',
    status: 'todo',
    priority: 2,
    due_date: toISOString(yesterday),
    life_area: 'health',
    tags: ['health', 'appointment'],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  // No due date tasks
  {
    id: 'task-8',
    title: 'Read "Atomic Habits" - Chapter 3',
    description: 'Focus on habit stacking concepts',
    status: 'todo',
    priority: 2,
    estimated_minutes: 45,
    life_area: 'learning',
    tags: ['reading', 'self-improvement'],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  // Subtask example
  {
    id: 'task-9',
    title: 'Set up database schema',
    description: 'Create SQLite tables for all entities',
    status: 'done',
    priority: 4,
    life_area: 'professional',
    project_id: 'proj-1',
    parent_id: 'task-1',
    tags: ['database'],
    completed_at: toISOString(yesterday),
    created_at: toISOString(lastWeek),
    updated_at: toISOString(yesterday),
  },
]

// ============================================================================
// Calendar Events
// ============================================================================

export const mockEvents: CalendarEvent[] = [
  {
    id: 'event-1',
    title: 'Team Standup',
    description: 'Daily sync with the development team',
    start_time: toISOString(new Date(today.getTime() + 9 * 60 * 60 * 1000)),
    end_time: toISOString(new Date(today.getTime() + 9.5 * 60 * 60 * 1000)),
    all_day: false,
    event_type: 'meeting',
    color: '#3B82F6',
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'event-2',
    title: 'Deep Work: API Development',
    description: 'Focus time for Life Planner backend',
    start_time: toISOString(new Date(today.getTime() + 10 * 60 * 60 * 1000)),
    end_time: toISOString(new Date(today.getTime() + 12 * 60 * 60 * 1000)),
    all_day: false,
    event_type: 'focus',
    color: '#10B981',
    created_at: toISOString(now),
    updated_at: toISOString(now),
  },
  {
    id: 'event-3',
    title: 'Lunch with Alex',
    description: 'Catching up at the new Italian place',
    start_time: toISOString(new Date(today.getTime() + 12.5 * 60 * 60 * 1000)),
    end_time: toISOString(new Date(today.getTime() + 13.5 * 60 * 60 * 1000)),
    all_day: false,
    location: 'Bella Italia, Downtown',
    event_type: 'personal',
    color: '#F59E0B',
    created_at: toISOString(now),
    updated_at: toISOString(now),
  },
  {
    id: 'event-4',
    title: 'Project deadline: MVP release',
    start_time: toISOString(nextWeek),
    end_time: toISOString(nextWeek),
    all_day: true,
    event_type: 'deadline',
    color: '#EF4444',
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  // Tomorrow's events
  {
    id: 'event-5',
    title: 'Design Review Meeting',
    description: 'Review new UI mockups with the team',
    start_time: toISOString(new Date(tomorrow.getTime() + 14 * 60 * 60 * 1000)),
    end_time: toISOString(new Date(tomorrow.getTime() + 15 * 60 * 60 * 1000)),
    all_day: false,
    location: 'Conference Room A',
    event_type: 'meeting',
    color: '#8B5CF6',
    created_at: toISOString(now),
    updated_at: toISOString(now),
  },
]

// ============================================================================
// Notes
// ============================================================================

export const mockNotes: Note[] = [
  {
    id: 'note-1',
    title: 'Life Planner Architecture',
    content: `# Life Planner Architecture

## Overview
The system follows a sub-agent architecture pattern with specialized agents for different domains.

## Key Components
- **Master Agent**: Routes requests to specialized agents
- **Task Agent**: Task management and scheduling
- **Calendar Agent**: Event management and time blocking
- **Notes Agent**: Knowledge management and retrieval

## Data Flow
1. User input received
2. NLP parsing extracts intent
3. Master agent routes to appropriate sub-agent
4. Sub-agent processes and returns response

[[Weekly Review Template]]
[[Goal Setting Framework]]`,
    note_type: 'reference',
    life_area: 'professional',
    tags: ['architecture', 'planning', 'life-planner'],
    is_pinned: true,
    word_count: 78,
    backlinks: ['note-2'],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'note-2',
    title: 'Weekly Review Template',
    content: `# Weekly Review Template

## Review Last Week
- [ ] Review completed tasks
- [ ] Check goal progress
- [ ] Identify blockers and learnings

## Plan Next Week
- [ ] Set top 3 priorities
- [ ] Schedule time blocks
- [ ] Update goal milestones

## Reflection Questions
1. What went well?
2. What could be improved?
3. What am I grateful for?

Related: [[Life Planner Architecture]]`,
    note_type: 'reference',
    life_area: 'personal',
    tags: ['template', 'review', 'planning'],
    is_pinned: true,
    word_count: 62,
    backlinks: ['note-1'],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'note-3',
    title: 'Daily Journal - Today',
    content: `# Daily Journal

## Morning Thoughts
Starting the day with a clear focus on API development. Energy levels are good after the workout.

## Key Tasks for Today
1. Finish React Query hooks setup
2. Review API design document
3. Catch up with Alex at lunch

## Evening Reflection
(To be filled)`,
    note_type: 'journal',
    life_area: 'personal',
    tags: ['journal', 'daily'],
    is_pinned: false,
    word_count: 48,
    backlinks: [],
    created_at: toISOString(today),
    updated_at: toISOString(now),
  },
  {
    id: 'note-4',
    title: 'Team Meeting Notes - Dec 28',
    content: `# Team Meeting Notes

## Attendees
- Me, Sarah, John, Alex

## Discussion Points
1. Sprint planning for next week
2. API integration timeline
3. UX feedback from user testing

## Action Items
- [ ] Sarah: Update design mockups
- [ ] John: Set up staging environment
- [ ] Me: Complete API hooks

## Next Meeting
Tuesday, 2:00 PM`,
    note_type: 'meeting',
    life_area: 'professional',
    tags: ['meeting', 'team', 'planning'],
    is_pinned: false,
    word_count: 55,
    backlinks: [],
    created_at: toISOString(yesterday),
    updated_at: toISOString(yesterday),
  },
]

// ============================================================================
// Goals
// ============================================================================

export const mockGoals: Goal[] = [
  {
    id: 'goal-1',
    title: 'Launch Life Planner MVP',
    description: 'Complete and launch the minimum viable product for the Life Planner application',
    status: 'active',
    life_area: 'professional',
    target_date: toISOString(nextWeek),
    progress: 65,
    milestones: [
      { id: 'm1', title: 'Complete database schema', completed: true, completed_at: toISOString(lastWeek) },
      { id: 'm2', title: 'Build core API endpoints', completed: true, completed_at: toISOString(yesterday) },
      { id: 'm3', title: 'Implement React frontend', completed: false },
      { id: 'm4', title: 'User testing and feedback', completed: false },
      { id: 'm5', title: 'Deploy to production', completed: false },
    ],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'goal-2',
    title: 'Run a Half Marathon',
    description: 'Train for and complete a half marathon race',
    status: 'active',
    life_area: 'health',
    target_date: toISOString(new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000)),
    progress: 35,
    milestones: [
      { id: 'm1', title: 'Run 5K without stopping', completed: true, completed_at: toISOString(lastWeek) },
      { id: 'm2', title: 'Run 10K', completed: false },
      { id: 'm3', title: 'Run 15K', completed: false },
      { id: 'm4', title: 'Complete half marathon', completed: false },
    ],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'goal-3',
    title: 'Read 24 Books This Year',
    description: 'Read 2 books per month across various genres',
    status: 'active',
    life_area: 'learning',
    target_date: toISOString(new Date(today.getFullYear(), 11, 31)),
    progress: 25,
    milestones: [
      { id: 'm1', title: 'Read 6 books (Q1)', completed: true, completed_at: toISOString(lastWeek) },
      { id: 'm2', title: 'Read 12 books (Q2)', completed: false },
      { id: 'm3', title: 'Read 18 books (Q3)', completed: false },
      { id: 'm4', title: 'Read 24 books (Q4)', completed: false },
    ],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
  {
    id: 'goal-4',
    title: 'Build Emergency Fund',
    description: 'Save 6 months of expenses in an emergency fund',
    status: 'active',
    life_area: 'finance',
    target_date: toISOString(new Date(today.getTime() + 180 * 24 * 60 * 60 * 1000)),
    progress: 50,
    milestones: [
      { id: 'm1', title: 'Save 1 month expenses', completed: true },
      { id: 'm2', title: 'Save 3 months expenses', completed: true },
      { id: 'm3', title: 'Save 6 months expenses', completed: false },
    ],
    created_at: toISOString(lastWeek),
    updated_at: toISOString(now),
  },
]

// ============================================================================
// Dashboard Data
// ============================================================================

export const mockDashboardStats: DashboardStats = {
  tasks_today: 5,
  tasks_overdue: 1,
  completion_rate: 72,
  streak_days: 7,
}

export const mockGoalSummaries: GoalSummary[] = mockGoals.map((goal) => ({
  id: goal.id,
  title: goal.title,
  progress: goal.progress,
  life_area: goal.life_area,
}))

export const mockActivityItems: ActivityItem[] = [
  {
    id: 'act-1',
    type: 'task_completed',
    title: 'Completed: Morning workout - 30 min cardio',
    timestamp: toISOString(new Date(today.getTime() + 7.5 * 60 * 60 * 1000)),
  },
  {
    id: 'act-2',
    type: 'goal_progress',
    title: 'Updated progress: Launch Life Planner MVP (65%)',
    timestamp: toISOString(yesterday),
  },
  {
    id: 'act-3',
    type: 'note_updated',
    title: 'Updated note: Life Planner Architecture',
    timestamp: toISOString(yesterday),
  },
  {
    id: 'act-4',
    type: 'event_created',
    title: 'Created event: Design Review Meeting',
    timestamp: toISOString(yesterday),
  },
]

export const mockDashboardData: DashboardData = {
  stats: mockDashboardStats,
  priority_tasks: mockTasks.filter((t) => t.status !== 'done' && t.priority >= 4).slice(0, 5),
  upcoming_events: mockEvents.slice(0, 3),
  goal_summaries: mockGoalSummaries,
  recent_activity: mockActivityItems,
}

// ============================================================================
// Progress Logs
// ============================================================================

export const mockProgressLogs: ProgressLog[] = [
  {
    id: 'log-1',
    goal_id: 'goal-1',
    progress_delta: 15,
    note: 'Completed API endpoints',
    logged_at: toISOString(yesterday),
  },
  {
    id: 'log-2',
    goal_id: 'goal-2',
    progress_delta: 5,
    note: 'Ran 8K today, feeling good',
    logged_at: toISOString(yesterday),
  },
]

// ============================================================================
// NLP Parsing Examples
// ============================================================================

export const mockParsedInputs: Record<string, ParsedInput> = {
  'remind me to call mom tomorrow at 3pm': {
    type: 'task',
    title: 'Call mom',
    due_date: toISOString(tomorrow),
    due_time: '15:00',
    priority: 3,
    life_area: 'relationships',
    raw_input: 'remind me to call mom tomorrow at 3pm',
  },
  'schedule a meeting with the team next monday at 10am': {
    type: 'event',
    title: 'Meeting with the team',
    due_date: toISOString(nextWeek),
    due_time: '10:00',
    raw_input: 'schedule a meeting with the team next monday at 10am',
  },
  'note about the project architecture decisions': {
    type: 'note',
    title: 'Project architecture decisions',
    life_area: 'professional',
    raw_input: 'note about the project architecture decisions',
  },
}

// ============================================================================
// Helper Functions for Mock Data
// ============================================================================

/**
 * Simulate network delay for more realistic testing
 */
export async function simulateDelay(ms: number = 200): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Deep clone an object to prevent mutation
 */
export function cloneDeep<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

/**
 * Generate a new mock task
 */
export function createMockTask(input: Partial<Task>): Task {
  return {
    id: generateId(),
    title: input.title || 'New Task',
    status: 'todo' as TaskStatus,
    priority: 3 as Priority,
    tags: [],
    created_at: toISOString(now),
    updated_at: toISOString(now),
    ...input,
  }
}

/**
 * Generate a new mock event
 */
export function createMockEvent(input: Partial<CalendarEvent>): CalendarEvent {
  const start = input.start_time ? new Date(input.start_time) : now
  const end = input.end_time ? new Date(input.end_time) : new Date(start.getTime() + 60 * 60 * 1000)

  return {
    id: generateId(),
    title: input.title || 'New Event',
    start_time: toISOString(start),
    end_time: toISOString(end),
    all_day: false,
    event_type: 'meeting' as EventType,
    created_at: toISOString(now),
    updated_at: toISOString(now),
    ...input,
  }
}

/**
 * Generate a new mock note
 */
export function createMockNote(input: Partial<Note>): Note {
  return {
    id: generateId(),
    title: input.title || 'New Note',
    content: input.content || '',
    note_type: 'note' as NoteType,
    tags: [],
    is_pinned: false,
    word_count: (input.content || '').split(/\s+/).length,
    backlinks: [],
    created_at: toISOString(now),
    updated_at: toISOString(now),
    ...input,
  }
}

/**
 * Generate a new mock goal
 */
export function createMockGoal(input: Partial<Goal>): Goal {
  return {
    id: generateId(),
    title: input.title || 'New Goal',
    status: 'active' as GoalStatus,
    progress: 0,
    milestones: [],
    created_at: toISOString(now),
    updated_at: toISOString(now),
    ...input,
  }
}
