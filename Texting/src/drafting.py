"""
Context-aware message drafting for iMessage Gateway.

Provides intelligent message drafting by:
- Pulling recent conversation context
- Applying contact style profiles
- Generating contextual suggestions
- Supporting review before send

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Initial implementation with context gathering (Claude)
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DraftContext:
    """Context gathered for drafting a message."""
    contact_name: str
    contact_phone: str
    topic: Optional[str] = None
    intent: Optional[str] = None

    # Recent conversation
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)
    last_message_from_contact: Optional[str] = None
    last_message_to_contact: Optional[str] = None
    conversation_gap_hours: Optional[float] = None

    # Style information
    style_profile: Optional[Dict[str, Any]] = None
    style_guidance: Optional[str] = None

    # Suggested responses
    suggested_replies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the draft context to a JSON-friendly dict."""
        return {
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "topic": self.topic,
            "intent": self.intent,
            "recent_messages_count": len(self.recent_messages),
            "last_message_from_contact": self.last_message_from_contact,
            "last_message_to_contact": self.last_message_to_contact,
            "conversation_gap_hours": self.conversation_gap_hours,
            "style_profile": self.style_profile,
            "style_guidance": self.style_guidance,
            "suggested_replies": self.suggested_replies,
        }


@dataclass
class Draft:
    """Represents a drafted message ready for review."""
    contact_name: str
    contact_phone: str
    message: str
    context: Optional[DraftContext] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the draft message to a JSON-friendly dict."""
        return {
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "message": self.message,
            "context": self.context.to_dict() if self.context else None,
            "created_at": self.created_at.isoformat(),
        }


# Common intents for quick drafting
INTENT_TEMPLATES = {
    "reply": "Reply to their last message",
    "follow-up": "Follow up on a previous conversation",
    "check-in": "Check in and see how they're doing",
    "thank": "Thank them for something",
    "invite": "Invite them to something",
    "remind": "Remind them about something",
    "apologize": "Apologize for something",
    "congratulate": "Congratulate them on something",
    "ask": "Ask them a question",
    "share": "Share something with them",
}


class MessageDrafter:
    """
    Drafts context-aware messages.

    Gathers conversation context and style information
    to help generate appropriate message drafts.
    """

    def __init__(
        self,
        contacts_manager=None,
        messages_interface=None,
        style_analyzer=None,
    ):
        """
        Initialize drafter.

        Args:
            contacts_manager: ContactsManager instance
            messages_interface: MessagesInterface instance
            style_analyzer: StyleAnalyzer instance
        """
        self.contacts_manager = contacts_manager
        self.messages_interface = messages_interface
        self.style_analyzer = style_analyzer

    def _get_contacts_manager(self):
        """Lazy load contacts manager."""
        if self.contacts_manager is None:
            from .contacts_manager import ContactsManager
            self.contacts_manager = ContactsManager()
        return self.contacts_manager

    def _get_messages_interface(self):
        """Lazy load messages interface."""
        if self.messages_interface is None:
            from .messages_interface import MessagesInterface
            self.messages_interface = MessagesInterface()
        return self.messages_interface

    def _get_style_analyzer(self):
        """Lazy load style analyzer."""
        if self.style_analyzer is None:
            from .style_analyzer import StyleAnalyzer
            self.style_analyzer = StyleAnalyzer()
        return self.style_analyzer

    def gather_context(
        self,
        contact_name: str,
        topic: Optional[str] = None,
        intent: Optional[str] = None,
        message_limit: int = 20,
    ) -> DraftContext:
        """
        Gather context for drafting a message.

        Args:
            contact_name: Name of the contact
            topic: Optional topic to focus on
            intent: Optional intent (reply, follow-up, etc.)
            message_limit: Number of recent messages to include

        Returns:
            DraftContext with gathered information

        Raises:
            ValueError: If contact not found
        """
        cm = self._get_contacts_manager()
        mi = self._get_messages_interface()

        # Find contact
        contact = cm.get_contact_by_name(contact_name)
        if not contact:
            raise ValueError(f"Contact '{contact_name}' not found")

        context = DraftContext(
            contact_name=contact.name,
            contact_phone=contact.phone,
            topic=topic,
            intent=intent,
        )

        # Get recent messages
        try:
            messages = mi.get_messages_by_phone(contact.phone, limit=message_limit)
            context.recent_messages = messages

            # Find last messages in each direction
            for msg in messages:
                if msg.get("is_from_me"):
                    if context.last_message_to_contact is None:
                        context.last_message_to_contact = msg.get("text", "")
                else:
                    if context.last_message_from_contact is None:
                        context.last_message_from_contact = msg.get("text", "")

                # Break if we have both
                if context.last_message_to_contact and context.last_message_from_contact:
                    break

            # Calculate conversation gap
            if messages:
                last_msg_time = messages[0].get("date")
                if last_msg_time:
                    if isinstance(last_msg_time, str):
                        from datetime import datetime
                        try:
                            last_msg_time = datetime.fromisoformat(last_msg_time.replace('Z', '+00:00'))
                        except ValueError:
                            last_msg_time = None

                    if last_msg_time:
                        now = datetime.now()
                        if hasattr(last_msg_time, 'tzinfo') and last_msg_time.tzinfo:
                            from datetime import timezone
                            now = datetime.now(timezone.utc)
                        gap = now - last_msg_time
                        context.conversation_gap_hours = gap.total_seconds() / 3600

        except Exception as e:
            logger.warning(f"Error getting messages: {e}")

        # Get style profile
        try:
            sa = self._get_style_analyzer()
            profile = sa.analyze_contact(contact.name, limit=100, days=60)
            context.style_profile = profile.to_dict()
            context.style_guidance = sa.generate_style_guidance(profile)
        except Exception as e:
            logger.warning(f"Error analyzing style: {e}")

        # Generate suggested replies based on context
        context.suggested_replies = self._generate_suggestions(context)

        return context

    def _generate_suggestions(self, context: DraftContext) -> List[str]:
        """Generate contextual message suggestions."""
        suggestions = []

        # Get style info for customization
        is_casual = False
        uses_emoji = False

        if context.style_profile:
            formality = context.style_profile.get("formality_score", 0.5)
            is_casual = formality < 0.4
            uses_emoji = context.style_profile.get("emoji_frequency", 0) > 0.3

        # Determine greeting based on style
        greeting = "Hey" if is_casual else "Hi"
        name = context.contact_name.split()[0] if context.contact_name else ""

        # Intent-based suggestions
        intent = context.intent or ""
        topic = context.topic or ""

        if intent == "reply" and context.last_message_from_contact:
            # Reply suggestions
            last_msg = context.last_message_from_contact.lower()

            if "?" in context.last_message_from_contact:
                # They asked a question
                suggestions.append(f"Let me get back to you on that")
                suggestions.append(f"Good question! I think...")
            elif any(w in last_msg for w in ["thanks", "thank you"]):
                suggestions.append("Of course! Happy to help")
                suggestions.append("Anytime!")
            else:
                suggestions.append(f"Got it, thanks for letting me know")
                suggestions.append(f"Makes sense!")

        elif intent == "follow-up":
            if topic:
                suggestions.append(f"{greeting}{', ' + name if name else ''}, wanted to follow up on {topic}. Any updates?")
            else:
                suggestions.append(f"{greeting}{', ' + name if name else ''}, just wanted to check in. How's everything going?")

            if context.conversation_gap_hours and context.conversation_gap_hours > 48:
                suggestions.append(f"Been a while! Hope you're doing well. {topic if topic else 'Wanted to touch base.'}")

        elif intent == "check-in":
            if context.conversation_gap_hours and context.conversation_gap_hours > 168:  # > 1 week
                suggestions.append(f"{greeting}{', ' + name if name else ''}! Long time no talk. How have you been?")
            else:
                suggestions.append(f"{greeting}{', ' + name if name else ''}! How's it going?")
            suggestions.append(f"Thinking of you, hope all is well!")

        elif intent == "thank":
            if topic:
                suggestions.append(f"Thanks so much for {topic}! Really appreciate it.")
            else:
                suggestions.append(f"Just wanted to say thanks for everything!")
            suggestions.append(f"Really appreciated that, thank you!")

        elif intent == "invite":
            if topic:
                suggestions.append(f"{greeting}! Would you be up for {topic}?")
            else:
                suggestions.append(f"{greeting}! Would love to hang out soon. Free this week?")

        elif intent == "apologize":
            if topic:
                suggestions.append(f"Sorry about {topic}. Can we talk?")
            else:
                suggestions.append(f"Hey, I wanted to apologize. Can we chat?")

        elif intent == "congratulate":
            emoji = " 🎉" if uses_emoji else "!"
            if topic:
                suggestions.append(f"Congrats on {topic}{emoji} That's amazing!")
            else:
                suggestions.append(f"Congratulations{emoji} So happy for you!")

        # Default suggestions if none matched
        if not suggestions:
            if context.last_message_from_contact:
                suggestions.append(f"Thanks for the message!")
            suggestions.append(f"{greeting}{', ' + name if name else ''}!")
            if topic:
                suggestions.append(f"Wanted to reach out about {topic}")

        return suggestions[:5]  # Limit to 5 suggestions

    def create_draft(
        self,
        contact_name: str,
        message: Optional[str] = None,
        topic: Optional[str] = None,
        intent: Optional[str] = None,
        use_template: Optional[str] = None,
        template_vars: Optional[Dict[str, str]] = None,
    ) -> Draft:
        """
        Create a message draft.

        Args:
            contact_name: Name of the contact
            message: Custom message (overrides suggestions)
            topic: Topic for the message
            intent: Intent (reply, follow-up, etc.)
            use_template: Template ID to use
            template_vars: Variables for template

        Returns:
            Draft object ready for review/send
        """
        # Gather context first
        context = self.gather_context(contact_name, topic, intent)

        # Determine message content
        if message:
            draft_message = message
        elif use_template:
            # Use template system
            from .templates import TemplateManager
            tm = TemplateManager()
            vars_dict = template_vars or {}
            vars_dict["name"] = context.contact_name.split()[0]
            if topic:
                vars_dict["topic"] = topic
            draft_message = tm.render_template(use_template, **vars_dict)
        elif context.suggested_replies:
            # Use first suggestion as default
            draft_message = context.suggested_replies[0]
        else:
            draft_message = f"Hey {context.contact_name.split()[0]}!"

        return Draft(
            contact_name=context.contact_name,
            contact_phone=context.contact_phone,
            message=draft_message,
            context=context,
        )

    def format_draft_preview(self, draft: Draft) -> str:
        """Format a draft for human-readable preview."""
        lines = []
        lines.append(f"📝 Draft Message to {draft.contact_name}")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Message: {draft.message}")
        lines.append("")

        if draft.context:
            ctx = draft.context

            if ctx.conversation_gap_hours:
                if ctx.conversation_gap_hours < 1:
                    gap_str = f"{int(ctx.conversation_gap_hours * 60)} minutes"
                elif ctx.conversation_gap_hours < 24:
                    gap_str = f"{int(ctx.conversation_gap_hours)} hours"
                else:
                    gap_str = f"{int(ctx.conversation_gap_hours / 24)} days"
                lines.append(f"Last interaction: {gap_str} ago")

            if ctx.last_message_from_contact:
                preview = ctx.last_message_from_contact[:100]
                if len(ctx.last_message_from_contact) > 100:
                    preview += "..."
                lines.append(f"Their last message: \"{preview}\"")

            if ctx.style_guidance:
                lines.append("")
                lines.append(f"Style tip: {ctx.style_guidance}")

            if len(ctx.suggested_replies) > 1:
                lines.append("")
                lines.append("Alternative suggestions:")
                for i, suggestion in enumerate(ctx.suggested_replies[1:4], 1):
                    lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)
