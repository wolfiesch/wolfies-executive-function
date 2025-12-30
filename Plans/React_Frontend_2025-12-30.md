# Life Planner React Frontend - Comprehensive Plan

**Created:** 12/30/2025 05:21 AM PST (via pst-timestamp)
**Status:** Planning Phase

---

## Executive Summary

A sleek, modern React frontend with a **Twitter-inspired dark aesthetic** that surfaces all life-planner functionality through an intuitive, highly functional UI. The design philosophy centers on **information density without clutter**, **keyboard-first interactions**, and **proactive intelligence**.

---

## 1. Design Philosophy & Aesthetic

### Visual Identity: "Obsidian Command Center"

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Primary Theme** | Pure dark mode (no light mode initially) | Focus, reduced eye strain, modern aesthetic |
| **Color Palette** | Black backgrounds with subtle blue accents | Twitter-like, professional, high contrast |
| **Typography** | Inter for UI, JetBrains Mono for data | Readability + developer-friendly |
| **Density** | Medium-high information density | Power users want to see more, not less |
| **Motion** | Subtle, purposeful animations | Responsive feel without distraction |
| **Layout** | Sidebar + main content + optional right panel | Proven pattern (Twitter, Discord, Slack) |

### Color System

```scss
// Core Backgrounds (layered depth)
--bg-primary: #000000;      // True black base
--bg-secondary: #0a0a0a;    // Elevated surfaces
--bg-tertiary: #141414;     // Cards, modals
--bg-hover: #1a1a1a;        // Hover states
--bg-active: #222222;       // Active/selected states

// Borders & Dividers
--border-subtle: #1e1e1e;   // Subtle separation
--border-default: #2e2e2e;  // Standard borders
--border-strong: #3e3e3e;   // Emphasized borders

// Text Hierarchy
--text-primary: #e7e9ea;    // Primary content (Twitter-like)
--text-secondary: #71767b;  // Secondary content
--text-tertiary: #4a4a4a;   // Tertiary/disabled
--text-link: #1d9bf0;       // Links

// Accent Colors (semantic)
--accent-blue: #1d9bf0;     // Primary actions, links
--accent-green: #00ba7c;    // Success, done, positive
--accent-yellow: #ffd400;   // Warning, attention
--accent-red: #f4212e;      // Danger, overdue, critical
--accent-purple: #7856ff;   // Goals, progress
--accent-orange: #ff7a00;   // High priority

// Priority Colors (P1-P5)
--priority-5: #f4212e;      // Critical - red
--priority-4: #ff7a00;      // High - orange
--priority-3: #ffd400;      // Normal - yellow
--priority-2: #71767b;      // Low - gray
--priority-1: #4a4a4a;      // Optional - dim gray
```

### Typography Scale

```scss
// Font Families
--font-ui: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

// Size Scale (rem-based for accessibility)
--text-xs: 0.75rem;    // 12px - metadata, timestamps
--text-sm: 0.875rem;   // 14px - secondary content
--text-base: 1rem;     // 16px - body text
--text-lg: 1.125rem;   // 18px - emphasized content
--text-xl: 1.25rem;    // 20px - section headers
--text-2xl: 1.5rem;    // 24px - page headers
--text-3xl: 1.875rem;  // 30px - dashboard hero

// Font Weights
--weight-normal: 400;
--weight-medium: 500;
--weight-semibold: 600;
--weight-bold: 700;
```

---

## 2. Tech Stack

### Core Framework

| Technology | Version | Rationale |
|------------|---------|-----------|
| **React** | 19.x | Latest features, concurrent rendering |
| **TypeScript** | 5.x | Type safety, better DX, refactoring confidence |
| **Vite** | 6.x | Fast dev server, optimized builds, ESM native |
| **React Router** | 7.x | File-based routing, data loading patterns |

### State Management

| Layer | Technology | Use Case |
|-------|------------|----------|
| **Server State** | TanStack Query (React Query) v5 | API data fetching, caching, optimistic updates |
| **Client State** | Zustand | UI state, preferences, sidebar collapse |
| **Form State** | React Hook Form + Zod | Form handling with validation |
| **URL State** | React Router + nuqs | Shareable filter states |

**Why This Stack:**
- TanStack Query handles 90% of state (server data) with automatic caching, background refetching, and optimistic updates
- Zustand is minimal (~2KB) for the remaining UI state - no Redux boilerplate
- URL state means filter settings persist through refresh and are shareable

### Styling

| Technology | Rationale |
|------------|-----------|
| **Tailwind CSS v4** | Utility-first, design system as code, great DX |
| **CSS Variables** | Theming, runtime customization |
| **Framer Motion** | Declarative animations, gesture support |
| **Radix UI Primitives** | Accessible, unstyled components as foundation |
| **Lucide Icons** | Clean, consistent icon set (open source) |

### Data Visualization

| Library | Use Case |
|---------|----------|
| **Recharts** | Charts (progress, completion rates, time tracking) |
| **react-calendar-timeline** | Gantt-style timeline views |
| **@nivo/calendar** | GitHub-style contribution heatmaps |

### Additional Libraries

