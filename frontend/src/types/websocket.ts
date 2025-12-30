/**
 * WebSocket Message Types
 *
 * CS Concept: **Event-Driven Architecture** - Components communicate
 * through events rather than direct calls. This decouples the sender
 * from receivers and enables easy extensibility.
 */

import type { Task, CalendarEvent, Note, Goal } from './models'

// ============================================================
// CLIENT → SERVER MESSAGES
// ============================================================

export interface SubscribeMessage {
  type: 'subscribe'
  topics: Topic[]
}

export interface UnsubscribeMessage {
  type: 'unsubscribe'
  topics: Topic[]
}

export interface PingMessage {
  type: 'ping'
  timestamp: number
}

export type ClientMessage = SubscribeMessage | UnsubscribeMessage | PingMessage

// ============================================================
// SERVER → CLIENT MESSAGES
// ============================================================

// Task Events
export interface TaskCreatedEvent {
  type: 'task_created'
  data: Task
  timestamp: string
}

export interface TaskUpdatedEvent {
  type: 'task_updated'
  data: Task
  timestamp: string
}

export interface TaskDeletedEvent {
  type: 'task_deleted'
  id: string
  timestamp: string
}

export interface TaskCompletedEvent {
  type: 'task_completed'
  data: Task
  timestamp: string
}

// Calendar Events
export interface EventCreatedEvent {
  type: 'event_created'
  data: CalendarEvent
  timestamp: string
}

export interface EventUpdatedEvent {
  type: 'event_updated'
  data: CalendarEvent
  timestamp: string
}

export interface EventDeletedEvent {
  type: 'event_deleted'
  id: string
  timestamp: string
}

// Note Events
export interface NoteCreatedEvent {
  type: 'note_created'
  data: Note
  timestamp: string
}

export interface NoteUpdatedEvent {
  type: 'note_updated'
  data: Note
  timestamp: string
}

export interface NoteDeletedEvent {
  type: 'note_deleted'
  id: string
  timestamp: string
}

// Goal Events
export interface GoalProgressEvent {
  type: 'goal_progress'
  goalId: string
  progress: number
  timestamp: string
}

export interface GoalUpdatedEvent {
  type: 'goal_updated'
  data: Goal
  timestamp: string
}

// Dashboard Events
export interface DashboardRefreshEvent {
  type: 'dashboard_refresh'
  timestamp: string
}

// System Messages
export interface PongMessage {
  type: 'pong'
  timestamp: number
  serverTime: string
}

export interface ErrorMessage {
  type: 'error'
  code: string
  message: string
}

// Union type of all server messages
export type ServerMessage =
  | TaskCreatedEvent
  | TaskUpdatedEvent
  | TaskDeletedEvent
  | TaskCompletedEvent
  | EventCreatedEvent
  | EventUpdatedEvent
  | EventDeletedEvent
  | NoteCreatedEvent
  | NoteUpdatedEvent
  | NoteDeletedEvent
  | GoalProgressEvent
  | GoalUpdatedEvent
  | DashboardRefreshEvent
  | PongMessage
  | ErrorMessage

// ============================================================
// SUBSCRIPTION TOPICS
// ============================================================

export type Topic = 'tasks' | 'calendar' | 'notes' | 'goals' | 'dashboard'

export const ALL_TOPICS: Topic[] = ['tasks', 'calendar', 'notes', 'goals', 'dashboard']

// ============================================================
// CONNECTION STATE
// ============================================================

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

// ============================================================
// WEBSOCKET CONFIGURATION
// ============================================================

export interface WebSocketConfig {
  /** WebSocket URL (defaults to /ws) */
  url?: string
  /** Topics to subscribe to on connect */
  topics?: Topic[]
  /** Reconnect on disconnect */
  reconnect?: boolean
  /** Reconnect delay in ms (doubles each attempt, max 30s) */
  reconnectDelay?: number
  /** Maximum reconnect attempts (0 = infinite) */
  maxReconnectAttempts?: number
  /** Ping interval in ms (keeps connection alive) */
  pingInterval?: number
}
