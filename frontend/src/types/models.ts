/**
 * Core domain models for the Life Planner
 */

import type { TaskStatus, Priority, LifeArea, GoalStatus, NoteType, EventType } from '@/lib/constants'

// Base model with common fields
export interface BaseModel {
  id: string
  created_at: string
  updated_at: string
}

// Task model
export interface Task extends BaseModel {
  title: string
  description?: string
  status: TaskStatus
  priority: Priority
  due_date?: string
  due_time?: string
  estimated_minutes?: number
  actual_minutes?: number
  life_area?: LifeArea
  project_id?: string
  parent_id?: string
  tags: string[]
  completed_at?: string
  waiting_for?: string
  waiting_since?: string
  metadata?: Record<string, unknown>
}

export interface TaskCreateInput {
  title: string
  description?: string
  priority?: Priority
  due_date?: string
  due_time?: string
  estimated_minutes?: number
  life_area?: LifeArea
  project_id?: string
  parent_id?: string
  tags?: string[]
}

export interface TaskUpdateInput extends Partial<TaskCreateInput> {
  status?: TaskStatus
  completed_at?: string
  waiting_for?: string
}

// Project model
export interface Project extends BaseModel {
  name: string
  description?: string
  status: 'active' | 'completed' | 'archived'
  life_area?: LifeArea
  color?: string
  icon?: string
  due_date?: string
  metadata?: Record<string, unknown>
}

// Calendar Event model
export interface CalendarEvent extends BaseModel {
  title: string
  description?: string
  start_time: string
  end_time: string
  all_day: boolean
  location?: string
  event_type: EventType
  calendar_source?: string
  external_id?: string
  recurrence_rule?: string
  color?: string
  metadata?: Record<string, unknown>
}

export interface CalendarEventCreateInput {
  title: string
  description?: string
  start_time: string
  end_time: string
  all_day?: boolean
  location?: string
  event_type?: EventType
  color?: string
}

// Note model
export interface Note extends BaseModel {
  title: string
  content: string
  note_type: NoteType
  life_area?: LifeArea
  tags: string[]
  is_pinned: boolean
  word_count: number
  backlinks: string[]
  metadata?: Record<string, unknown>
}

export interface NoteCreateInput {
  title: string
  content?: string
  note_type?: NoteType
  life_area?: LifeArea
  tags?: string[]
}

// Goal model
export interface Goal extends BaseModel {
  title: string
  description?: string
  status: GoalStatus
  life_area?: LifeArea
  target_date?: string
  progress: number
  milestones: Milestone[]
  metadata?: Record<string, unknown>
}

export interface Milestone {
  id: string
  title: string
  completed: boolean
  completed_at?: string
}

export interface GoalCreateInput {
  title: string
  description?: string
  life_area?: LifeArea
  target_date?: string
  milestones?: { title: string }[]
}

export interface ProgressLog {
  id: string
  goal_id: string
  progress_delta: number
  note?: string
  logged_at: string
}

// Dashboard types
export interface DashboardStats {
  tasks_today: number
  tasks_overdue: number
  completion_rate: number
  streak_days: number
}

export interface DashboardData {
  stats: DashboardStats
  priority_tasks: Task[]
  upcoming_events: CalendarEvent[]
  goal_summaries: GoalSummary[]
  recent_activity: ActivityItem[]
}

export interface GoalSummary {
  id: string
  title: string
  progress: number
  life_area?: LifeArea
}

export interface ActivityItem {
  id: string
  type: 'task_completed' | 'note_updated' | 'goal_progress' | 'event_created'
  title: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// Filter types
export interface TaskFilters {
  status?: TaskStatus[]
  priority?: Priority[]
  life_area?: LifeArea[]
  project_id?: string
  has_due_date?: boolean
  overdue_only?: boolean
  search?: string
}

export interface NoteFilters {
  note_type?: NoteType[]
  life_area?: LifeArea[]
  tags?: string[]
  search?: string
}

export interface GoalFilters {
  status?: GoalStatus[]
  life_area?: LifeArea[]
}

// API response types
export interface ApiResponse<T> {
  data: T
  success: boolean
  error?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

// NLP parsing result
export interface ParsedInput {
  type: 'task' | 'event' | 'note'
  title: string
  due_date?: string
  due_time?: string
  priority?: Priority
  tags?: string[]
  life_area?: LifeArea
  raw_input: string
}
