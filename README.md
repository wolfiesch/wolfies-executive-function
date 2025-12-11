# AI Life Planner

An AI-powered personal life planner using Claude Code as the primary interface. Helps manage tasks, projects, notes, and goals across all life domains with natural language interaction.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python scripts/init_db.py
```

This creates the SQLite database with all necessary tables and default PARA categories.

### 3. Verify Installation

```bash
python3 -c "from src.core import Database, Config; print('✓ Core modules loaded successfully')"
```

### 4. Start Using the CLI

```bash
# Add a task
python3 planner.py add "Call John about project" --due tomorrow --priority 4

# View today's tasks
python3 planner.py today

# List all active tasks
python3 planner.py list

# Mark task as done
python3 planner.py done 5

# View statistics
python3 planner.py stats
```

**Tip**: Create an alias for easier usage:
```bash
alias planner="python3 /path/to/LIFE-PLANNER/planner.py"
```

## Project Structure

```
/
├── config/                 # Configuration files (auto-generated)
│   ├── settings.json      # System settings
│   ├── para_categories.json  # PARA method configuration
│   └── preferences.json   # User preferences
├── data/
│   ├── database/          # SQLite database
│   │   └── planner.db
│   ├── notes/             # Markdown notes
│   └── attachments/       # File attachments
├── src/
│   ├── core/              # Core models, database, config
│   ├── agents/            # Specialized agent implementations
│   ├── integrations/      # MCP servers and external integrations
│   └── utils/             # Date utilities, text processing
├── scripts/               # Database initialization, migrations
├── tests/                 # Unit and integration tests
└── Plans/                 # Feature plans and documentation
```

## Core Concepts

### PARA Method

The system uses the PARA organization method:
- **Projects**: Short-term efforts with specific goals
- **Areas**: Long-term responsibilities (Health, Finance, etc.)
- **Resources**: Reference materials and topics of interest
- **Archives**: Inactive items from other categories

### Database Schema

Core tables:
- `para_categories` - PARA organization structure
- `projects` - Active and completed projects
- `tasks` - Hierarchical task management
- `notes` - Personal knowledge management (PKM)
- `calendar_events` - Calendar and scheduling

## Development Status

**Current Phase**: MVP - Minimal Working System ✨

Completed:
- ✅ Project structure
- ✅ Database schema and initialization
- ✅ Configuration management
- ✅ Core data models
- ✅ Basic CRUD operations
- ✅ **CLI interface with 5 commands**

**Ready to use!** The system is now functional for daily task management.

Planned:
- Enhanced natural language parsing for dates/times
- Project management commands
- Note capture and search
- Daily dashboard improvements
- Calendar integration

## CLI Usage

The planner supports the following commands:

### `add` - Create a new task
```bash
python3 planner.py add "Task title" [--due DATE] [--priority 1-5] [--project NAME]

# Examples
python3 planner.py add "Review proposal"
python3 planner.py add "Call client" --due tomorrow --priority 5
python3 planner.py add "Write tests" -d monday -p 4
```

**Supported date formats**: `today`, `tomorrow`, `monday`, `tuesday`, etc.

### `today` - View today's schedule
```bash
python3 planner.py today
```

Shows tasks due today, overdue tasks, and high-priority items.

### `list` - List all tasks
```bash
python3 planner.py list [--status STATUS] [--project NAME] [--all]

# Examples
python3 planner.py list                    # Active tasks only
python3 planner.py list --status todo      # Only todo tasks
python3 planner.py list --all              # Including completed
```

### `done` - Mark task as complete
```bash
python3 planner.py done TASK_ID

# Example
python3 planner.py done 5
```

### `stats` - View statistics
```bash
python3 planner.py stats
```

Shows total, completed, and in-progress task counts with completion rate.

## Configuration

After first run, configuration files are created in `config/`:

- `settings.json` - System paths, timezone, date formats
- `para_categories.json` - Life areas and PARA configuration
- `preferences.json` - Daily review times, work hours, notification settings

Edit these files to customize your experience.

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_tasks.py
```

## Privacy & Data

- All data stored locally in SQLite database
- No cloud services required for core functionality
- Full control over your information
- Easy backup (just copy the `data/` directory)

## Documentation

See `Plans/AI_Life_Planner_System_2025-12-06.md` for the comprehensive feature plan and architecture.

## License

(TBD)

---

**Built with Claude Code** - An AI-powered development assistant
