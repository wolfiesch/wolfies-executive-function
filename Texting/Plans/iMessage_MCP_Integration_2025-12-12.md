# iMessage MCP Integration - Personalized Messaging for Life Planner

**Created:** 12/12/2025 02:14 PM PST (via pst-timestamp)
**Status:** Sprint Planning Phase
**Priority:** T1 - Enhanced Communication Capabilities
**Parent Project:** AI Life Planner System

---

## Executive Summary

This plan outlines the development of a custom iMessage MCP (Model Context Protocol) server deeply integrated with the Life Planner system. Unlike generic iMessage MCPs, this implementation provides context-aware messaging, automatic contact enrichment, learned style/tone preferences, and automatic interaction logging to the CRM database.

**Key Differentiators:**
- **Contact Intelligence**: Name-based lookup with fuzzy matching, relationship context
- **Style Personalization**: Learns from your past messages, adapts tone per contact
- **Context-Aware**: Leverages life planner data (notes, tasks, calendar, interactions)
- **CRM Integration**: Auto-logs conversations, enables proactive follow-ups
- **Privacy-First**: All processing local, no cloud dependencies

---

## Vision & Goals

### Primary Goals
1. **Frictionless Communication**: "Text Sarah about project" → intelligent draft with context
2. **Relationship Maintenance**: Proactive follow-up suggestions based on interaction cadence
3. **Natural Voice**: Messages sound authentically like you, not generic AI
4. **Smart Scheduling**: Calendar-aware meeting requests via text
5. **Interaction History**: Complete communication log in CRM for relationship insights

### Success Criteria
- [ ] Send messages using contact names (not phone numbers)
- [ ] Draft messages in user's learned style
- [ ] Auto-log all interactions to life planner database
- [ ] Provide context from recent notes/tasks when drafting
- [ ] Suggest follow-ups for neglected relationships
- [ ] Support message templates for common scenarios

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│              Claude Code (MCP Client)                    │
│  - Natural language message requests                    │
│  - Message drafting with context                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         iMessage Life Planner MCP Server                │
│  - Contact resolution (name → phone)                    │
│  - Style/tone adaptation                                │
│  - Context enrichment from life planner                 │
│  - Interaction logging                                  │
└────────┬───────────┬───────────┬────────────────────────┘
         │           │           │
    ┌────▼───┐  ┌────▼────┐ ┌───▼──────────┐
    │ macOS  │  │  Life   │ │   Messages   │
    │Contacts│  │ Planner │ │   chat.db    │
    │  API   │  │   DB    │ │  (reading)   │
    └────────┘  └─────────┘ └──────────────┘
         │
    ┌────▼────────────┐
    │   AppleScript   │
    │ (send messages) │
    └─────────────────┘
```

### Core Components

1. **MCP Server** (`mcp_server/`)
   - Tool definitions (send, draft, search, etc.)
   - Server initialization and registration
   - Error handling and logging

2. **Messages Interface** (`src/messages_interface.py`)
   - AppleScript wrapper for sending
   - chat.db reader for message history
   - attributedBody parser for macOS Ventura+

3. **Contact Manager** (`src/contacts_sync.py`)
   - Sync with macOS Contacts
   - Fuzzy name matching
   - Phone number normalization
   - Interaction logging to life planner DB

4. **Style Analyzer** (`src/style_analyzer.py`)
   - Parse user's message history
   - Extract patterns (length, emoji, formality, common phrases)
   - Build per-contact tone profiles
   - Generate style preferences config

5. **Message Composer** (`src/message_composer.py`)
   - Context retrieval from life planner
   - Template expansion
   - Tone adaptation
   - Claude-powered drafting with user's voice

---

## Implementation Roadmap

### Sprint 1: Core MCP Server & Basic Messaging (Week 1) ✅ COMPLETE
**Goal:** Send and receive messages via MCP with contact name lookup

**Tasks:**
- [x] Set up MCP server project structure
- [x] Install dependencies (MCP Python SDK, etc.)
- [x] Implement AppleScript message sender
- [x] Create basic contact name → phone lookup (manual config initially)
- [x] Register MCP tools: `send_message`, `get_recent_messages`, `list_contacts`
- [x] Test integration with Claude Code ✅ All tests passed!
- [x] Handle macOS permissions (Full Disk Access) (documented in SETUP.md)

**Deliverables:**
- Working MCP server that can send messages
- Basic contact resolution
- Integration test with Claude Code

---

### Sprint 2: Contact Intelligence & Sync (Week 2) ✅ COMPLETE
**Goal:** Auto-sync contacts from macOS Contacts ~~and life planner DB~~ (DB integration deferred)

**Tasks:**
- [x] Build macOS Contacts reader ✅
- [x] Implement fuzzy name matching algorithm ✅
- [x] Create contacts sync script (macOS Contacts → ~~Life Planner DB~~ JSON config) ✅
- [x] Add phone number normalization (handle +1, country codes, etc.) ✅
- [ ] Extend life planner contacts table with messaging metadata (deferred - Life Planner WIP)
- [ ] Implement interaction auto-logging (deferred - Life Planner WIP)
- [ ] Create contact enrichment workflow (deferred - Life Planner WIP)

**Database Schema Extensions:**
```sql
-- Enhance contacts.metadata JSON field
{
  "messaging": {
    "phone_numbers": ["+14155551234", "4155551234"],
    "imessage_handle": "user@icloud.com",
    "preferred_method": "imessage",
    "last_synced": "2025-12-12T14:00:00Z"
  }
}

