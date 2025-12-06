# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered life planner system designed to serve as a comprehensive daily interface for managing personal, social, and professional life. The system uses Claude Code as the primary agent orchestration layer with specialized sub-agents for different domains.

**Core Philosophy:**
- **Proactive over Reactive**: Anticipate needs rather than just respond to requests
- **Context-Aware**: Maintain deep understanding of user's life, preferences, and patterns
- **Frictionless Capture**: Make it easier to put information in the system than to keep it in your head
- **Privacy-First**: All data stored locally with full user control

## Architecture

### High-Level System Design

The system follows a **sub-agent architecture** pattern:

```
Conversational Agent Core (Claude Code)
    ↓
Master Agent (routes requests to specialized agents)
    ↓
├── Task Agent: Task management and smart scheduling
├── Knowledge Agent: Note-taking and knowledge retrieval
├── Calendar Agent: Event scheduling and time blocking optimization
├── Goal Agent: Progress tracking and motivation
└── Review Agent: Daily/weekly reviews and reflections
    ↓
Data Storage Layer
├── SQLite: Structured data (tasks, events, contacts, metrics)
├── Markdown: Notes, journals, meeting notes (in data/notes/)
├── JSON: Configuration, preferences, templates
└── File System: Documents and attachments
    ↓
Integration Layer (MCP)
├── Calendar APIs (Google Calendar, iCal)
├── Email (Gmail, Outlook)
└── Communication (Slack, Teams)
```

### Data Architecture

**Local-first approach:**
- All user data stored in local SQLite database and markdown files
- No cloud dependencies for core functionality
- External integrations are optional and user-controlled

**Key data models:**
- **Tasks**: Hierarchical (projects → tasks → subtasks) with smart scheduling metadata
- **Calendar Events**: Multi-source aggregation with time-blocking capabilities
- **Notes**: Markdown-based with bi-directional linking (PKM system)
- **Goals**: OKR-style with milestones and progress tracking
- **Memories**: Long-term preferences, patterns, and contextual information
- **Contacts**: CRM-lite for relationship management

### Directory Structure (Once Implemented)

```
/
├── Plans/                      # Feature plans and project documentation
├── config/                     # User settings and preferences (JSON)
├── data/
│   ├── database/              # SQLite database
│   ├── notes/                 # Markdown notes and journals
│   └── attachments/           # File attachments
├── src/
│   ├── core/                  # Core models, database, config
│   ├── agents/                # Specialized agent implementations
│   ├── integrations/          # MCP servers and external integrations
│   ├── analytics/             # Reports, patterns, visualizations
│   └── utils/                 # Date utilities, text processing
├── scripts/                   # Database initialization, migrations
└── tests/                     # Unit and integration tests
```

## Development Workflow

### Working with Plans

Active feature plans are stored in `Plans/` directory with naming convention:
- Format: `Feature_Name_YYYY-MM-DD.md`
- Each plan includes implementation steps, database schemas, and success criteria
- **Update the Change Log section** as you complete tasks with timestamps

To execute a plan:
```bash
/runplan   # If you have this custom command configured
```

Or manually reference the plan and work through implementation steps sequentially.

### Database Management

**Initial Setup:**
```bash
python scripts/init_db.py    # Create database with schema
```

**Migrations:**
- Create migration scripts in `scripts/migrations/`
- Always test migrations with sample data first
- Maintain backwards compatibility where possible

**Schema Philosophy:**
- Use UTC timestamps for all datetime fields
- Store complex data as JSON in `metadata` fields when appropriate
- Create indexes on frequently queried fields (status, due_date, priority)

### Agent Development

When creating new agents:
1. Inherit from base agent class in `src/agents/base_agent.py`
2. Implement domain-specific logic and conversation handling
3. Ensure agents can communicate and hand off to other agents
4. Store agent state in database or context as needed

**Key considerations:**
- Agents should be single-purpose and focused
- Use master agent for routing complex multi-domain requests
- Share context efficiently between agents
- Implement graceful handoffs and error handling

### Natural Language Processing

The system relies heavily on natural language understanding:
- Task creation: "Remind me to call John tomorrow at 2pm"
- Scheduling: "Block 2 hours for deep work this week"
- Queries: "What's on my plate for this week?"

**Best practices:**
- Use context and memory to disambiguate vague requests
- Confirm interpretations for important actions
- Learn from corrections and store preferences

### Testing

Run tests with:
```bash
pytest tests/                    # All tests
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/unit/test_tasks.py # Specific test file
```

**Testing priorities:**
- Unit test all scheduling and date/time logic
- Mock external integrations in tests
- Test agent coordination workflows end-to-end
- Validate database constraints and migrations

## Key Design Decisions

### Why Local-First?
Privacy and user control are paramount. Users should own their data and the system should work offline. Cloud sync is optional, not required.

### Why SQLite?
Simplicity and zero configuration. SQLite handles the expected data volume easily and keeps deployment simple. Migration path to PostgreSQL exists if needed for multi-user scenarios.

### Why Markdown for Notes?
Human-readable, version-controllable, portable, and works with existing tools. Users can edit notes in any editor and the system still functions.

### Why Sub-Agents?
Specialized agents provide better context management and more focused capabilities. The master agent routes requests to appropriate domain experts, similar to how a chief of staff delegates to department heads.

## Integration Guidelines

### MCP Server Development

When building MCP integrations:
1. Create server in `src/integrations/mcp_servers/`
2. Follow MCP protocol specifications
3. Handle authentication securely (never commit credentials)
4. Implement bi-directional sync where appropriate
5. Provide fallback for when external service is unavailable

### External Calendar Sync

**Critical considerations:**
- Time zone handling (store UTC, display local)
- Conflict resolution strategies
- Respect user's sync direction preferences
- Handle recurring events properly
- Don't create sync loops

## Project-Specific Conventions

### Task Status Values
Use: `todo`, `in_progress`, `waiting`, `done`, `cancelled`

### Priority Levels
1-5 scale where:
- 5 = Critical/Urgent
- 3 = Normal
- 1 = Low priority

### Life Areas
Categorize all tasks, goals, and notes by life area:
- personal, professional, health, finance, relationships, learning, etc.
- Defined in `config/life_areas.json`

### Timestamp Format
All timestamps stored as ISO 8601 in UTC:
```python
datetime.utcnow().isoformat()  # "2025-12-06T15:37:00.123456"
```

## Proactive Features

The system should be **proactive**, not just reactive:

**Morning Routine:**
- Review today's schedule and tasks
- Surface important deadlines
- Suggest priorities for the day

**Throughout the Day:**
- Time block reminders
- Schedule optimization suggestions
- Relationship follow-up prompts

**Evening Review:**
- Log completed tasks
- Update progress on goals
- Prompt for journal entry
- Plan tomorrow

**Weekly/Monthly:**
- Progress review on goals
- Pattern insights and analytics
- Relationship check-ins
- Life area balance assessment

## Reference Documentation

Comprehensive planning document: `Plans/AI_Life_Planner_System_2025-12-06.md`

This plan includes:
- Complete feature requirements (T0/T1/T2 prioritization)
- Detailed database schemas for all entities
- 12-week phased implementation roadmap
- Testing strategies and success criteria
- Research references from leading 2025 AI systems