| Library | Purpose |
|---------|---------|
| **date-fns** | Date manipulation (already used in backend) |
| **cmdk** | Command palette (⌘K) |
| **react-hot-toast** | Toast notifications |
| **@tiptap/react** | Rich text editor for notes |
| **react-markdown** | Markdown rendering |
| **react-hotkeys-hook** | Keyboard shortcuts |

---

## 3. Application Architecture

### Directory Structure

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Root component, providers
│   ├── routes.tsx                  # Route definitions
│   │
│   ├── api/                        # API layer
│   │   ├── client.ts               # Axios/fetch wrapper
│   │   ├── endpoints.ts            # API endpoint definitions
│   │   └── hooks/                  # React Query hooks
│   │       ├── useTasks.ts
│   │       ├── useCalendar.ts
│   │       ├── useNotes.ts
│   │       ├── useGoals.ts
│   │       └── useDashboard.ts
│   │
│   ├── components/                 # Shared components
│   │   ├── ui/                     # Base UI primitives
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Dialog.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Avatar.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/                 # Layout components
│   │   │   ├── AppShell.tsx        # Main app wrapper
│   │   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   │   ├── Header.tsx          # Top bar
│   │   │   ├── RightPanel.tsx      # Optional detail panel
│   │   │   └── CommandPalette.tsx  # ⌘K command menu
│   │   │
│   │   ├── tasks/                  # Task-specific components
│   │   │   ├── TaskCard.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskDetail.tsx
│   │   │   ├── TaskForm.tsx
│   │   │   ├── TaskFilters.tsx
│   │   │   ├── PriorityBadge.tsx
│   │   │   └── StatusDropdown.tsx
│   │   │
│   │   ├── calendar/               # Calendar components
│   │   │   ├── CalendarGrid.tsx
│   │   │   ├── WeekView.tsx
│   │   │   ├── DayView.tsx
│   │   │   ├── MonthView.tsx
│   │   │   ├── EventCard.tsx
│   │   │   ├── TimeBlock.tsx
│   │   │   └── EventForm.tsx
│   │   │
│   │   ├── notes/                  # Note components
│   │   │   ├── NoteCard.tsx
│   │   │   ├── NoteEditor.tsx
│   │   │   ├── NoteList.tsx
│   │   │   ├── NoteGraph.tsx
│   │   │   ├── BacklinkPanel.tsx
│   │   │   └── TagCloud.tsx
│   │   │
│   │   ├── goals/                  # Goal components
│   │   │   ├── GoalCard.tsx
│   │   │   ├── GoalProgress.tsx
│   │   │   ├── MilestoneList.tsx
│   │   │   ├── KeyResultTracker.tsx
│   │   │   └── GoalForm.tsx
│   │   │
│   │   ├── dashboard/              # Dashboard components
│   │   │   ├── TodayHero.tsx
│   │   │   ├── PriorityList.tsx
│   │   │   ├── TimelineFeed.tsx
│   │   │   ├── StatsGrid.tsx
│   │   │   ├── UpcomingEvents.tsx
│   │   │   └── QuickCapture.tsx
│   │   │
│   │   └── common/                 # Shared functional components
│   │       ├── NaturalLanguageInput.tsx
│   │       ├── DateTimePicker.tsx
│   │       ├── RelativeTime.tsx
│   │       ├── ProgressRing.tsx
│   │       ├── EmptyState.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── pages/                      # Route pages
│   │   ├── Dashboard.tsx           # Today view / home
│   │   ├── Tasks.tsx               # Task management
│   │   ├── TaskDetail.tsx          # Single task view
│   │   ├── Calendar.tsx            # Calendar view
│   │   ├── Notes.tsx               # Notes/PKM
│   │   ├── NoteDetail.tsx          # Single note editor
│   │   ├── Goals.tsx               # Goals dashboard
│   │   ├── GoalDetail.tsx          # Single goal view
│   │   ├── Projects.tsx            # Project management
│   │   ├── Search.tsx              # Global search
│   │   ├── Settings.tsx            # User settings
│   │   └── NotFound.tsx            # 404 page
│   │
│   ├── stores/                     # Zustand stores
│   │   ├── uiStore.ts              # Sidebar, panels, modals
│   │   ├── preferencesStore.ts     # User preferences
│   │   └── selectionStore.ts       # Multi-select state
│   │
│   ├── hooks/                      # Custom hooks
│   │   ├── useKeyboardShortcuts.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useMediaQuery.ts
│   │   ├── useDebounce.ts
│   │   └── useClickOutside.ts
│   │
│   ├── lib/                        # Utilities
│   │   ├── utils.ts                # General utilities
│   │   ├── dates.ts                # Date formatting
│   │   ├── cn.ts                   # Tailwind class merger
│   │   └── constants.ts            # App constants
│   │
│   ├── types/                      # TypeScript types
│   │   ├── api.ts                  # API response types
│   │   ├── models.ts               # Domain models
│   │   └── ui.ts                   # UI types
│   │
│   └── styles/
│       ├── globals.css             # Global styles, CSS variables
│       └── tailwind.css            # Tailwind directives
│
├── index.html
├── tailwind.config.ts
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## 4. Page Designs

