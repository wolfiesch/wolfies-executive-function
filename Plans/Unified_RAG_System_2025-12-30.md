# Unified RAG System - Multi-Source Knowledge Base

**Created:** 12/30/2024 01:35 PM PST (via pst-timestamp)
**Status:** In Progress

## Overview

Extend the existing iMessage RAG system to index multiple personal data sources into a unified semantic search system. This creates a comprehensive personal knowledge base spanning all communication and documentation.

## Data Sources

| Source | Data Type | Volume | Access Method |
|--------|-----------|--------|---------------|
| **iMessage** | Text conversations | 150k+ messages | SQLite DB (already implemented) |
| **Gmail** | Emails | TBD | Gmail MCP tools |
| **Notes** | Markdown documents | ~20+ files | File system |
| **Calendar** | Events + notes | TBD | Google Calendar API |
| **Slack** | Messages | TBD | Rube MCP (SLACK_*) |
| **SuperWhisper** | Voice transcriptions | 3200+ recordings | JSON files (`~/Documents/superwhisper/recordings/`) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unified RAG System                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  iMessage │ │   Gmail   │ │   Notes   │ │ Calendar  │ ...   │
│  │  Indexer  │ │  Indexer  │ │  Indexer  │ │  Indexer  │       │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘       │
│        │             │             │             │              │
│        v             v             v             v              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Unified Chunker Interface                   │   │
│  │   - Source-specific chunking strategies                  │   │
│  │   - Common metadata schema                               │   │
│  │   - Deduplication via deterministic IDs                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            v                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              EmbeddingProvider (shared)                  │   │
│  │   - OpenAI text-embedding-3-small (1536 dims)           │   │
│  │   - Local fallback: all-MiniLM-L6-v2                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            v                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ChromaDB Collections                        │   │
│  │                                                          │   │
│  │   imessage_chunks    gmail_chunks     notes_chunks       │   │
│  │   calendar_chunks    slack_chunks     superwhisper_chunks│   │
│  │                                                          │   │
│  │   Storage: data/chroma/                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            v                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Unified Retriever                           │   │
│  │   - Cross-collection search                              │   │
│  │   - Source filtering                                     │   │
│  │   - Date range filtering                                 │   │
│  │   - Result ranking and deduplication                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            v                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MCP Tools / API Layer                       │   │
│  │   - index_source(source, options)                        │   │
│  │   - search(query, sources=[], filters={})                │   │
│  │   - get_stats()                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Unified Chunk Schema

All sources produce chunks with this common structure:

```python
@dataclass
class UnifiedChunk:
    # Identity
    chunk_id: str              # SHA256 hash (source|context|text)[:12]
    source: str                # "imessage", "gmail", "notes", "calendar", "slack", "superwhisper"

    # Content
    text: str                  # Main text content
    title: Optional[str]       # Subject, filename, event title, etc.

    # Context
    context_id: str            # Contact name, email thread ID, file path, etc.
    context_type: str          # "conversation", "thread", "document", "event", "channel"

    # Temporal
    timestamp: datetime        # Primary timestamp (UTC)
    end_timestamp: Optional[datetime]  # For conversations/events with duration

    # Metadata
    participants: List[str]    # People involved (names/emails)
    tags: List[str]            # Labels, categories, life areas
    word_count: int

    # Source-specific
    metadata: Dict[str, Any]   # Additional source-specific data
```

## Source-Specific Chunking Strategies

### 1. Gmail
- **Chunk unit**: Full email or email thread
- **Context ID**: Thread ID
- **Participants**: From, To, CC
- **Metadata**: Labels, attachments (names only), importance flags

```python
class GmailChunker:
    def chunk_email(self, email: dict) -> UnifiedChunk:
        return UnifiedChunk(
            chunk_id=hash(f"gmail|{email['thread_id']}|{email['id']}"),
            source="gmail",
            text=f"Subject: {email['subject']}\n\n{email['body']}",
            title=email['subject'],
            context_id=email['thread_id'],
            context_type="thread",
            timestamp=parse_date(email['date']),
            participants=[email['from']] + email.get('to', []),
            tags=email.get('labels', []),
            metadata={
                "has_attachments": bool(email.get('attachments')),
                "is_unread": email.get('is_unread', False),
            }
        )
```

### 2. Notes/Documents (Markdown)
- **Chunk unit**: By headers (H1/H2 sections) or fixed-size windows
- **Context ID**: File path
- **Metadata**: Frontmatter, folder category

```python
class NotesChunker:
    def chunk_document(self, path: Path, content: str) -> List[UnifiedChunk]:
        # Split by headers or use sliding window
        sections = self.split_by_headers(content)
        folder = path.parent.name  # journals, meetings, etc.

        return [
            UnifiedChunk(
                chunk_id=hash(f"notes|{path}|{i}"),
                source="notes",
                text=section.text,
                title=section.header or path.stem,
                context_id=str(path),
                context_type="document",
                timestamp=self.get_document_date(path, content),
                participants=[],
                tags=[folder],
                metadata={"section_index": i}
            )
            for i, section in enumerate(sections)
        ]
```

### 3. Calendar Events
- **Chunk unit**: Single event
- **Context ID**: Event ID
- **Participants**: Attendees

