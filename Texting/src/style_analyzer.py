"""
Message style analyzer for iMessage Gateway.

Extracts messaging patterns from chat.db to build per-contact style profiles:
- Formality level (formal vs casual)
- Emoji usage patterns
- Average message length
- Response timing
- Common greetings and sign-offs

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Initial implementation with profile generation (Claude)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class StyleProfile:
    """Represents a contact's messaging style profile."""
    contact_name: str
    contact_phone: str

    # Message patterns
    avg_message_length: float = 0.0
    avg_word_count: float = 0.0
    message_count: int = 0

    # Emoji patterns
    emoji_frequency: float = 0.0  # Emojis per message
    top_emojis: List[str] = field(default_factory=list)
    uses_emojis: bool = False

    # Formality indicators
    formality_score: float = 0.5  # 0=casual, 1=formal
    uses_punctuation: bool = True
    uses_capitalization: bool = True
    uses_contractions: bool = True

    # Common patterns
    common_greetings: List[str] = field(default_factory=list)
    common_signoffs: List[str] = field(default_factory=list)
    common_phrases: List[str] = field(default_factory=list)

    # Timing patterns
    avg_response_time_minutes: Optional[float] = None
    active_hours: List[int] = field(default_factory=list)  # Hours of day (0-23)

    # Metadata
    analyzed_at: Optional[datetime] = None
    message_date_range: Optional[Tuple[datetime, datetime]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the style profile to a JSON-friendly dict."""
        return {
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "avg_message_length": round(self.avg_message_length, 1),
            "avg_word_count": round(self.avg_word_count, 1),
            "message_count": self.message_count,
            "emoji_frequency": round(self.emoji_frequency, 2),
            "top_emojis": self.top_emojis[:5],
            "uses_emojis": self.uses_emojis,
            "formality_score": round(self.formality_score, 2),
            "formality_level": self._formality_level(),
            "uses_punctuation": self.uses_punctuation,
            "uses_capitalization": self.uses_capitalization,
            "uses_contractions": self.uses_contractions,
            "common_greetings": self.common_greetings[:3],
            "common_signoffs": self.common_signoffs[:3],
            "common_phrases": self.common_phrases[:5],
            "avg_response_time_minutes": round(self.avg_response_time_minutes, 1) if self.avg_response_time_minutes else None,
            "active_hours": self.active_hours[:5],
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }

    def _formality_level(self) -> str:
        """Get human-readable formality level."""
        if self.formality_score >= 0.7:
            return "formal"
        elif self.formality_score >= 0.4:
            return "neutral"
        else:
            return "casual"

    def get_style_summary(self) -> str:
        """Get a human-readable style summary."""
        parts = []

        # Formality
        formality = self._formality_level()
        parts.append(f"Tone: {formality}")

        # Message length
        if self.avg_word_count < 5:
            parts.append("Short messages")
        elif self.avg_word_count > 20:
            parts.append("Detailed messages")

        # Emoji usage
        if self.uses_emojis:
            if self.emoji_frequency > 0.5:
                parts.append("Frequent emoji user")
            else:
                parts.append("Occasional emojis")
        else:
            parts.append("Rarely uses emojis")

        # Timing
        if self.avg_response_time_minutes is not None:
            if self.avg_response_time_minutes < 5:
                parts.append("Quick responder")
            elif self.avg_response_time_minutes > 60:
                parts.append("Slow responder")

        return " | ".join(parts)


class StyleAnalyzer:
    """
    Analyzes messaging patterns to build style profiles.

    Uses message history from chat.db to extract patterns like:
    - Formality (capitalization, punctuation, contractions)
    - Emoji usage
    - Message length tendencies
    - Common phrases and greetings
    """

    # Common greetings to detect
    GREETINGS = [
        r'\bhey\b', r'\bhi\b', r'\bhello\b', r'\byo\b', r'\bsup\b',
        r'\bmorning\b', r'\bafternoon\b', r'\bevening\b',
        r'\bwhat\'?s up\b', r'\bhowdy\b'
    ]

    # Common sign-offs
    SIGNOFFS = [
        r'\bthanks\b', r'\bthx\b', r'\bty\b', r'\bcheers\b',
        r'\blater\b', r'\bbye\b', r'\bttyl\b', r'\bxoxo\b',
        r'\blove you\b', r'\btake care\b'
    ]

    # Formal indicators
    FORMAL_INDICATORS = [
        r'\bkind regards\b', r'\bbest regards\b', r'\bsincerely\b',
        r'\bplease\b', r'\bthank you\b', r'\bapologies\b',
        r'\bi apologize\b', r'\bwould you\b', r'\bcould you\b'
    ]

    # Casual indicators
    CASUAL_INDICATORS = [
        r'\blol\b', r'\blmao\b', r'\bimo\b', r'\bimo\b', r'\bbtw\b',
        r'\bomg\b', r'\bidk\b', r'\bnvm\b', r'\bjk\b', r'\bfyi\b',
        r'\bdude\b', r'\bman\b', r'\bbro\b', r'\bfam\b'
    ]

    # Emoji regex
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended
        "\U00002600-\U000026FF"  # misc symbols
        "]+",
        flags=re.UNICODE
    )

    def __init__(self, messages_interface=None, contacts_manager=None):
        """
        Initialize style analyzer.

        Args:
            messages_interface: MessagesInterface for fetching messages
            contacts_manager: ContactsManager for contact resolution
        """
        if messages_interface is None:
            from .messages_interface import MessagesInterface
            messages_interface = MessagesInterface()
        if contacts_manager is None:
            from .contacts_manager import ContactsManager
            project_root = Path(__file__).parent.parent
            contacts_path = project_root / "config" / "contacts.json"
            contacts_manager = ContactsManager(str(contacts_path))

        self.messages = messages_interface
        self.contacts = contacts_manager
        self._profiles: Dict[str, StyleProfile] = {}

    def analyze_contact(
        self,
        contact_name: str,
        limit: int = 500,
        days: Optional[int] = 90,
    ) -> StyleProfile:
        """
        Analyze a contact's messaging style.

        Args:
            contact_name: Name of contact to analyze
            limit: Maximum messages to analyze
            days: Days of history to analyze (default: 90)

        Returns:
            StyleProfile for the contact

        Raises:
            ValueError: If contact not found
        """
        contact = self.contacts.get_contact_by_name(contact_name)
        if not contact:
            raise ValueError(f"Contact '{contact_name}' not found")

        # Fetch messages
        messages = self.messages.get_messages_by_phone(contact.phone, limit=limit)

        if not messages:
            logger.warning(f"No messages found for {contact_name}")
            return StyleProfile(
                contact_name=contact.name,
                contact_phone=contact.phone,
                analyzed_at=datetime.now(),
            )

        # Filter to only outgoing messages (user's style)
        sent_messages = [m for m in messages if m.get('is_from_me')]
        received_messages = [m for m in messages if not m.get('is_from_me')]

        # Build profile from sent messages (to learn user's style with this contact)
        profile = self._analyze_messages(sent_messages, contact.name, contact.phone)

        # Add response time analysis
        if len(received_messages) > 1 and len(sent_messages) > 1:
            profile.avg_response_time_minutes = self._calculate_response_time(messages)

        # Store profile
        self._profiles[contact.phone] = profile

        logger.info(f"Analyzed style for {contact_name}: {len(sent_messages)} sent messages")
        return profile

    def _analyze_messages(
        self,
        messages: List[Dict],
        contact_name: str,
        contact_phone: str,
    ) -> StyleProfile:
        """Analyze a list of messages to build a style profile."""
        if not messages:
            return StyleProfile(
                contact_name=contact_name,
                contact_phone=contact_phone,
                analyzed_at=datetime.now(),
            )

        texts = [m.get('text', '') or '' for m in messages]
        texts = [t for t in texts if t.strip()]  # Filter empty

        if not texts:
            return StyleProfile(
                contact_name=contact_name,
                contact_phone=contact_phone,
                analyzed_at=datetime.now(),
            )

        # Basic stats
        lengths = [len(t) for t in texts]
        word_counts = [len(t.split()) for t in texts]
        avg_length = sum(lengths) / len(lengths)
        avg_words = sum(word_counts) / len(word_counts)

        # Emoji analysis
        all_emojis = []
        emoji_counts = []
        for text in texts:
            emojis = self.EMOJI_PATTERN.findall(text)
            all_emojis.extend(emojis)
            emoji_counts.append(len(emojis))

        emoji_freq = sum(emoji_counts) / len(emoji_counts) if emoji_counts else 0
        emoji_counter = Counter(all_emojis)
        top_emojis = [e for e, _ in emoji_counter.most_common(5)]

        # Formality analysis
        formality = self._analyze_formality(texts)

        # Punctuation and capitalization
        uses_punct = self._check_punctuation_usage(texts)
        uses_caps = self._check_capitalization_usage(texts)
        uses_contractions = self._check_contraction_usage(texts)

        # Common patterns
        greetings = self._extract_patterns(texts, self.GREETINGS)
        signoffs = self._extract_patterns(texts, self.SIGNOFFS)
        phrases = self._extract_common_phrases(texts)

        # Active hours
        active_hours = self._extract_active_hours(messages)

        # Date range
        timestamps = [m.get('timestamp') for m in messages if m.get('timestamp')]
        date_range = None
        if timestamps:
            try:
                dates = []
                for ts in timestamps:
                    if isinstance(ts, str):
                        dates.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    elif isinstance(ts, datetime):
                        dates.append(ts)
                if dates:
                    date_range = (min(dates), max(dates))
            except (ValueError, TypeError):
                pass

        return StyleProfile(
            contact_name=contact_name,
            contact_phone=contact_phone,
            avg_message_length=avg_length,
            avg_word_count=avg_words,
            message_count=len(texts),
            emoji_frequency=emoji_freq,
            top_emojis=top_emojis,
            uses_emojis=emoji_freq > 0.1,
            formality_score=formality,
            uses_punctuation=uses_punct,
            uses_capitalization=uses_caps,
            uses_contractions=uses_contractions,
            common_greetings=greetings,
            common_signoffs=signoffs,
            common_phrases=phrases,
            active_hours=active_hours,
            analyzed_at=datetime.now(),
            message_date_range=date_range,
        )

    def _analyze_formality(self, texts: List[str]) -> float:
        """Analyze formality level (0=casual, 1=formal)."""
        formal_count = 0
        casual_count = 0

        for text in texts:
            text_lower = text.lower()

            for pattern in self.FORMAL_INDICATORS:
                if re.search(pattern, text_lower):
                    formal_count += 1
                    break

            for pattern in self.CASUAL_INDICATORS:
                if re.search(pattern, text_lower):
                    casual_count += 1
                    break

        total = formal_count + casual_count
        if total == 0:
            return 0.5  # Neutral

        return formal_count / total

    def _check_punctuation_usage(self, texts: List[str]) -> bool:
        """Check if user typically uses punctuation."""
        punct_count = sum(1 for t in texts if t.rstrip()[-1:] in '.!?')
        return punct_count / len(texts) > 0.5

    def _check_capitalization_usage(self, texts: List[str]) -> bool:
        """Check if user typically capitalizes first letter."""
        cap_count = sum(1 for t in texts if t and t[0].isupper())
        return cap_count / len(texts) > 0.5

    def _check_contraction_usage(self, texts: List[str]) -> bool:
        """Check if user uses contractions."""
        contractions = ["'m", "'s", "'t", "'re", "'ve", "'ll", "'d"]
        contraction_count = sum(
            1 for t in texts
            if any(c in t.lower() for c in contractions)
        )
        return contraction_count / len(texts) > 0.2

    def _extract_patterns(self, texts: List[str], patterns: List[str]) -> List[str]:
        """Extract matched patterns from texts."""
        found = Counter()
        for text in texts:
            text_lower = text.lower()
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    found[match] += 1
        return [p for p, _ in found.most_common(5)]

    def _extract_common_phrases(self, texts: List[str], min_length: int = 3) -> List[str]:
        """Extract commonly used phrases (2-4 word ngrams)."""
        phrase_counter = Counter()

        for text in texts:
            words = text.lower().split()
            # 2-grams
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i+2])
                if len(phrase) >= min_length:
                    phrase_counter[phrase] += 1
            # 3-grams
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3])
                if len(phrase) >= min_length:
                    phrase_counter[phrase] += 1

        # Filter out very common words
        stop_phrases = ['i am', 'i was', 'you are', 'it is', 'to the', 'in the']
        return [
            p for p, count in phrase_counter.most_common(10)
            if count >= 2 and p not in stop_phrases
        ][:5]

    def _extract_active_hours(self, messages: List[Dict]) -> List[int]:
        """Extract most active hours of day."""
        hour_counter = Counter()

        for msg in messages:
            ts = msg.get('timestamp')
            if ts:
                try:
                    if isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    elif isinstance(ts, datetime):
                        dt = ts
                    else:
                        continue
                    hour_counter[dt.hour] += 1
                except (ValueError, TypeError):
                    pass

        return [h for h, _ in hour_counter.most_common(5)]

    def _calculate_response_time(self, messages: List[Dict]) -> Optional[float]:
        """Calculate average response time in minutes."""
        response_times = []

        # Sort by timestamp
        sorted_msgs = sorted(
            messages,
            key=lambda m: m.get('timestamp', ''),
        )

        prev_msg = None
        for msg in sorted_msgs:
            if prev_msg is None:
                prev_msg = msg
                continue

            # If previous was received and this is sent, calculate response time
            if not prev_msg.get('is_from_me') and msg.get('is_from_me'):
                try:
                    prev_ts = prev_msg.get('timestamp')
                    curr_ts = msg.get('timestamp')

                    if isinstance(prev_ts, str):
                        prev_dt = datetime.fromisoformat(prev_ts.replace('Z', '+00:00'))
                    else:
                        prev_dt = prev_ts

                    if isinstance(curr_ts, str):
                        curr_dt = datetime.fromisoformat(curr_ts.replace('Z', '+00:00'))
                    else:
                        curr_dt = curr_ts

                    delta = (curr_dt - prev_dt).total_seconds() / 60
                    if 0 < delta < 24 * 60:  # Within 24 hours
                        response_times.append(delta)
                except (ValueError, TypeError):
                    pass

            prev_msg = msg

        if response_times:
            return sum(response_times) / len(response_times)
        return None

    def get_profile(self, contact_name: str) -> Optional[StyleProfile]:
        """Get cached profile for a contact."""
        contact = self.contacts.get_contact_by_name(contact_name)
        if contact and contact.phone in self._profiles:
            return self._profiles[contact.phone]
        return None

    def generate_style_guidance(self, profile: StyleProfile) -> str:
        """
        Generate style guidance for drafting messages.

        Returns a natural language description of how to match the contact's style.
        """
        guidance = []

        # Formality
        if profile.formality_score >= 0.7:
            guidance.append("Use formal language, proper punctuation, and complete sentences.")
        elif profile.formality_score <= 0.3:
            guidance.append("Keep it casual and relaxed. Abbreviations and slang are fine.")
        else:
            guidance.append("Use a balanced, friendly tone.")

        # Message length
        if profile.avg_word_count < 5:
            guidance.append("Keep messages short and concise.")
        elif profile.avg_word_count > 20:
            guidance.append("Feel free to write longer, detailed messages.")

        # Emojis
        if profile.uses_emojis and profile.emoji_frequency > 0.3:
            top = ', '.join(profile.top_emojis[:3]) if profile.top_emojis else ''
            guidance.append(f"Include emojis freely. Favorites: {top}")
        elif not profile.uses_emojis:
            guidance.append("Avoid emojis - they rarely use them.")

        # Punctuation/Capitalization
        if not profile.uses_punctuation:
            guidance.append("Ending punctuation is optional.")
        if not profile.uses_capitalization:
            guidance.append("Lowercase is fine.")

        # Common phrases
        if profile.common_greetings:
            guidance.append(f"Common greetings: {', '.join(profile.common_greetings[:2])}")

        return " ".join(guidance)