### 4.1 Dashboard (Today View) - Primary Landing Page

The command center. Shows everything you need to know at a glance.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────┐                                              🔍 ⌘K     ⚙️ 👤    │
│ │         │  LIFE PLANNER                                                   │
│ │  Logo   │────────────────────────────────────────────────────────────────│
│ │         │                                                                 │
│ ├─────────┤  ┌───────────────────────────────────────┬──────────────────┐  │
│ │         │  │                                       │                  │  │
│ │ 📊 Today │  │  Good morning, Wolfgang!              │   UPCOMING       │  │
│ │         │  │  Monday, December 30                  │   ─────────      │  │
│ │ ✅ Tasks │  │                                       │   9:00 AM        │  │
│ │         │  │  ┌─────────┬─────────┬─────────┐     │   Team standup   │  │
│ │ 📅 Cal   │  │  │  12     │   4     │  87%    │     │                  │  │
│ │         │  │  │  Tasks  │ Overdue │ Rate    │     │   11:30 AM       │  │
│ │ 📝 Notes │  │  │  today  │         │         │     │   Lunch w/ Sarah │  │
│ │         │  │  └─────────┴─────────┴─────────┘     │                  │  │
│ │ 🎯 Goals │  │                                       │   2:00 PM        │  │
│ │         │  │  ────────────────────────────────     │   Deep work      │  │
│ │ 📁 Proj  │  │  TOP PRIORITIES                      │   (blocked)      │  │
│ │         │  │  ────────────────────────────────     │                  │  │
│ │ ─────── │  │                                       │──────────────────│  │
│ │         │  │  ◐ Review Q4 metrics report      P5  │                  │  │
│ │ 👥 People│  │    Due today · 45m · Professional   │   GOAL PROGRESS  │  │
│ │         │  │                                       │   ─────────      │  │
│ │ 📈 Review│  │  ○ Finalize budget proposal     P4  │                  │  │
│ │         │  │    Due today · 1h 30m · Finance      │   ▓▓▓▓▓░░░ 65%   │  │
│ │         │  │                                       │   Learn Piano    │  │
│ │         │  │  ○ Call mom back                 P3  │                  │  │
│ │         │  │    Due today · 15m · Relationships   │   ▓▓▓▓▓▓▓░ 82%   │  │
│ │         │  │                                       │   Fitness Q4     │  │
│ │         │  │  ○ Ship login feature            P4  │                  │  │
│ │         │  │    Overdue 2d · 3h · Professional    │──────────────────│  │
│ │         │  │                                       │                  │  │
│ │         │  │  ────────────────────────────────     │   QUICK CAPTURE  │  │
│ │         │  │  RECENT ACTIVITY                      │   ─────────      │  │
│ │         │  │  ────────────────────────────────     │                  │  │
│ │ ─────── │  │                                       │  ┌────────────┐  │  │
│ │         │  │  ✓ Completed "Fix auth bug"  2h ago  │  │ Add task...│  │  │
│ │ ⚙️ Set   │  │  📝 Updated "Meeting notes"  3h ago  │  │            │  │  │
│ │         │  │  🎯 Progress on "Fitness"    4h ago  │  └────────────┘  │  │
│ └─────────┘  └───────────────────────────────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Time-based greeting with current date
- Stats cards: tasks due, overdue count, completion rate
- Top priorities list with status indicators, priority badges, time estimates
- Upcoming events timeline
- Goal progress summaries
- Quick capture input for rapid task entry
- Recent activity feed

### 4.2 Tasks Page

Full task management with filtering, sorting, and bulk operations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TASKS                                        [+ New Task]  🔍 ⌘K     ⚙️ 👤  │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 🔍 Search tasks...                            Filters ▼  Sort ▼     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Status: All ▼  │ Priority: All ▼  │ Project: All ▼  │ Life Area: All ▼│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────┬────────────────────┐  │
│  │ TASK LIST                          12 tasks     │   TASK DETAIL      │  │
│  │─────────────────────────────────────────────────│                    │  │
│  │                                                 │   Review Q4 Report │  │
│  │  ☐ Review Q4 metrics report              P5    │   ─────────────────│  │
│  │    📁 Q4 Planning · Due today · 45m            │                    │  │
│  │                                                 │   Status: In Prog  │  │
│  │  ☐ Finalize budget proposal              P4    │   Priority: ●●●●●  │  │
│  │    📁 Finance Review · Due today · 1h 30m      │   Due: Today 5pm   │  │
│  │                                                 │   Est: 45 minutes  │  │
│  │  ☐ Call mom back                         P3    │   Project: Q4 Plan │  │
│  │    📁 Personal · Due today · 15m               │   Area: Professional│  │
│  │                                                 │                    │  │
│  │  ☐ Ship login feature                    P4    │   Description:     │  │
│  │    📁 Auth Project · Overdue 2d · 3h           │   Review and summa-│  │
│  │    ⚠️ OVERDUE                                   │   rize the Q4 met- │  │
│  │                                                 │   rics for the...  │  │
│  │  ✓ Fix authentication bug                P5    │                    │  │
│  │    📁 Auth Project · Completed 2h ago          │   ┌──────────────┐ │  │
│  │                                                 │   │ ▶ Start      │ │  │
│  │  ☐ Update documentation                  P2    │   └──────────────┘ │  │
│  │    📁 Auth Project · Due in 3 days · 2h        │   ┌──────────────┐ │  │
│  │                                                 │   │ ✓ Complete   │ │  │
│  │  ☐ Schedule dentist appointment          P2    │   └──────────────┘ │  │
│  │    📁 Health · No due date · 10m               │                    │  │
│  │                                                 │   ─────────────────│  │
│  │  ◎ Waiting for client feedback           P3    │                    │  │
│  │    📁 Client Work · Due in 5 days              │   Subtasks (2/4)   │  │
│  │    ⏳ Waiting since Dec 28                      │   ☐ Pull data      │  │
│  │                                                 │   ☐ Create charts  │  │
│  │                                                 │   ✓ Get access     │  │
│  │  [Load more...]                                │   ✓ Review scope   │  │
│  └─────────────────────────────────────────────────┴────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Search with instant results
- Multi-filter system (status, priority, project, life area, date range)
- Sort options (due date, priority, created date, title)
- Task list with inline status indicators and context
- Slide-out detail panel (or dedicated page on click)
- Bulk selection and operations
- Keyboard navigation (j/k to move, x to select, e to edit)

