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
python -c "from src.core import Database, Config; print('✓ Core modules loaded successfully')"
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

**Current Phase**: Core Infrastructure (MVP)

Completed:
- ✅ Project structure
- ✅ Database schema and initialization
- ✅ Configuration management
- ✅ Core data models

In Progress:
- 🔨 Basic CRUD operations
- 🔨 Simple CLI interface

Planned:
- Natural language task creation
- Daily dashboard view
- Note capture and search
- Calendar integration

## Usage

(Coming soon - CLI interface under development)

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
