import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LifeArea, Priority } from '@/lib/constants'

type Theme = 'dark' | 'light' | 'system'
type DateFormat = 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD'
type TimeFormat = '12h' | '24h'
type CalendarView = 'day' | 'week' | 'month'

interface PreferencesState {
  // Display
  theme: Theme
  setTheme: (theme: Theme) => void

  // Date/Time
  timezone: string
  setTimezone: (timezone: string) => void
  dateFormat: DateFormat
  setDateFormat: (format: DateFormat) => void
  timeFormat: TimeFormat
  setTimeFormat: (format: TimeFormat) => void
  weekStartsOn: 0 | 1 | 6 // 0 = Sunday, 1 = Monday, 6 = Saturday
  setWeekStartsOn: (day: 0 | 1 | 6) => void

  // Defaults
  defaultLifeArea: LifeArea | null
  setDefaultLifeArea: (area: LifeArea | null) => void
  defaultPriority: Priority
  setDefaultPriority: (priority: Priority) => void
  defaultCalendarView: CalendarView
  setDefaultCalendarView: (view: CalendarView) => void

  // Notifications
  notificationsEnabled: boolean
  setNotificationsEnabled: (enabled: boolean) => void
  dailyReviewTime: string | null // HH:mm format
  setDailyReviewTime: (time: string | null) => void

  // Tasks
  showCompletedTasks: boolean
  setShowCompletedTasks: (show: boolean) => void
  autoArchiveCompletedDays: number // 0 = never
  setAutoArchiveCompletedDays: (days: number) => void

  // Reset
  resetPreferences: () => void
}

const defaultPreferences = {
  theme: 'dark' as Theme,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  dateFormat: 'MM/DD/YYYY' as DateFormat,
  timeFormat: '12h' as TimeFormat,
  weekStartsOn: 0 as 0 | 1 | 6,
  defaultLifeArea: null,
  defaultPriority: 3 as Priority,
  defaultCalendarView: 'week' as CalendarView,
  notificationsEnabled: true,
  dailyReviewTime: '09:00',
  showCompletedTasks: true,
  autoArchiveCompletedDays: 7,
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      ...defaultPreferences,

      // Display
      setTheme: (theme) => set({ theme }),

      // Date/Time
      setTimezone: (timezone) => set({ timezone }),
      setDateFormat: (dateFormat) => set({ dateFormat }),
      setTimeFormat: (timeFormat) => set({ timeFormat }),
      setWeekStartsOn: (weekStartsOn) => set({ weekStartsOn }),

      // Defaults
      setDefaultLifeArea: (defaultLifeArea) => set({ defaultLifeArea }),
      setDefaultPriority: (defaultPriority) => set({ defaultPriority }),
      setDefaultCalendarView: (defaultCalendarView) => set({ defaultCalendarView }),

      // Notifications
      setNotificationsEnabled: (notificationsEnabled) => set({ notificationsEnabled }),
      setDailyReviewTime: (dailyReviewTime) => set({ dailyReviewTime }),

      // Tasks
      setShowCompletedTasks: (showCompletedTasks) => set({ showCompletedTasks }),
      setAutoArchiveCompletedDays: (autoArchiveCompletedDays) =>
        set({ autoArchiveCompletedDays }),

      // Reset
      resetPreferences: () => set(defaultPreferences),
    }),
    {
      name: 'life-planner-preferences',
    }
  )
)