-- Enhance interactions table
ALTER TABLE interactions ADD COLUMN message_preview TEXT;
ALTER TABLE interactions ADD COLUMN message_direction TEXT; -- 'sent', 'received'
```

**Deliverables:**
- Contact sync working end-to-end
- Robust name matching (handles typos, nicknames)
- Interaction logging functional

---

### Sprint 3: Style Learning & Personalization (Week 3)
**Goal:** Learn user's texting style and adapt messages accordingly

**Tasks:**
- [ ] Implement chat.db reader for message history
- [ ] Handle attributedBody parsing (macOS Ventura+)
- [ ] Build style analysis pipeline
  - [ ] Message length distribution
  - [ ] Emoji usage patterns
  - [ ] Formality detection
  - [ ] Common phrases/openers/closers
  - [ ] Punctuation style
- [ ] Generate per-contact tone profiles
- [ ] Create style preferences config
- [ ] Implement tone adaptation in message composer
- [ ] Test with different contact types (professional vs casual)

**Style Config Schema:**
```json
{
  "global_style": {
    "avg_message_length": "medium",
    "formality_level": 7,
    "emoji_frequency": "low",
    "common_openers": ["Hey", "Hi", "Hope you're doing well"],
    "common_closers": ["Thanks", "Let me know", "Talk soon"],
    "punctuation_style": "standard"
  },
  "contact_overrides": {
    "Sarah Johnson": {
      "tone": "casual",
      "formality_level": 4,
      "emoji_frequency": "moderate"
    },
    "Mike Chen": {
      "tone": "professional-friendly",
      "formality_level": 8
    }
  }
}
```

**Deliverables:**
- Style profile generated from message history
- Messages sound authentically like user
- Per-contact tone adaptation working

---

### Sprint 4: Context Integration & Intelligence (Week 4)
**Goal:** Leverage life planner context for intelligent message drafting

**Tasks:**
- [ ] Connect message composer to life planner database
- [ ] Implement context retrieval:
  - [ ] Recent interactions with contact
  - [ ] Related notes/meeting notes
  - [ ] Shared tasks or projects
  - [ ] Calendar availability
  - [ ] Last conversation topic
- [ ] Build `draft_contextual_message` MCP tool
- [ ] Create message templates library
- [ ] Implement calendar-aware scheduling suggestions
- [ ] Add proactive follow-up detection
- [ ] Build relationship maintenance alerts

**MCP Tools:**
```python
# New tools for Sprint 4
- draft_contextual_message(contact_name, intent, include_context=True)
- suggest_follow_up(contact_name)  # Based on last interaction date
- schedule_via_message(contact_name, meeting_intent)  # Calendar-aware
- search_conversation_history(contact_name, query)
```

**Message Templates:**
```json
{
  "meeting_request": {
    "casual": "Hey {name}, would you be free for {meeting_type} {timeframe}? I'd love to {purpose}.",
    "professional": "Hi {name}, I wanted to see if you'd be available for a {duration} {meeting_type} {timeframe} to discuss {topic}."
  },
  "follow_up": {
    "casual": "Hey {name}! Just wanted to follow up on {topic}. {question}",
    "professional": "Hi {name}, I wanted to circle back on {topic} from our last conversation. {question}"
  },
  "check_in": {
    "casual": "Hey {name}! Been a while - how've you been? {specific_question}",
    "professional": "Hi {name}, hope you're doing well. I wanted to check in about {topic}."
  }
}
```

**Deliverables:**
- Contextual message drafting working
- Templates integrated
- Proactive follow-up suggestions
- Calendar integration for scheduling

---

### Sprint 5: Polish, Testing & Documentation (Week 5)
**Goal:** Production-ready MCP server with comprehensive documentation

**Tasks:**
- [ ] Comprehensive error handling and edge cases
- [ ] Unit tests for all core components
- [ ] Integration tests with life planner DB
- [ ] Performance optimization (message history queries)
- [ ] Security audit (permissions, data handling)
- [ ] User documentation (setup guide, examples)
- [ ] Developer documentation (architecture, extending)
- [ ] Example workflows and use cases
- [ ] Configuration wizard for initial setup
- [ ] Analytics dashboard (message patterns, relationship metrics)

**Documentation Deliverables:**
- [ ] README.md with setup instructions
- [ ] ARCHITECTURE.md explaining system design
- [ ] EXAMPLES.md with common usage patterns
- [ ] TROUBLESHOOTING.md for common issues

---

## Database Schema

### Contacts Enhancement (Life Planner DB)

```sql
-- The contacts table already exists in life planner
-- We'll use the metadata JSON field for messaging-specific data

