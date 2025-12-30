import { User, Bell, Palette, Clock, Shield, Database, ChevronRight } from 'lucide-react'
import { AppShell } from '@/components/layout'

/**
 * Settings - User preferences and configuration page
 *
 * Features:
 * - Profile settings
 * - Notification preferences
 * - Display/theme settings
 * - Time zone and date format
 * - Privacy and data management
 *
 * Design pattern: **Settings Panel Pattern** - grouped categories
 * with progressive disclosure for complex configuration.
 */
export function Settings() {
  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Settings</h1>
          <p className="text-[var(--color-text-secondary)]">
            Manage your preferences and account settings
          </p>
        </div>

        {/* Settings sections */}
        <div className="space-y-4">
          <SettingsSection
            icon={User}
            title="Profile"
            description="Your name, email, and profile picture"
          >
            <SettingsRow label="Display Name" value="User" />
            <SettingsRow label="Email" value="user@example.com" />
            <SettingsRow label="Profile Picture" value="Set photo" />
          </SettingsSection>

          <SettingsSection
            icon={Bell}
            title="Notifications"
            description="Manage how you receive notifications"
          >
            <SettingsToggle label="Email Notifications" description="Receive daily digest emails" />
            <SettingsToggle
              label="Push Notifications"
              description="Desktop and mobile push notifications"
            />
            <SettingsToggle label="Daily Review Reminder" description="Reminder for morning review" />
          </SettingsSection>

          <SettingsSection
            icon={Palette}
            title="Appearance"
            description="Customize how the app looks"
          >
            <SettingsRow label="Theme" value="Dark" />
            <SettingsRow label="Accent Color" value="Blue" />
            <SettingsToggle label="Reduced Motion" description="Minimize animations" />
          </SettingsSection>

          <SettingsSection
            icon={Clock}
            title="Date & Time"
            description="Configure regional preferences"
          >
            <SettingsRow label="Timezone" value="America/Los_Angeles (PST)" />
            <SettingsRow label="Date Format" value="MM/DD/YYYY" />
            <SettingsRow label="Time Format" value="12-hour" />
            <SettingsRow label="Week Starts On" value="Sunday" />
          </SettingsSection>

          <SettingsSection
            icon={Shield}
            title="Privacy"
            description="Control your data and privacy"
          >
            <SettingsToggle
              label="Analytics"
              description="Help improve the app by sharing anonymous usage data"
            />
            <SettingsRow label="Export Data" value="Download all your data" />
          </SettingsSection>

          <SettingsSection
            icon={Database}
            title="Data"
            description="Manage your data and storage"
          >
            <SettingsRow label="Storage Used" value="12.4 MB" />
            <SettingsRow label="Clear Cache" value="Free up space" />
            <SettingsRow label="Reset All Data" value="Delete everything" danger />
          </SettingsSection>
        </div>
      </div>
    </AppShell>
  )
}

// Settings section component
interface SettingsSectionProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  children: React.ReactNode
}

function SettingsSection({ icon: Icon, title, description, children }: SettingsSectionProps) {
  return (
    <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]">
      <div className="flex items-center gap-3 border-b border-[var(--color-border-subtle)] px-5 py-4">
        <div className="rounded-lg bg-[var(--color-bg-tertiary)] p-2">
          <Icon className="h-5 w-5 text-[var(--color-text-secondary)]" />
        </div>
        <div>
          <h2 className="font-semibold text-[var(--color-text-primary)]">{title}</h2>
          <p className="text-sm text-[var(--color-text-tertiary)]">{description}</p>
        </div>
      </div>
      <div className="divide-y divide-[var(--color-border-subtle)]">{children}</div>
    </div>
  )
}

// Settings row (label + value)
interface SettingsRowProps {
  label: string
  value: string
  danger?: boolean
}

function SettingsRow({ label, value, danger }: SettingsRowProps) {
  return (
    <button className="flex w-full items-center justify-between px-5 py-3 text-left hover:bg-[var(--color-bg-hover)]">
      <span className="text-sm text-[var(--color-text-primary)]">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`text-sm ${danger ? 'text-[var(--color-accent-red)]' : 'text-[var(--color-text-secondary)]'}`}>
          {value}
        </span>
        <ChevronRight className="h-4 w-4 text-[var(--color-text-tertiary)]" />
      </div>
    </button>
  )
}

// Settings toggle
interface SettingsToggleProps {
  label: string
  description?: string
}

function SettingsToggle({ label, description }: SettingsToggleProps) {
  return (
    <div className="flex items-center justify-between px-5 py-3">
      <div>
        <p className="text-sm text-[var(--color-text-primary)]">{label}</p>
        {description && (
          <p className="text-xs text-[var(--color-text-tertiary)]">{description}</p>
        )}
      </div>
      {/* Toggle placeholder */}
      <div className="h-6 w-11 rounded-full bg-[var(--color-bg-tertiary)]">
        <div className="ml-0.5 mt-0.5 h-5 w-5 rounded-full bg-[var(--color-text-tertiary)]" />
      </div>
    </div>
  )
}

export default Settings
