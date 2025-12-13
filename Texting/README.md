# iMessage MCP Integration for Life Planner

A personalized iMessage MCP (Model Context Protocol) server that integrates deeply with the AI Life Planner system.

## Features

- 🎯 **Context-Aware Messaging**: Drafts messages using full life planner context (notes, tasks, calendar)
- 🧠 **Style Personalization**: Learns your texting style and adapts per contact
- 📊 **CRM Integration**: Auto-logs all interactions to relationship database
- 🔍 **Smart Contact Lookup**: Name-based lookup with fuzzy matching
- 🤝 **Proactive Follow-ups**: Suggests contacts that need attention
- 📅 **Calendar Integration**: Schedule meetings via text with availability checking

## Project Status

**Current Sprint:** Sprint 1 - Core MCP Server & Basic Messaging
**Progress:** 0% (just started)

See `Plans/iMessage_MCP_Integration_2025-12-12.md` for detailed roadmap.

## Quick Start

### Prerequisites

- macOS (required for iMessage integration)
- Python 3.9+
- iMessage configured and working
- Life Planner database set up (`../data/database/planner.db`)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup script (creates config files)
python scripts/setup.sh

# Start MCP server
python mcp_server/server.py
```

### Configuration

1. Grant **Full Disk Access** permission:
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal.app or your Python interpreter

2. Configure contacts (initially manual, auto-sync in Sprint 2):
   - Edit `config/contacts.json`

3. Register MCP server with Claude Code:
   - Add to Claude Code MCP configuration

## Usage Examples

Once Sprint 1 is complete:

```
User: "Send a message to Sarah saying I'm running late"
Claude: [Uses send_message MCP tool]
→ Message sent to Sarah: "Hey! Running about 10 minutes late, see you soon!"
```

After Sprint 3 (style learning):
```
User: "Draft a message to Mike about grabbing coffee"
Claude: [Uses draft_contextual_message with your learned style]
→ "Hey Mike - would love to catch up. Free for coffee Thu 2pm or Fri 10am?"
[Tone matches your style, references calendar availability]
```

## Project Structure

```
Texting/
├── Plans/                      # Planning documents
├── mcp_server/                 # MCP server implementation
│   ├── server.py              # Main server
│   └── tools.py               # Tool definitions
├── src/                        # Core components
│   ├── messages_interface.py  # macOS Messages integration
│   ├── contacts_sync.py       # Contact management
│   ├── style_analyzer.py      # Style learning
│   └── message_composer.py    # Context-aware drafting
├── config/                     # Configuration files
├── tests/                      # Test suite
└── scripts/                    # Utility scripts
```

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_messages_interface.py -v

# With coverage
pytest --cov=src tests/
```

### Contributing

See `.claude/CLAUDE.md` for development guidelines and sprint-specific instructions.

## Documentation

- **Master Plan**: `Plans/iMessage_MCP_Integration_2025-12-12.md`
- **Development Guide**: `.claude/CLAUDE.md`
- **Architecture**: [Coming in Sprint 5]
- **API Reference**: [Coming in Sprint 5]

## License

Part of the AI Life Planner system - Private project

## Roadmap

- [x] Sprint 0: Planning & Documentation
- [ ] Sprint 1: Core MCP Server & Basic Messaging (Week 1) **← Current**
- [ ] Sprint 2: Contact Intelligence & Sync (Week 2)
- [ ] Sprint 3: Style Learning & Personalization (Week 3)
- [ ] Sprint 4: Context Integration & Intelligence (Week 4)
- [ ] Sprint 5: Polish, Testing & Documentation (Week 5)

---

*Last Updated: 12/12/2025*