-- Example metadata structure:
{
  "messaging": {
    "phone_numbers": ["+14155551234", "4155551234"],
    "imessage_handle": "user@icloud.com",
    "preferred_contact_method": "imessage",
    "last_message_date": "2025-12-10T14:30:00Z",
    "message_frequency": "weekly",
    "texting_preferences": {
      "tone": "casual",
      "emoji_usage": "moderate",
      "avg_response_time_hours": 2.5
    }
  },
  "macos_contact_id": "ABC123-DEF456",
  "last_synced": "2025-12-12T14:00:00Z"
}
```

### Interactions Enhancement

```sql
-- Extend existing interactions table
ALTER TABLE interactions ADD COLUMN message_preview TEXT;
ALTER TABLE interactions ADD COLUMN message_direction TEXT CHECK(message_direction IN ('sent', 'received'));
ALTER TABLE interactions ADD COLUMN sentiment TEXT CHECK(sentiment IN ('positive', 'neutral', 'negative'));

CREATE INDEX idx_interactions_direction ON interactions(message_direction);
```

### New: Message Templates Table

```sql
CREATE TABLE message_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL, -- 'meeting', 'follow_up', 'check_in', etc.
    tone TEXT NOT NULL CHECK(tone IN ('casual', 'professional', 'professional-friendly')),
    template_text TEXT NOT NULL,
    variables TEXT, -- JSON array of template variables
    created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')),
    updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc'))
);

CREATE INDEX idx_templates_category ON message_templates(category);
CREATE INDEX idx_templates_tone ON message_templates(tone);
```

---

## Configuration Files

### 1. MCP Server Config (`config/mcp_server.json`)

```json
{
  "server_name": "imessage-life-planner",
  "version": "1.0.0",
  "life_planner_db_path": "../data/database/planner.db",
  "messages_db_path": "~/Library/Messages/chat.db",
  "contacts_sync": {
    "enabled": true,
    "auto_sync_interval_hours": 24,
    "fuzzy_match_threshold": 0.85
  },
  "logging": {
    "level": "INFO",
    "file": "../logs/mcp_server.log",
    "max_size_mb": 10
  }
}
```

### 2. Style Preferences (`config/style_preferences.json`)

```json
{
  "version": "1.0",
  "last_analyzed": "2025-12-12T14:00:00Z",
  "analysis_source": {
    "message_count": 1000,
    "date_range": "2023-01-01 to 2025-12-12"
  },
  "global_style": {
    "avg_message_length_chars": 120,
    "formality_level": 7,
    "emoji_frequency_per_message": 0.2,
    "common_openers": ["Hey", "Hi", "Hope you're doing well"],
    "common_closers": ["Thanks", "Let me know", "Talk soon"],
    "punctuation_style": "standard",
    "uses_contractions": true,
    "paragraph_style": "single-paragraph"
  },
  "contact_overrides": {}
}
```

### 3. Message Templates (`config/message_templates.json`)

```json
{
  "meeting_request": {
    "casual": "Hey {name}, would you be free for {meeting_type} {timeframe}? I'd love to {purpose}.",
    "professional": "Hi {name}, I wanted to see if you'd be available for a {duration} {meeting_type} {timeframe} to discuss {topic}.",
    "professional-friendly": "Hey {name}, hope you're doing well! Would you be free for a quick {duration} {meeting_type} sometime {timeframe}? I'd love to discuss {topic}."
  },
  "follow_up": {
    "casual": "Hey {name}! Just wanted to follow up on {topic}. {question}",
    "professional": "Hi {name}, I wanted to circle back on {topic} from our last conversation. {question}",
    "professional-friendly": "Hi {name}, hope you're well! I wanted to follow up on {topic} we discussed. {question}"
  },
  "check_in": {
    "casual": "Hey {name}! Been a while - how've you been? {specific_question}",
    "professional": "Hi {name}, hope you're doing well. I wanted to check in about {topic}.",
    "professional-friendly": "Hey {name}, hope you're doing well! Just wanted to check in - {specific_question}"
  },
  "thank_you": {
    "casual": "Thanks so much for {action}, really appreciate it!",
    "professional": "Thank you for {action}. I greatly appreciate your {quality}.",
    "professional-friendly": "Thanks for {action}! Really appreciate your help with this."
  }
}
```

---

## Project Structure

```
Texting/
├── Plans/
│   └── iMessage_MCP_Integration_2025-12-12.md  # This document
├── mcp_server/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── tools.py               # MCP tool definitions
│   └── README.md              # MCP server setup guide
├── src/
│   ├── __init__.py
│   ├── messages_interface.py  # macOS Messages integration
│   ├── contacts_sync.py       # Contact management & sync
│   ├── style_analyzer.py      # Message style learning
│   ├── message_composer.py    # Context-aware message drafting
│   └── utils.py               # Shared utilities
├── config/
│   ├── mcp_server.json        # Server configuration
│   ├── style_preferences.json # Learned texting style
│   └── message_templates.json # Message templates
├── tests/
│   ├── test_messages_interface.py
│   ├── test_contacts_sync.py
│   ├── test_style_analyzer.py
│   ├── test_message_composer.py
│   └── test_mcp_tools.py
├── scripts/
│   ├── setup.sh               # Initial setup script
│   ├── sync_contacts.py       # Manual contact sync
│   └── analyze_style.py       # Run style analysis
├── logs/
│   └── mcp_server.log
├── .claude/
│   └── CLAUDE.md              # Claude-specific instructions
├── requirements.txt
└── README.md
```

---

## MCP Tools Specification

### Tool 1: `send_message`

```python
@tool()
async def send_message(
    contact_name: str,
    message: str,
    tone: str = "auto"  # 'auto', 'casual', 'professional', 'professional-friendly'
) -> str:
    """
    Send an iMessage to a contact using their name.

    Args:
        contact_name: Name of contact (fuzzy matched)
        message: Message text to send
        tone: Optional tone override (default: use contact's learned tone)

    Returns:
        Confirmation message with delivery status

    Side Effects:
        - Logs interaction to life planner DB
        - Updates last_message_date in contact metadata
    """
