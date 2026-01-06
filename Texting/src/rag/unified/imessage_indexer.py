"""
iMessage conversation indexer for unified RAG.

Uses time-windowed chunking to preserve conversation context.
Individual messages are too short for effective embeddings (5-20 words),
so we group by contact and time windows (default 4 hours).

This follows the proven approach from the legacy iMessage RAG system.

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Fixed O(n²) contact enrichment: pre-build phone→name map (Claude)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base_indexer import BaseSourceIndexer
from .chunk import UnifiedChunk
from .index_state import IndexState
from ..chunker import ConversationChunker, ConversationChunk

logger = logging.getLogger(__name__)


class ImessageIndexer(BaseSourceIndexer):
    """
    Indexes iMessage conversations using time-windowed chunking.

    Args:
        messages_interface: MessagesInterface instance for fetching messages
        contacts_manager: ContactsManager for name resolution
        store: UnifiedVectorStore for storage
        window_hours: Hours between messages to split chunks (default: 4)
        min_words: Minimum words per chunk (default: 20)
        max_words: Maximum words before splitting (default: 500)
        use_local_embeddings: Use local embeddings instead of OpenAI
    """

    source_name = "imessage"

    def __init__(
        self,
        messages_interface=None,
        contacts_manager=None,
        window_hours: float = 4.0,
        min_words: int = 20,
        max_words: int = 500,
        state_file: Optional[Path] = None,
        **kwargs,
    ):
        """Initialize the iMessage indexer.

        Args:
            messages_interface: MessagesInterface for message access.
            contacts_manager: ContactsManager for name resolution.
            window_hours: Max hours between messages in a chunk.
            min_words: Minimum words per chunk.
            max_words: Maximum words before splitting a chunk.
            state_file: Optional path for incremental index state.
            **kwargs: Forwarded to BaseSourceIndexer.
        """
        super().__init__(**kwargs)

        # Lazy-import to avoid circular dependencies
        # These imports only work when running in the project context
        if messages_interface is None:
            from ...messages_interface import MessagesInterface
            messages_interface = MessagesInterface()
        if contacts_manager is None:
            from ...contacts_manager import ContactsManager
            # Find project root (6 levels up from this file)
            project_root = Path(__file__).parent.parent.parent.parent
            contacts_path = project_root / "config" / "contacts.json"
            contacts_manager = ContactsManager(str(contacts_path))

        self.messages = messages_interface
        self.contacts = contacts_manager
        self._phone_to_name_cache: Dict[str, str] = {}  # Cached phone→name map
        self.chunker = ConversationChunker(
            window_hours=window_hours,
            min_words=min_words,
            max_words=max_words,
        )

        # State tracking for incremental indexing
        # Default state file: ~/.imessage_rag/index_state.json
        if state_file is None:
            state_file = Path.home() / ".imessage_rag" / "index_state.json"
        self.state = IndexState(state_file)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to digits only for consistent matching."""
        return ''.join(c for c in phone if c.isdigit())

    def _build_phone_to_name_map(self) -> Dict[str, str]:
        """
        Build phone→name map for O(1) contact lookups.

        PERF: Changed from O(messages × contacts) to O(contacts) once + O(1) per message.
        Maps multiple phone formats to handle different number styles.
        """
        if self._phone_to_name_cache:
            return self._phone_to_name_cache

        phone_map = {}
        for contact in self.contacts.list_contacts():
            if not contact.phone:
                continue

            # Normalize to digits only
            normalized = self._normalize_phone(contact.phone)
            phone_map[normalized] = contact.name

            # Also store last 10 digits for matching without country code
            if len(normalized) > 10:
                phone_map[normalized[-10:]] = contact.name

        self._phone_to_name_cache = phone_map
        logger.debug(f"Built phone→name map with {len(phone_map)} entries")
        return phone_map

    def _get_contact_name_fast(self, phone: str, phone_map: Dict[str, str]) -> Optional[str]:
        """O(1) contact name lookup using pre-built map."""
        if not phone:
            return None

        normalized = self._normalize_phone(phone)

        # Try exact match first
        if normalized in phone_map:
            return phone_map[normalized]

        # Try last 10 digits (without country code)
        if len(normalized) > 10:
            suffix = normalized[-10:]
            if suffix in phone_map:
                return phone_map[suffix]

        # Try with US country code added
        if len(normalized) == 10:
            with_country = "1" + normalized
            if with_country in phone_map:
                return phone_map[with_country]

        return None

    def fetch_data(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None,
        contact_name: Optional[str] = None,
        incremental: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Fetch iMessages from local database.

        Args:
            days: Days of history to fetch (overrides incremental mode if set)
            limit: Maximum messages to fetch
            contact_name: Fetch messages only with this contact
            incremental: If True, only fetch messages since last index (default: True)

        Returns:
            List of message dicts from MessagesInterface
        """
        # Determine fetch strategy
        if incremental and not days and not contact_name:
            # Incremental mode: fetch only new messages
            last_indexed = self.state.get_last_indexed("imessage")

            if last_indexed:
                logger.info(f"Incremental mode: fetching messages since {last_indexed.isoformat()}")
                messages = self.messages.get_messages_since(last_indexed, limit=limit)
            else:
                logger.info("No previous index state, doing full index")
                limit = limit or 10000
                messages = self.messages.get_all_recent_conversations(limit=limit)

        elif days:
            # Days mode: fetch last N days
            logger.info(f"Days mode: fetching last {days} days")
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=days)

            messages = self.messages.get_messages_since(cutoff, limit=limit)

        elif contact_name:
            # Contact-specific mode
            logger.info(f"Contact mode: fetching messages with {contact_name}")
            contact = self.contacts.get_contact_by_name(contact_name)
            if not contact:
                raise ValueError(f"Contact '{contact_name}' not found")

            limit = limit or 10000
            messages = self.messages.get_recent_messages(
                contact.phone,
                limit=limit
            )

            # Enrich with contact name
            for msg in messages:
                msg["_contact_name"] = contact.name
                msg["phone"] = contact.phone

        else:
            # Full mode: fetch all recent
            logger.info("Full mode: fetching all messages")
            limit = limit or 10000
            messages = self.messages.get_all_recent_conversations(limit=limit)

        # Enrich messages with contact names where available
        # PERF: Use O(1) lookup via pre-built phone→name map instead of O(n) per message
        if not contact_name:  # Skip if already enriched above
            phone_map = self._build_phone_to_name_map()
            for msg in messages:
                phone = msg.get("phone")
                if phone and "_contact_name" not in msg:
                    name = self._get_contact_name_fast(phone, phone_map)
                    if name:
                        msg["_contact_name"] = name

        logger.info(f"Fetched {len(messages)} iMessages")
        return messages

    def chunk_data(self, messages: List[Dict[str, Any]]) -> List[UnifiedChunk]:
        """
        Convert iMessages to UnifiedChunks using time-windowed conversation chunks.

        Args:
            messages: List of message dicts from MessagesInterface

        Returns:
            List of UnifiedChunks ready for indexing
        """
        if not messages:
            return []

        # Use ConversationChunker to create time-windowed chunks
        conversation_chunks = self.chunker.chunk_messages(messages)

        # Convert ConversationChunks to UnifiedChunks
        unified_chunks = []
        for conv_chunk in conversation_chunks:
            unified_chunk = self._conversation_chunk_to_unified(conv_chunk)
            if unified_chunk:
                unified_chunks.append(unified_chunk)

        logger.info(
            f"Created {len(unified_chunks)} unified chunks from "
            f"{len(messages)} messages ({len(conversation_chunks)} conversations)"
        )
        return unified_chunks

    def index(
        self,
        days: Optional[int] = None,
        limit: Optional[int] = None,
        batch_size: int = 100,
        incremental: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Index iMessages with incremental state tracking.

        Overrides base method to add state management for incremental indexing.

        Args:
            days: How many days of history to index
            limit: Maximum items to index
            batch_size: Batch size for embedding API
            incremental: If True, only index new messages (default: True)
            **kwargs: Source-specific options (e.g., contact_name)

        Returns:
            Dict with indexing stats
        """
        start_time = datetime.now()

        # Store incremental flag for fetch_data
        kwargs["incremental"] = incremental

        # Call parent's index method
        result = super().index(days=days, limit=limit, batch_size=batch_size, **kwargs)

        # Update state on successful indexing (incremental mode only)
        if result.get("success") and incremental and not days:
            # Get the latest message timestamp from this indexing run
            # We'll update state to current time (conservative approach)
            # Alternatively, we could track max message timestamp from fetch_data
            self.state.update_last_indexed("imessage", datetime.now())

            logger.info("Updated incremental index state")

        return result

    def _conversation_chunk_to_unified(
        self,
        conv_chunk: ConversationChunk,
    ) -> Optional[UnifiedChunk]:
        """
        Convert a ConversationChunk to UnifiedChunk.

        Args:
            conv_chunk: ConversationChunk from ConversationChunker

        Returns:
            UnifiedChunk ready for indexing, or None if invalid
        """
        # Skip chunks that are too short (likely noise)
        if not conv_chunk.text or conv_chunk.word_count < 10:
            return None

        # Determine context type
        context_type = "conversation"  # For 1:1 and group chats

        # Build title
        if conv_chunk.is_group:
            title = f"Group: {conv_chunk.group_name or 'Unnamed'}"
        else:
            title = f"Conversation with {conv_chunk.contact}"

        # Build participants list
        participants = [conv_chunk.contact]
        if conv_chunk.is_group:
            # Extract unique phones from metadata
            phones = conv_chunk.metadata.get("phones", [])
            participants.extend(phones)
            participants = list(set(participants))  # Deduplicate

        # Build tags
        tags = []
        if conv_chunk.is_group:
            tags.append("group_chat")

        return UnifiedChunk(
            chunk_id=conv_chunk.chunk_id,  # Reuse conversation chunk ID
            source="imessage",
            text=conv_chunk.text,
            title=title,
            context_id=conv_chunk.contact,
            context_type=context_type,
            timestamp=conv_chunk.start_time,
            end_timestamp=conv_chunk.end_time,
            participants=participants,
            tags=tags,
            word_count=conv_chunk.word_count,
            metadata={
                "message_count": conv_chunk.message_count,
                "duration_minutes": conv_chunk.duration_minutes,
                "is_group": conv_chunk.is_group,
                "group_name": conv_chunk.group_name or "",
            },
        )