### 4.3 Calendar Page

Week view as default with month/day toggles.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CALENDAR                                    [+ Event]  🔍 ⌘K     ⚙️ 👤      │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  < Dec 30 - Jan 5, 2025 >                   [Day] [Week] [Month]    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐          │
│  │  Mon   │  Tue   │  Wed   │  Thu   │  Fri   │  Sat   │  Sun   │          │
│  │  30    │  31    │   1    │   2    │   3    │   4    │   5    │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │        │        │        │        │        │        │        │          │
│  │ 8 AM   │        │        │        │        │        │        │          │
│  │        │        │        │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │▓▓▓▓▓▓▓▓│        │        │        │        │        │        │          │
│  │ 9 AM   │        │ New Yr │        │        │        │        │          │
│  │ Standup│        │ 🎉     │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │        │        │        │        │        │        │        │          │
│  │ 10 AM  │        │        │        │        │        │        │          │
│  │        │        │        │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │▓▓▓▓▓▓▓▓│▓▓▓▓▓▓▓▓│        │▓▓▓▓▓▓▓▓│        │        │        │          │
│  │ 11 AM  │ 1:1 w/ │        │ Client │        │        │        │          │
│  │ Lunch  │ Sarah  │        │ Call   │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │        │        │        │        │        │        │        │          │
│  │ 12 PM  │        │        │        │        │        │        │          │
│  │        │        │        │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │        │        │        │        │        │        │        │          │
│  │ 1 PM   │        │        │        │        │        │        │          │
│  │        │        │        │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │████████│████████│        │        │████████│        │        │          │
│  │ 2 PM   │ Deep   │        │        │ Focus  │        │        │          │
│  │ Deep   │ Work   │        │        │ Time   │        │        │          │
│  │ Work   │        │        │        │        │        │        │          │
│  │ Block  │        │        │        │        │        │        │          │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤          │
│  │        │        │        │        │        │        │        │          │
│  │ 5 PM   │        │        │        │        │        │        │          │
│  └────────┴────────┴────────┴────────┴────────┴────────┴────────┘          │
│                                                                             │
│  Legend:  ▓ Meeting  █ Focus Block  ░ Free Time                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Week/Day/Month view toggles
- Click-drag to create events
- Event color coding by calendar source
- Time block visualization for focus time
- "Find free time" button
- All-day events at top
- Sync status indicator for Google Calendar

### 4.4 Notes Page (PKM/Knowledge Base)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ NOTES                                       [+ New Note]  🔍 ⌘K     ⚙️ 👤   │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 🔍 Search notes...                                    View: List ▼  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┬──────────────────────────────────────────────────┐   │
│  │ SIDEBAR          │  NOTE EDITOR                                     │   │
│  │──────────────────│──────────────────────────────────────────────────│   │
│  │                  │                                                  │   │
│  │ Recent           │  # Meeting Notes: Project Kickoff               │   │
│  │ ────────         │                                                  │   │
│  │ 📝 Meeting notes │  **Date:** December 28, 2024                    │   │
│  │ 📝 Project ideas │  **Attendees:** Sarah, Mike, Wolfgang           │   │
│  │ 📝 Book notes    │                                                  │   │
│  │                  │  ## Key Decisions                                │   │
│  │ Journals         │                                                  │   │
│  │ ────────         │  - Launch date set for Q1 2025                  │   │
│  │ 📓 Dec 29, 2024  │  - Using React for frontend                     │   │
│  │ 📓 Dec 28, 2024  │  - Mike owns backend architecture               │   │
│  │ 📓 Dec 27, 2024  │                                                  │   │
│  │                  │  ## Action Items                                 │   │
│  │ Tags             │                                                  │   │
│  │ ────────         │  - [ ] Create project timeline                  │   │
│  │ #work (12)       │  - [ ] Schedule design review                   │   │
│  │ #ideas (8)       │  - [x] Send meeting recap                       │   │
│  │ #learning (5)    │                                                  │   │
│  │ #journal (23)    │  ## Related Notes                                │   │
│  │                  │                                                  │   │
│  │ Life Areas       │  [[Project Roadmap]]                            │   │
│  │ ────────         │  [[Q1 Planning]]                                │   │
│  │ 📁 Professional  │                                                  │   │
│  │ 📁 Personal      │──────────────────────────────────────────────────│   │
│  │ 📁 Learning      │                                                  │   │
│  │                  │  BACKLINKS (3)                                   │   │
│  │                  │  ────────                                        │   │
│  │                  │  • Project Roadmap → mentioned here             │   │
│  │                  │  • Weekly Review Dec 29 → references this       │   │
│  │                  │  • Team Standup Notes → linked                  │   │
│  └──────────────────┴──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Full markdown editor with live preview
- Bidirectional linking with [[wikilinks]]
- Backlinks panel showing incoming references
- Tag-based organization
- Full-text search across all notes
- Note type badges (journal, meeting, reference)
- Word count and reading time
- Export to PDF/markdown