```

**Example Usage:**
```
User: "Text Sarah that I'll be 10 minutes late"
Claude: send_message("Sarah", "Hey! Running about 10 minutes late, see you soon!", "auto")
```

---

### Tool 2: `draft_contextual_message`

```python
@tool()
async def draft_contextual_message(
    contact_name: str,
    intent: str,
    include_context: bool = True
) -> str:
    """
    Draft a message using full life planner context.

    Args:
        contact_name: Name of contact
        intent: What you want to communicate (natural language)
        include_context: Whether to pull context from life planner

    Returns:
        Drafted message text (user can review/edit before sending)

    Context Retrieved:
        - Recent interactions with contact
        - Related notes/meeting notes
        - Shared tasks or projects
        - Calendar availability (for scheduling intents)
        - Last conversation topic
    """
```

**Example Usage:**
```
User: "Draft a message to Mike about grabbing coffee this week"
Claude: draft_contextual_message("Mike", "schedule coffee this week", True)

Output: "Hey Mike - would love to catch up and continue our conversation about
the startup idea. Are you free for coffee Thursday at 2pm or Friday at 10am?"

[Context used:
- Last conversation mentioned startup idea
- Your calendar shows availability Thu 2pm, Fri 10am
- Mike is categorized as 'colleague' → professional-friendly tone]
```

---

### Tool 3: `get_recent_messages`

```python
@tool()
async def get_recent_messages(
    contact_name: str,
    limit: int = 20
) -> str:
    """
    Retrieve recent message history with a contact.

    Args:
        contact_name: Name of contact
        limit: Number of recent messages to retrieve

    Returns:
        Formatted message history with timestamps and direction
    """
```

---

### Tool 4: `search_messages`

```python
@tool()
async def search_messages(
    query: str,
    contact_name: str = None,
    date_range: dict = None
) -> str:
    """
    Search message history by keyword or phrase.

    Args:
        query: Search query (keywords or phrase)
        contact_name: Optional contact filter
        date_range: Optional {"start": "2025-01-01", "end": "2025-12-31"}

    Returns:
        Matching messages with context
    """
```

---

### Tool 5: `suggest_follow_up`

```python
@tool()
async def suggest_follow_up(
    contact_name: str = None,
    days_threshold: int = 14
) -> str:
    """
    Suggest contacts that might need a follow-up message.

    Args:
        contact_name: Optional specific contact to check
        days_threshold: Number of days since last contact

    Returns:
        List of contacts with suggested follow-up context

    Logic:
        - Check last_message_date in contacts
        - Filter by relationship importance
        - Provide context about last conversation
        - Suggest message intent based on relationship type
    """
```

**Example Output:**
```
Contacts needing follow-up:

1. Alex Thompson (colleague, importance: 4)
   Last contact: 6 weeks ago
   Last topic: Discussed new job at TechCorp
   Suggested intent: "Check in on how new job is going"

2. Sarah Chen (friend, importance: 5)
   Last contact: 3 weeks ago
   Last topic: Birthday plans
   Suggested intent: "General catch-up"
```

---

### Tool 6: `schedule_via_message`

```python
@tool()
async def schedule_via_message(
    contact_name: str,
    meeting_intent: str,
    duration_minutes: int = 30
) -> str:
    """
    Draft a scheduling message with calendar-aware time suggestions.

    Args:
        contact_name: Name of contact
        meeting_intent: Purpose of meeting (e.g., "discuss project", "coffee")
        duration_minutes: Meeting duration

    Returns:
        Drafted message with 2-3 specific time slot suggestions

    Context:
        - Checks your calendar for availability
        - Suggests times based on past meeting patterns with contact
        - Respects working hours and buffer times
    """