```python
class CalendarChunker:
    def chunk_event(self, event: dict) -> UnifiedChunk:
        description = event.get('description', '')
        notes = event.get('notes', '')

        return UnifiedChunk(
            chunk_id=hash(f"calendar|{event['id']}"),
            source="calendar",
            text=f"{event['title']}\n\n{description}\n\n{notes}",
            title=event['title'],
            context_id=event['id'],
            context_type="event",
            timestamp=parse_date(event['start']),
            end_timestamp=parse_date(event['end']),
            participants=event.get('attendees', []),
            tags=[event.get('calendar', 'primary')],
            metadata={
                "location": event.get('location'),
                "is_recurring": event.get('recurring', False),
            }
        )
```

### 4. Slack
- **Chunk unit**: Conversation windows (similar to iMessage)
- **Context ID**: Channel ID or DM ID
- **Metadata**: Channel name, thread info

```python
class SlackChunker:
    window_hours: float = 4.0

    def chunk_conversation(self, messages: List[dict]) -> List[UnifiedChunk]:
        # Group by time windows, similar to iMessage
        windows = self.group_by_time_window(messages)

        return [
            UnifiedChunk(
                chunk_id=hash(f"slack|{window.channel_id}|{window.start}"),
                source="slack",
                text=self.format_messages(window.messages),
                title=window.channel_name,
                context_id=window.channel_id,
                context_type="channel",
                timestamp=window.start,
                end_timestamp=window.end,
                participants=list(set(m['user'] for m in window.messages)),
                tags=[],
                metadata={
                    "is_thread": window.is_thread,
                    "message_count": len(window.messages),
                }
            )
            for window in windows
        ]
```

### 5. SuperWhisper
- **Chunk unit**: Single recording
- **Context ID**: Recording ID (timestamp)
- **Metadata**: Mode, duration, segments

```python
class SuperWhisperChunker:
    def chunk_recording(self, recording: dict) -> UnifiedChunk:
        meta = recording['meta']

        return UnifiedChunk(
            chunk_id=hash(f"superwhisper|{recording['id']}"),
            source="superwhisper",
            text=meta['result'],
            title=f"Voice note - {meta['modeName']}",
            context_id=str(recording['id']),
            context_type="transcription",
            timestamp=parse_date(meta['datetime']),
            participants=[],  # Self
            tags=[meta['modeName']],
            metadata={
                "duration_ms": meta['duration'],
                "model": meta['modelName'],
                "has_segments": bool(meta.get('segments')),
            }
        )
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1) ✅
1. [x] Analyze existing iMessage RAG implementation
2. [x] Create `UnifiedChunk` dataclass
3. [x] Create base `SourceIndexer` abstract class
4. [x] Extend `MessageVectorStore` to support multiple collections
5. [x] Create `UnifiedRetriever` with cross-collection search

### Phase 2: Source Indexers (Week 1-2) ✅
1. [x] **SuperWhisper Indexer** - Easiest, local JSON files
2. [x] **Notes Indexer** - Markdown files in data/notes/
3. [x] **Gmail Indexer** - Via Gmail MCP tools
4. [x] **Calendar Indexer** - Via Google Calendar API
5. [x] **Slack Indexer** - Via Rube MCP

### Phase 3: MCP Integration (Week 2) ✅
1. [x] Add unified indexing tools to MCP server
2. [x] Add cross-source search tools
3. [x] Add per-source stats and management tools

### Phase 4: Optimization (Week 3+)
1. [ ] Implement incremental indexing (watch for changes)
2. [ ] Add hybrid search (semantic + keyword)
3. [ ] Implement result reranking
4. [ ] Performance optimization for large corpora

## File Structure

```
src/
├── rag/
│   ├── __init__.py
│   ├── store.py              # Extended for multi-collection
│   ├── chunker.py            # Base chunker (iMessage)
│   ├── retriever.py          # Extended for unified search
│   └── unified/
│       ├── __init__.py
│       ├── chunk.py          # UnifiedChunk dataclass
│       ├── base_indexer.py   # Abstract SourceIndexer
│       ├── gmail_indexer.py
│       ├── notes_indexer.py
│       ├── calendar_indexer.py
│       ├── slack_indexer.py
│       └── superwhisper_indexer.py
```

## MCP Tools (Proposed)

```python
# Indexing
index_source(source: str, options: dict)
# source: "gmail", "notes", "calendar", "slack", "superwhisper", "all"

# Searching
search_knowledge(
    query: str,
    sources: List[str] = None,  # Filter to specific sources
    days: int = None,           # Date filter
    participants: List[str] = None,  # Filter by people
    limit: int = 10
)

# Stats
knowledge_stats()  # Returns stats for all indexed sources
```

## Success Criteria

- [ ] All 6 sources indexable with consistent interface
- [ ] Cross-source semantic search returns relevant results
- [ ] Source attribution preserved in all results
- [ ] Incremental indexing (don't re-index unchanged content)
- [ ] Query latency < 500ms for semantic search
- [ ] Index size manageable (< 1GB for typical usage)

## Change Log

| Timestamp | Change | Notes |
|-----------|--------|-------|
| 12/30/2024 01:35 PM PST | Created plan | Initial architecture design |
| 12/30/2024 01:50 PM PST | Core infrastructure complete | UnifiedChunk, UnifiedVectorStore, BaseSourceIndexer |
| 12/30/2024 01:55 PM PST | All indexers implemented | SuperWhisper, Notes, Gmail, Slack, Calendar |
| 12/30/2024 02:05 PM PST | MCP tools added | index_knowledge, search_knowledge, knowledge_stats |
| 12/30/2024 02:10 PM PST | Phase 1-3 complete | Local sources tested and working |