### 4.5 Goals Page

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GOALS                                        [+ New Goal]  🔍 ⌘K    ⚙️ 👤   │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│  ┌─────────────────────────────────────┬────────────────────────────────┐  │
│  │ ACTIVE GOALS                        │  GOAL DETAIL                   │  │
│  │─────────────────────────────────────│                                │  │
│  │                                     │  🎯 Learn to Play Piano       │  │
│  │  🎯 Learn to Play Piano             │  ─────────────────────────────│  │
│  │     ▓▓▓▓▓▓▓░░░░░░░░ 45%            │                                │  │
│  │     🎵 Learning · Target: Mar 2025  │  Progress: 45%                 │  │
│  │                                     │  ┌────────────────────────┐   │  │
│  │  🎯 Run a Marathon                  │  │ ▓▓▓▓▓▓▓░░░░░░░░ 45%    │   │  │
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓░░░ 78%            │  └────────────────────────┘   │  │
│  │     🏃 Health · Target: Apr 2025    │                                │  │
│  │                                     │  Started: Oct 15, 2024        │  │
│  │  🎯 Ship Side Project               │  Target: Mar 31, 2025         │  │
│  │     ▓▓▓▓▓▓▓▓▓▓░░░░░ 62%            │  Days left: 91                │  │
│  │     💼 Professional · Target: Feb   │                                │  │
│  │                                     │  ─────────────────────────────│  │
│  │  🎯 Read 24 Books                   │                                │  │
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 92%            │  KEY RESULTS                   │  │
│  │     📚 Learning · 22/24 books       │                                │  │
│  │                                     │  ✓ Complete beginner course   │  │
│  │  🎯 Save Emergency Fund             │  ✓ Practice 30 min daily     │  │
│  │     ▓▓▓▓▓▓▓▓▓▓▓▓░░░ 80%            │  ◐ Learn 5 songs              │  │
│  │     💰 Finance · $8K / $10K         │    3/5 completed              │  │
│  │                                     │  ○ Perform for family         │  │
│  │─────────────────────────────────────│                                │  │
│  │                                     │  ─────────────────────────────│  │
│  │ COMPLETED (3)                       │                                │  │
│  │─────────────────────────────────────│  PROGRESS LOG                  │  │
│  │                                     │                                │  │
│  │  ✓ Launch Blog                      │  Dec 28 - Learned Für Elise  │  │
│  │     Completed Nov 2024              │  Dec 25 - Finished scales     │  │
│  │                                     │  Dec 20 - 1hr practice sess   │  │
│  │  ✓ Get Promoted                     │  Dec 15 - Started new song    │  │
│  │     Completed Oct 2024              │                                │  │
│  │                                     │  [+ Log Progress]              │  │
│  └─────────────────────────────────────┴────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Progress visualization with progress bars
- Key results/milestones tracking
- Progress logging with history
- Goal categories by life area
- Target date countdown
- Completion celebrations
- Archive for completed goals
- Goal-to-task linking

---

## 5. Core Components Design

### 5.1 Command Palette (⌘K)

The power-user's best friend. Access everything from one place.

```typescript
// Command categories
const commandCategories = [
  {
    name: 'Quick Actions',
    commands: [
      { id: 'new-task', label: 'New Task', shortcut: 'T', action: openNewTaskDialog },
      { id: 'new-event', label: 'New Event', shortcut: 'E', action: openNewEventDialog },
      { id: 'new-note', label: 'New Note', shortcut: 'N', action: openNewNoteDialog },
      { id: 'new-goal', label: 'New Goal', shortcut: 'G', action: openNewGoalDialog },
    ]
  },
  {
    name: 'Navigation',
    commands: [
      { id: 'go-dashboard', label: 'Go to Dashboard', shortcut: '1', action: () => navigate('/') },
      { id: 'go-tasks', label: 'Go to Tasks', shortcut: '2', action: () => navigate('/tasks') },
      { id: 'go-calendar', label: 'Go to Calendar', shortcut: '3', action: () => navigate('/calendar') },
      { id: 'go-notes', label: 'Go to Notes', shortcut: '4', action: () => navigate('/notes') },
      { id: 'go-goals', label: 'Go to Goals', shortcut: '5', action: () => navigate('/goals') },
    ]
  },
  {
    name: 'Search',
    commands: [
      { id: 'search-all', label: 'Search Everything...', action: openGlobalSearch },
      { id: 'search-tasks', label: 'Search Tasks...', action: openTaskSearch },
      { id: 'search-notes', label: 'Search Notes...', action: openNoteSearch },
    ]
  }
];
```