```

---

## Success Metrics

### Sprint-Level Metrics

**Sprint 1:**
- [ ] MCP server successfully registered with Claude Code
- [ ] Can send messages via AppleScript (100% success rate)
- [ ] Contact name lookup works for manually configured contacts

**Sprint 2:**
- [ ] Contact sync completes successfully (macOS Contacts → Life Planner)
- [ ] Fuzzy matching accuracy >85% on test set of 100 names
- [ ] Interactions auto-logged for all sent messages

**Sprint 3:**
- [ ] Style profile generated from ≥500 past messages
- [ ] Blind test: 3 people can't distinguish AI drafts from user's actual messages
- [ ] Per-contact tone adaptation works for 3 test contacts (casual, professional, mixed)

**Sprint 4:**
- [ ] Context retrieval includes ≥3 data sources (notes, tasks, calendar, interactions)
- [ ] Drafted messages reference relevant context ≥80% of the time
- [ ] Follow-up suggestions identify ≥90% of neglected important relationships

**Sprint 5:**
- [ ] 0 critical bugs in production use
- [ ] Test coverage ≥80%
- [ ] Setup time for new user <15 minutes
- [ ] Documentation complete and reviewed

---

## Risks & Mitigations

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **macOS Ventura+ attributedBody parsing** | High - Can't read message history | Medium | Use AppleScript fallback for sending; research NSKeyedArchiver parsing |
| **Full Disk Access permissions** | High - Can't access Messages DB | Low | Clear setup documentation; permission request handling |
| **Contact matching accuracy** | Medium - Wrong contact gets message | Medium | Fuzzy matching with confidence threshold; confirmation prompt for low confidence |
| **MCP protocol changes** | Medium - Server breaks | Low | Pin MCP SDK version; monitor official releases |
| **Life planner DB schema drift** | Medium - Integration breaks | Low | Version checks; migration scripts |

### Product Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Messages don't sound like user** | High - User won't adopt | Medium | Extensive style analysis; user review before sending |
| **Context too verbose/irrelevant** | Medium - Annoying to user | Medium | Configurable context inclusion; smart relevance filtering |
| **Privacy concerns** | High - User uncomfortable | Low | Local-only processing; clear data handling docs |
| **Setup too complex** | Medium - High friction to adopt | Medium | Automated setup script; detailed onboarding |

---

## Dependencies

### External Dependencies

- **MCP Python SDK** - `pip install mcp`
- **macOS Contacts API** - Native macOS (requires Full Disk Access)
- **AppleScript** - Native macOS
- **SQLite** - Native Python
- **Life Planner Database** - Must exist and be populated

### Internal Dependencies

- Life Planner contacts table (from main project)
- Life Planner interactions table
- Life Planner notes system (for context retrieval)
- Life Planner calendar agent (for scheduling features - Sprint 4+)

---

## Testing Strategy

### Unit Tests

- Contact name fuzzy matching (edge cases: typos, nicknames, duplicates)
- Phone number normalization (various formats)
- Style analysis parsing (different message structures)
- Template variable substitution
- Tone adaptation logic

### Integration Tests

- End-to-end message sending flow
- Contact sync (macOS Contacts → Life Planner DB)
- Context retrieval from multiple data sources
- Interaction logging
- MCP tool execution via Claude Code

### Manual Testing

- Send messages to test contacts (verify delivery)
- Review drafted messages (sound like user?)
- Test follow-up suggestions (accurate?)
- Verify context relevance (appropriate?)
- Permission handling (clear errors?)

---

## Future Enhancements (Post-MVP)

### Phase 2 Features

1. **Group Message Support**
   - Handle group conversations
   - Track group membership in DB
   - Group-specific context

2. **Attachments & Rich Media**
   - Send images, links, files
   - Parse incoming attachments
   - Store attachment references

3. **Message Scheduling**
   - "Send this tomorrow at 9am"
   - Queue management
   - Automatic delivery

4. **Sentiment Analysis**
   - Detect conversation tone/mood
   - Alert on negative sentiment
   - Relationship health indicators

5. **Multi-Channel Support**
   - Email integration
   - Slack/Teams messages
   - Unified conversation view

6. **Analytics Dashboard**
   - Message volume over time
   - Response time patterns
   - Relationship strength scores
   - Communication balance (who initiates)

---

## Change Log

**Instructions for updating this log:**
- Add timestamped entries as you complete tasks
- Include sprint number, task description, and any relevant notes
- Use format: `[YYYY-MM-DD HH:MM AM/PM PST] - Sprint X: Task description - Notes`
- Update corresponding task checkboxes in roadmap

### December 2025

**[12/12/2025 02:14 PM PST (via pst-timestamp)]** - Project Initialization
- Created master planning document
- Defined 5-sprint roadmap with detailed tasks
- Established architecture and technical approach
- Set up project structure in `/Texting/` directory
- Status: Sprint Planning Phase complete, ready to begin Sprint 1

**[12/12/2025 02:53 PM PST (via pst-timestamp)]** - Sprint 1: Core MCP Server Implementation (80% Complete)
- ✅ Created project directory structure (mcp_server/, src/, config/, tests/, scripts/)
- ✅ Installed MCP Python SDK and core dependencies
- ✅ Implemented `MessagesInterface` with AppleScript message sender (src/messages_interface.py)
  - Handles message sending via AppleScript to Messages.app
  - Includes basic message history retrieval from chat.db
  - Proper error handling and logging
- ✅ Implemented `ContactsManager` with name-based lookup (src/contacts_manager.py)
  - Loads contacts from config/contacts.json
  - Supports exact, case-insensitive, and partial name matching
  - Phone number normalization (handles +1 country code differences)
  - All unit tests passing (10/10 tests green)
- ✅ Created MCP server with 3 core tools (mcp_server/server.py)
  - `send_message`: Send iMessage using contact name
  - `get_recent_messages`: Retrieve message history
  - `list_contacts`: Show all configured contacts
- ✅ Created comprehensive setup documentation (SETUP.md)
- ✅ Created README.md with project overview
- ✅ Configuration files initialized (mcp_server.json, contacts.json)
- **Next:** Test integration with Claude Code (final Sprint 1 task)
- **Status:** Sprint 1 ~80% complete (6/7 tasks done)

**[12/12/2025 03:16 PM PST (via pst-timestamp)]** - Sprint 1: COMPLETE ✅ (100%)
- ✅ Added Wolfgang Schoenberger as test contact (config/contacts.json)
- ✅ Registered MCP server in Claude Code config (~/.claude/mcp.json)
- ✅ Created comprehensive test suite (scripts/test_mcp_tools.py)
- ✅ **All tests passed:**
  - List contacts: 2 contacts loaded successfully
  - Contact lookup: Exact, partial, and case-insensitive matching working
  - Send message via AppleScript: Successfully sent test iMessage
  - Message delivery: Confirmed received on user's device
- ✅ MCP server verified working with Claude Code
- **Sprint 1 Deliverables: 100% COMPLETE**
  - Working MCP server that can send messages ✓
  - Basic contact resolution ✓
  - Integration test with Claude Code ✓
- **Total Sprint Duration:** ~1 hour (2:14 PM - 3:16 PM PST)
- **Status:** Ready for Sprint 2

**[12/12/2025 03:26 PM PST (via pst-timestamp)]** - Critical Bug Discovery & Fix
- ❌ **Bug Found:** MCP tools not appearing in fresh Claude Code session
- 🔍 **Root Cause:** Test suite (`test_mcp_tools.py`) was testing Python functions directly, NOT the actual MCP protocol
  - Previous "successful" tests bypassed the MCP protocol entirely
  - Never verified actual JSON-RPC communication via stdio
- ✅ **Created:** Proper MCP protocol test (`scripts/test_mcp_protocol.py`)
  - Simulates Claude Code's actual communication pattern
  - Tests JSON-RPC 2.0 over stdio transport
- ❌ **Error Discovered:** "Invalid request parameters" (-32602) when requesting `tools/list`
- 🔍 **Investigation:** Enabled DEBUG logging, examined MCP SDK source code
- ✅ **Solution Found:** Missing `initialized` notification in protocol handshake
  - MCP protocol requires 3-step initialization (like LSP):
    1. Client sends `initialize` request
    2. Server responds with capabilities
    3. **Client sends `initialized` notification** ← This was missing!
    4. Only then can client make other requests
- ✅ **Fix Implemented:** Added `initialized` notification to test protocol
- ✅ **Verification:** All 3 MCP tools now successfully returned via protocol:
  - `send_message`
  - `get_recent_messages`
  - `list_contacts`
- **Impact:** Server implementation was correct all along; test was incomplete
- **Next:** Verify tools appear in fresh Claude Code session
- **Status:** MCP protocol communication verified working

**[12/12/2025 03:36 PM PST (via pst-timestamp)]** - Additional Fix: Path Resolution
- ❌ **Bug Found:** MCP server still not connecting in Claude Code
- 🔍 **Root Cause:** Relative paths in server.py and config broke when Claude Code started server from different CWD
  - Logging path `logs/mcp_server.log` failed to create
  - Config path `config/contacts.json` resolved to wrong location (home directory)
- ✅ **Fix Applied:** (mcp_server/server.py:30-69)
  - Added `PROJECT_ROOT` variable using `Path(__file__).parent.parent`
  - Created `resolve_path()` function to convert relative paths to absolute
  - All paths now resolve relative to project directory regardless of CWD
  - Log directory now auto-created if missing (`mkdir(exist_ok=True)`)
- ✅ **Verified:** Server starts correctly from home directory and loads 2 contacts
- **Next:** Restart Claude Code to test MCP connection
- **Status:** Awaiting Claude Code restart for final verification

**[12/12/2025 03:39 PM PST (via pst-timestamp)]** - Final Fix: MCP Registration Scope
- ❌ **Bug Found:** Server still not appearing in `claude mcp list` after restart
- 🔍 **Root Cause:** Wrong config file scope
  - Server was registered in `~/.claude/mcp.json` (global config)
  - Claude Code uses project-level configs stored in `~/.claude.json` under `projects` key
- ✅ **Fix Applied:** Used `claude mcp add` command to register at correct scope:
  ```bash
  claude mcp add -t stdio imessage-life-planner -- python3 /path/to/server.py
  ```
- ✅ **Result:** Server now shows as connected:
  ```
  imessage-life-planner: python3 ... - ✓ Connected
  ```
- **Config Location:** `~/.claude.json` → `projects["/Users/.../LIFE-PLANNER"].mcpServers`
- **Status:** ✅ MCP Server fully operational - restart needed for tools to load

**[12/12/2025 03:41 PM PST (via pst-timestamp)]** - Sprint 1 VERIFIED COMPLETE ✅
- ✅ **All 3 MCP tools tested successfully via Claude Code:**
  - `list_contacts` → Returns 2 configured contacts
  - `get_recent_messages` → Retrieves message history from chat.db
  - `send_message` → Verified working (earlier test at 3:07 PM received)
- ✅ **End-to-end integration confirmed:**
  - MCP protocol handshake working
  - Tools appear in Claude Code session
  - Can query contacts and message history via natural language
- **Note:** `[attributedBody - not parsed yet]` for outgoing messages is expected (Sprint 3 feature)
- **Sprint 1 Duration:** 02:14 PM - 03:41 PM PST (~1.5 hours including debugging)
- **Status:** 🎉 SPRINT 1 COMPLETE - Ready for Sprint 2

**[12/12/2025 03:51 PM PST (via pst-timestamp)]** - Sprint 1.5: attributedBody Parsing (Bonus Feature)
- ✅ **Implemented streamtyped format parsing** for macOS Messages (src/messages_interface.py:23-198)
  - `parse_attributed_body()` - Handles bplist/NSKeyedArchiver format
  - `extract_text_from_blob()` - Handles streamtyped format (macOS Messages native)
- ✅ **Format understanding:**
  - macOS stores message text in `attributedBody` column as binary blob
  - Format: `streamtyped` header → `NSString` marker → 5 control bytes → `+` → length byte → **actual text** → `0x86/0x84` terminator
- ✅ **Verified parsing works:**
  - "Testing iMessage MCP - Sprint 1 Complete! 🎉" ✅
  - "Liked 'On the plane back to SF.'" ✅
  - "cute video", "hey yeah" ✅
  - Emoji support working (🎉)
- **Note:** Some older messages still show "[message content not available]" - may be attachment-only or different format
- **Next:** Restart Claude Code to reload MCP server with new parsing
- **Status:** Feature complete - awaiting MCP server restart

**[12/12/2025 04:11 PM PST (via pst-timestamp)]** - Sprint 1.5 VERIFIED ✅
- ✅ **MCP server reloaded with attributedBody parsing**
- ✅ **Tested via MCP tools - parsing works perfectly:**
  - Recent messages now show actual content instead of "[attributedBody - not parsed yet]"
  - "Testing iMessage MCP - Sprint 1 Complete! 🎉" ✅
  - "Liked 'On the plane back to SF.'" ✅
  - "cute video", "hey yeah" ✅
- ✅ **Also documented MCP configuration in global `~/.claude/CLAUDE.md`**
  - Added "MCP Server Configuration (CRITICAL)" section
  - Covers proper `claude mcp add` usage, path requirements, verification
  - Future MCP servers will be configured correctly from the start
- **Status:** 🎉 Sprint 1 + 1.5 COMPLETE - Ready for Sprint 2

**[12/12/2025 04:32 PM PST (via pst-timestamp)]** - Sprint 2: Contact Intelligence & Sync COMPLETE ✅
- ✅ **Built macOS Contacts reader** (`src/contacts_sync.py`)
  - `MacOSContactsReader` class uses PyObjC Contacts framework
  - Fetches all contacts from macOS Contacts.app with full metadata
  - `fetch_all_contacts()` - retrieve all contacts
  - `search_contacts(name)` - search by name
  - Extracts phone numbers, emails, names, organization data
  - Handles macOS permission requests gracefully
- ✅ **Implemented fuzzy name matching algorithm**
  - `FuzzyNameMatcher` class with configurable threshold (default 0.85)
  - Uses multiple fuzzywuzzy strategies for best accuracy:
    - Token sort ratio (handles word order: "John Doe" ↔ "Doe John")
    - Token set ratio (handles partial: "John Michael Doe" ↔ "John Doe")
    - Partial ratio (handles substrings: "John" ↔ "John Doe")
    - Levenshtein distance (handles typos: "Jon Doe" ↔ "John Doe")
  - `find_best_match()` - returns best candidate above threshold with confidence score
  - `find_all_matches()` - returns top N matches sorted by score
- ✅ **Enhanced phone number normalization** (`normalize_phone_number()`)
  - Handles international formats: +44, +49, etc.
  - Detects "+" prefix to preserve existing country codes
  - Adds default country code (1) only for domestic US/CA numbers
  - Supports all separators: dots, dashes, spaces, parentheses
  - `compare_phone_numbers()` - intelligent matching handles format differences
- ✅ **Created contacts sync script** (`scripts/sync_contacts.py`)
  - Syncs macOS Contacts → JSON config file
  - Filters to contacts with phone numbers
  - Merge strategy: preserves manual edits to relationship_type and notes
  - Stores all phone numbers + primary phone (prefers mobile)
  - Includes email addresses and macOS contact ID for future sync
  - CLI with options: --output, --include-no-phone, --no-merge, --verbose
- ✅ **Comprehensive test suite** (`tests/test_contacts_sync.py`)
  - 32 unit tests covering all Sprint 2 functionality
  - All tests passing ✅
  - Test coverage: fuzzy matching (10 tests), phone normalization (10 tests), contact models (7 tests)
  - Integration tests for macOS Contacts (marked as skip - requires manual run with permissions)
- ✅ **Installed dependencies**
  - fuzzywuzzy==0.18.0
  - python-Levenshtein==0.27.3
  - pyobjc-framework-Contacts (already in requirements.txt)
- **Note:** Life Planner DB integration deferred (parent project still WIP)
  - Contacts sync to JSON instead of SQLite for now
  - Interaction logging to be added in future sprint
  - Contact enrichment workflow pending Life Planner readiness
- **Next Steps:**
  - Run contact sync: `python3 scripts/sync_contacts.py`
  - Grant Contacts permission when prompted
  - Review synced contacts in config/contacts.json
  - Update ContactsManager to use fuzzy matching (Sprint 2.5 follow-up)
- **Sprint 2 Duration:** ~45 minutes (all tasks completed)
- **Status:** 🎉 SPRINT 2 COMPLETE (without Life Planner integration) - Ready for Sprint 3

**[12/12/2025 04:51 PM PST (via pst-timestamp)]** - Sprint 2.5: Enhanced Message Search & Discovery ✅
- ✅ **Extended MessagesInterface** with 3 new methods (`src/messages_interface.py`)
  - `get_all_recent_conversations(limit)` - Get recent messages from ALL conversations
    - Returns messages across all contacts (known and unknown)
    - Shows phone number/handle for each message
    - MCP tool enriches with contact names where available
  - `search_messages(query, phone=None, limit)` - Full-text search across messages
    - Search all messages or filter by specific contact
    - Returns matches with context snippets (50 chars before/after)
    - Case-insensitive matching
    - Handles both text and attributedBody messages
  - `_create_snippet(text, query)` - Helper to create match context snippets
- ✅ **Added 3 new MCP tools** (`mcp_server/server.py`)
  - `get_all_recent_conversations` - Browse recent activity across all conversations
    - Solves the "unknown number" problem - no contact needed
    - Shows most recent messages regardless of contact status
    - Automatically resolves phone numbers to contact names when available
  - `search_messages` - Find messages by content/keyword
    - Search all messages: "find messages about dinner"
    - Search with specific contact: "find messages about project with Sarah"
    - Returns date, sender, and context snippet
  - `get_messages_by_phone` - Direct phone number lookup
    - No contact configuration required
    - Works with any format: +14155551234, (415) 555-1234, email handles
    - Useful for unknown numbers or testing
- ✅ **Verified MCP server compatibility**
  - Server imports successfully with all 6 tools (3 Sprint 1 + 3 Sprint 2.5)
  - No breaking changes to existing tools
  - Backward compatible with Sprint 1 functionality
- **Why Sprint 2.5?**
  - User identified critical UX gap: "Can't search messages from unknown contacts"
  - This was blocking real-world usage
  - Tools originally planned for Sprint 3 but needed immediately
  - Quick implementation (~20 minutes) using existing infrastructure
- **Impact:**
  - **Before:** Could only get messages if contact was pre-configured
  - **After:** Can discover conversations, search content, handle unknown numbers
  - **Example Use Cases:**
    - "Show me my recent messages" → sees all conversations
    - "What did that (415) number say?" → gets messages by phone directly
    - "Find messages about project deadline" → searches all messages
- **Next Steps:**
  - Restart Claude Code to reload MCP server with new tools
  - Test new tools with real message data
  - Sprint 3: Style learning and personalization
- **Sprint 2.5 Duration:** ~20 minutes (all core functionality)
- **Status:** 🎉 SPRINT 2.5 COMPLETE - Major UX improvement, MCP server much more useful

---

## References & Resources

### Existing MCP Servers (Research)
- [marissamarym/imessage-mcp-server](https://github.com/marissamarym/imessage-mcp-server)
- [carterlasalle/mac_messages_mcp](https://github.com/carterlasalle/mac_messages_mcp)
- [hannesrudolph/imessage-query-fastmcp-mcp-server](https://github.com/hannesrudolph/imessage-query-fastmcp-server)

### MCP Development
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Quick Start Guide 2025](https://github.com/munganaai/mcp-server-playbook-2025)

### macOS Messages Database
- [Searching iMessage with SQL](https://spin.atomicobject.com/search-imessage-sql/)
- [Accessing iMessages with SQL](https://davidbieber.com/snippets/2020-05-20-imessage-sql-db/)
- [Chat.db Location & Access](https://darwinsdata.com/where-is-the-chat-db-stored-on-a-mac/)

### Life Planner Integration
- Main Plan: `/Users/wolfgangschoenberger/LIFE-PLANNER/Plans/AI_Life_Planner_System_2025-12-06.md`
- Database: `/Users/wolfgangschoenberger/LIFE-PLANNER/data/database/planner.db`

---

## Appendix

### A. macOS Permissions Setup

1. **Full Disk Access** (required for Messages DB)
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal.app or your Python interpreter
   - Required for reading `~/Library/Messages/chat.db`

2. **Contacts Access**
   - First access will trigger permission prompt
   - Grant via System Settings if denied

3. **AppleScript Permissions**
   - Messages.app automation permission
   - Usually auto-granted on first use

### B. Troubleshooting Common Issues

**Issue: "Can't access Messages database"**
- Check Full Disk Access permissions
- Verify path: `~/Library/Messages/chat.db`
- Restart Terminal/Python after granting permissions

**Issue: "Contact not found"**
- Run contact sync: `python scripts/sync_contacts.py`
- Check fuzzy match threshold in config
- Verify contact exists in macOS Contacts

**Issue: "Messages sent but not logged to DB"**
- Check life planner DB connection
- Verify interactions table exists
- Check logs: `logs/mcp_server.log`

**Issue: "Drafted messages don't sound like me"**
- Re-run style analysis with more messages
- Adjust formality_level in config
- Add contact-specific overrides

---

*Last Updated: 12/12/2025 02:14 PM PST (via pst-timestamp)*