### 5.2 Natural Language Input Component

The magical input that understands what you mean.

```tsx
interface NaturalLanguageInputProps {
  placeholder?: string;
  onSubmit: (parsed: ParsedInput) => void;
  context?: 'task' | 'event' | 'note' | 'any';
}

// Examples of what it parses:
// "Call John tomorrow at 2pm #personal" → Task with due date, time, tag
// "Meeting with Sarah next Monday 10am-11am" → Calendar event
// "Remind me to review docs in 3 days P4" → Task with priority
// "Note: Great idea for the app - add dark mode" → Creates a note
```

### 5.3 Quick Capture Widget

Always accessible, minimal friction input.

```
┌─────────────────────────────────────────────────────┐
│ ✨ Add task, event, or note...                      │
│─────────────────────────────────────────────────────│
│ "Review proposal tomorrow 3pm P4 #work"            │
│                                                     │
│ Parsed: Task · Due: Dec 31 3:00 PM · Priority: 4   │
│         Tags: #work                                 │
│                                           [Create]  │
└─────────────────────────────────────────────────────┘
```

---

## 6. API Layer Design

### Backend API Endpoints

The frontend needs a REST API (or could use the agents via WebSocket for more dynamic interactions).

```typescript
// api/endpoints.ts

export const API_ROUTES = {
  // Tasks
  tasks: {
    list: 'GET /api/tasks',
    get: 'GET /api/tasks/:id',
    create: 'POST /api/tasks',
    update: 'PATCH /api/tasks/:id',
    delete: 'DELETE /api/tasks/:id',
    complete: 'POST /api/tasks/:id/complete',
    search: 'GET /api/tasks/search',
  },

  // Calendar
  calendar: {
    events: 'GET /api/calendar/events',
    get: 'GET /api/calendar/events/:id',
    create: 'POST /api/calendar/events',
    update: 'PATCH /api/calendar/events/:id',
    delete: 'DELETE /api/calendar/events/:id',
    freeTime: 'GET /api/calendar/free-time',
  },

  // Notes
  notes: {
    list: 'GET /api/notes',
    get: 'GET /api/notes/:id',
    create: 'POST /api/notes',
    update: 'PATCH /api/notes/:id',
    delete: 'DELETE /api/notes/:id',
    search: 'GET /api/notes/search',
    backlinks: 'GET /api/notes/:id/backlinks',
  },

  // Goals
  goals: {
    list: 'GET /api/goals',
    get: 'GET /api/goals/:id',
    create: 'POST /api/goals',
    update: 'PATCH /api/goals/:id',
    logProgress: 'POST /api/goals/:id/progress',
    milestones: 'GET /api/goals/:id/milestones',
    completeMilestone: 'POST /api/goals/:id/milestones/:milestoneId/complete',
  },

  // Dashboard
  dashboard: {
    today: 'GET /api/dashboard/today',
    stats: 'GET /api/dashboard/stats',
    recentActivity: 'GET /api/dashboard/activity',
  },

  // Configuration
  config: {
    preferences: 'GET /api/config/preferences',
    updatePreferences: 'PATCH /api/config/preferences',
    lifeAreas: 'GET /api/config/life-areas',
  },

  // Natural Language
  nlp: {
    parse: 'POST /api/nlp/parse',
  },
};
```

### React Query Hooks

```typescript
// api/hooks/useTasks.ts

export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => taskApi.list(filters),
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: ['tasks', id],
    queryFn: () => taskApi.get(id),
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: taskApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useCompleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => taskApi.complete(id),
    // Optimistic update
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['tasks'] });
      const previous = queryClient.getQueryData(['tasks']);
      queryClient.setQueryData(['tasks'], (old: Task[]) =>
        old.map(t => t.id === id ? { ...t, status: 'done' } : t)
      );
      return { previous };
    },
    onError: (err, id, context) => {
      queryClient.setQueryData(['tasks'], context?.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
```

---

## 7. State Management

### Zustand Stores

```typescript
// stores/uiStore.ts

interface UIState {
  sidebarCollapsed: boolean;
  rightPanelOpen: boolean;
  rightPanelContent: 'task' | 'event' | 'note' | null;
  rightPanelId: string | null;
  commandPaletteOpen: boolean;
  newTaskDialogOpen: boolean;
  newEventDialogOpen: boolean;

  // Actions
  toggleSidebar: () => void;
  openRightPanel: (content: 'task' | 'event' | 'note', id: string) => void;
  closeRightPanel: () => void;
  toggleCommandPalette: () => void;
  openNewTaskDialog: () => void;
  closeNewTaskDialog: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      rightPanelOpen: false,
      rightPanelContent: null,
      rightPanelId: null,
      commandPaletteOpen: false,
      newTaskDialogOpen: false,
      newEventDialogOpen: false,

      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      openRightPanel: (content, id) => set({ rightPanelOpen: true, rightPanelContent: content, rightPanelId: id }),
      closeRightPanel: () => set({ rightPanelOpen: false, rightPanelContent: null, rightPanelId: null }),
      toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
      openNewTaskDialog: () => set({ newTaskDialogOpen: true }),
      closeNewTaskDialog: () => set({ newTaskDialogOpen: false }),
    }),
    {
      name: 'life-planner-ui',
      partialize: (state) => ({ sidebarCollapsed: state.sidebarCollapsed }),
    }
  )
);
```

---

## 8. Keyboard Shortcuts

Power users love keyboard shortcuts. Make the app fully navigable without a mouse.

```typescript
// Global shortcuts
const globalShortcuts = {
  'mod+k': 'Open command palette',
  'mod+/': 'Show keyboard shortcuts',
  'mod+n': 'New task',
  'mod+shift+n': 'New note',
  'mod+e': 'New event',
  'mod+shift+g': 'New goal',

  // Navigation
  'g h': 'Go to dashboard (home)',
  'g t': 'Go to tasks',
  'g c': 'Go to calendar',
  'g n': 'Go to notes',
  'g g': 'Go to goals',
  'g p': 'Go to projects',
  'g s': 'Go to settings',

  // Task list shortcuts (when on tasks page)
  'j': 'Move down',
  'k': 'Move up',
  'x': 'Toggle select',
  'e': 'Edit selected',
  'd': 'Mark done',
  'Escape': 'Clear selection',

  // Quick actions
  '/': 'Focus search',
  'c': 'Quick capture (anywhere)',
};
```

---

## 9. Mobile Considerations

While desktop-first, the layout should be responsive:

```typescript
// Responsive breakpoints
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet portrait
  lg: '1024px',  // Tablet landscape / small desktop
  xl: '1280px',  // Desktop
  '2xl': '1536px', // Large desktop
};

// Mobile adaptations:
// - Sidebar becomes bottom nav or hamburger menu
// - Right panel becomes full-screen modal
// - Command palette optimized for touch
// - Larger touch targets (44px minimum)
// - Swipe gestures for common actions
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Working app shell with routing and basic components

**Deliverables:**
- [ ] Project setup (Vite + React + TypeScript + Tailwind)
- [ ] Design system: colors, typography, base components
- [ ] App shell: sidebar, header, main content area
- [ ] Routing setup with React Router
- [ ] API client configuration
- [ ] Base UI components: Button, Input, Card, Badge, Dialog

**Success Criteria:**
- Can navigate between empty pages
- Design system applied consistently
- API client ready for integration

### Phase 2: Dashboard (Week 2-3)

**Goal:** Functional "Today" view

**Deliverables:**
- [ ] Dashboard page layout
- [ ] Stats cards component
- [ ] Priority task list with status indicators
- [ ] Upcoming events timeline
- [ ] Goal progress summaries
- [ ] Quick capture input
- [ ] Dashboard API integration

**Success Criteria:**
- Dashboard shows real data from backend
- Quick capture creates real tasks
- Real-time feel with optimistic updates

### Phase 3: Tasks (Week 3-4)

**Goal:** Full task management functionality

**Deliverables:**
- [ ] Task list page with filtering
- [ ] Task detail panel/page
- [ ] Task creation form with NL parsing preview
- [ ] Task editing
- [ ] Status transitions
- [ ] Priority management
- [ ] Search functionality
- [ ] Bulk operations

**Success Criteria:**
- Can CRUD tasks from UI
- Natural language parsing works
- Filters and search functional

### Phase 4: Calendar (Week 4-5)

**Goal:** Calendar view with event management

**Deliverables:**
- [ ] Week view calendar grid
- [ ] Day view
- [ ] Month view
- [ ] Event creation (click-drag)
- [ ] Event editing
- [ ] Time block visualization
- [ ] Google Calendar sync status

**Success Criteria:**
- Can view and manage events
- Visual clarity for busy schedules
- Synced events display correctly

### Phase 5: Notes (Week 5-6)

**Goal:** Knowledge management with PKM features

**Deliverables:**
- [ ] Note list with sidebar
- [ ] Markdown editor with Tiptap
- [ ] Live preview
- [ ] Wikilink support [[note]]
- [ ] Backlinks panel
- [ ] Tag management
- [ ] Full-text search

**Success Criteria:**
- Can create and edit markdown notes
- Bidirectional links functional
- Search across note content works

### Phase 6: Goals (Week 6-7)

**Goal:** Goal tracking with progress visualization

**Deliverables:**
- [ ] Goals list page
- [ ] Goal detail view
- [ ] Progress bar visualizations
- [ ] Key results/milestone tracking
- [ ] Progress logging
- [ ] Goal creation form

**Success Criteria:**
- Can create and track goals
- Progress updates reflected visually
- Milestones manageable

### Phase 7: Polish & Power Features (Week 7-8)

**Goal:** Power user features and refinement

**Deliverables:**
- [ ] Command palette (⌘K)
- [ ] Keyboard shortcuts throughout
- [ ] Toast notifications
- [ ] Loading states and skeletons
- [ ] Error boundaries and handling
- [ ] Settings page
- [ ] Performance optimization

**Success Criteria:**
- App feels snappy and professional
- Keyboard-navigable throughout
- Error handling graceful

### Phase 8: Integration & Testing (Week 8-9)

**Goal:** Production readiness

**Deliverables:**
- [ ] E2E tests with Playwright
- [ ] Unit tests for critical paths
- [ ] Accessibility audit (a11y)
- [ ] Performance audit (Lighthouse)
- [ ] Bug fixes from testing
- [ ] Documentation

**Success Criteria:**
- Tests passing
- Lighthouse score > 90
- WCAG 2.1 AA compliant

---

## 11. File Structure for Initial Setup

```bash
# Initialize project
npm create vite@latest frontend -- --template react-ts
cd frontend

# Core dependencies
npm install react-router-dom @tanstack/react-query zustand
npm install react-hook-form @hookform/resolvers zod
npm install framer-motion lucide-react date-fns
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install @radix-ui/react-popover @radix-ui/react-tooltip
npm install @radix-ui/react-checkbox @radix-ui/react-select
npm install @radix-ui/react-switch @radix-ui/react-tabs
npm install cmdk react-hot-toast
npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-link
npm install axios nuqs react-hotkeys-hook  # Added missing deps

# Styling
npm install -D tailwindcss postcss autoprefixer
npm install tailwind-merge clsx

# Charts
npm install recharts

# Dev dependencies
npm install -D @types/node
npm install -D eslint @typescript-eslint/eslint-plugin
npm install -D prettier prettier-plugin-tailwindcss
```

---

## 12. Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | React 19 + Vite | Fast dev, modern features, large ecosystem |
| **Styling** | Tailwind CSS | Utility-first, design system as code |
| **State** | TanStack Query + Zustand | Server state separated from UI state |
| **Routing** | React Router 7 | Industry standard, data loading patterns |
| **Forms** | React Hook Form + Zod | Performant, type-safe validation |
| **Components** | Radix UI primitives | Accessible foundation, unstyled |
| **Icons** | Lucide | Clean, consistent, open source |
| **Editor** | Tiptap | Modern, extensible, great DX |
| **Animations** | Framer Motion | Declarative, powerful |
| **Dark Theme** | Pure dark (no light mode) | Focused aesthetic, faster to build |

---

## 13. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Backend API doesn't exist yet** | Build API layer with mock data first, switch to real endpoints later |
| **Scope creep** | Strict phase deliverables, MVP mindset |
| **Performance with large datasets** | Virtual lists, pagination, React Query caching |
| **Accessibility gaps** | Use Radix primitives, run axe-core in CI |
| **Mobile experience** | Responsive from start, but desktop-first priority |

---

## Change Log

| Timestamp | Change | Details |
|-----------|--------|---------|
| 12/30/2025 05:21 AM PST | Initial plan created | Comprehensive frontend architecture document |
| 12/30/2025 05:29 AM PST (via pst-timestamp) | Plan reviewed, deps fixed | Added missing deps (axios, nuqs, react-hotkeys-hook), added more Radix primitives. Starting parallel implementation. |
| 12/30/2025 05:46 AM PST (via pst-timestamp) | **Phase 1 Complete** | Built 60+ components: UI primitives (Button, Input, Card, Badge, Dialog, Dropdown, Tooltip, Avatar, Skeleton), layout (AppShell, Sidebar, Header, RightPanel, CommandPalette), task components (TaskCard, PriorityBadge, StatusBadge), dashboard (StatsCard, QuickCapture), API layer with mock data, React Query hooks, Zustand stores, all pages (Dashboard, Tasks, Calendar, Notes, Goals, Projects, Settings). App builds and runs successfully. |
| 12/30/2025 06:08 AM PST (via pst-timestamp) | **Backend API Complete** | Created FastAPI backend wrapping agent layer: `/backend/` with main.py, schemas.py, dependencies.py, routers for tasks, calendar, notes, goals, dashboard, NLP. Updated frontend to use real API (USE_REAL_API=true). Vite proxy configured. All endpoints tested: tasks (7), notes (3), NLP working. Dashboard has minor timezone bug (TODO). |

---

## Next Steps

1. **Fix dashboard timezone bug** - DashboardAggregator datetime offset issue
2. **Implement command palette** - Complete the cmdk integration for ⌘K navigation
3. **Add keyboard shortcuts** - Wire up navigation and task shortcuts
4. **Build out Tasks page** - TaskList, TaskFilters, TaskForm components
5. **Calendar integration** - Week/Month views with event creation

---

*This plan will evolve as implementation progresses. Update the change log with significant modifications.*
