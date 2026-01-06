"""
Contact management for iMessage MCP server.

Sprint 1: Basic contact lookup from JSON config
Sprint 2: macOS Contacts sync, fuzzy matching, DB integration
Sprint 3: SQLite-backed contacts with interaction logging

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Added SQLite backend with Life Planner DB integration (Claude)
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Life Planner database path
LIFE_PLANNER_DB = Path(__file__).parent.parent.parent / "data" / "database" / "planner.db"


class Contact:
    """Represents a contact with messaging information."""

    def __init__(
        self,
        name: str,
        phone: str,
        relationship_type: str = "other",
        notes: str = "",
        id: Optional[int] = None,
        last_interaction: Optional[datetime] = None,
        interaction_count: int = 0
    ):
        """Initialize a contact record.

        Args:
            name: Display name for the contact.
            phone: Primary phone number for messaging.
            relationship_type: Relationship category label.
            notes: Freeform notes about the contact.
            id: Optional database identifier.
            last_interaction: Timestamp of last interaction, if any.
            interaction_count: Count of logged interactions.
        """
        self.id = id
        self.name = name
        self.phone = phone
        self.relationship_type = relationship_type
        self.notes = notes
        self.last_interaction = last_interaction
        self.interaction_count = interaction_count

    def __repr__(self):
        """Return a concise representation for logs/debugging."""
        return f"Contact(id={self.id}, name='{self.name}', phone='{self.phone}')"

    def to_dict(self) -> dict:
        """Serialize the contact to a JSON-friendly dict."""
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "relationship_type": self.relationship_type,
            "notes": self.notes,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count
        }


class ContactsManager:
    """
    Manages contact lookup and resolution.

    Sprint 1: Load from JSON config file
    Sprint 2: Sync with macOS Contacts and Life Planner database
    Sprint 3: SQLite-backed with Life Planner DB integration
    """

    def __init__(self, config_path: str = "config/contacts.json", use_db: bool = True):
        """
        Initialize contacts manager.

        Args:
            config_path: Path to contacts configuration file (fallback)
            use_db: Whether to use SQLite database (default: True)
        """
        self.config_path = Path(config_path)
        self.use_db = use_db and LIFE_PLANNER_DB.exists()
        self.contacts: List[Contact] = []
        self._db_conn: Optional[sqlite3.Connection] = None
        self._load_contacts()

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._db_conn is None:
            self._db_conn = sqlite3.connect(LIFE_PLANNER_DB)
            self._db_conn.row_factory = sqlite3.Row
        return self._db_conn

    def _load_contacts(self):
        """Load contacts from database or JSON fallback."""
        if self.use_db:
            self._load_from_db()
        else:
            self._load_from_json()

    def _load_from_db(self):
        """Load contacts from Life Planner SQLite database."""
        try:
            conn = self._get_db_connection()
            cursor = conn.execute("""
                SELECT id, name, phone, relationship_type, notes,
                       last_interaction, interaction_count
                FROM contacts
                ORDER BY name
            """)

            self.contacts = []
            for row in cursor:
                last_interaction = None
                if row["last_interaction"]:
                    try:
                        last_interaction = datetime.fromisoformat(row["last_interaction"])
                    except (ValueError, TypeError):
                        pass

                self.contacts.append(Contact(
                    id=row["id"],
                    name=row["name"],
                    phone=row["phone"],
                    relationship_type=row["relationship_type"] or "other",
                    notes=row["notes"] or "",
                    last_interaction=last_interaction,
                    interaction_count=row["interaction_count"] or 0
                ))

            logger.info(f"Loaded {len(self.contacts)} contacts from database")

        except sqlite3.Error as e:
            logger.error(f"Database error, falling back to JSON: {e}")
            self.use_db = False
            self._load_from_json()

    def _load_from_json(self):
        """Load contacts from JSON configuration file (fallback)."""
        if not self.config_path.exists():
            logger.warning(f"Contacts config not found: {self.config_path}")
            logger.warning("Creating empty contacts.json - please add your contacts")
            self._create_default_config()
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            contacts_data = data.get("contacts", [])
            self.contacts = [
                Contact(
                    name=c["name"],
                    phone=c["phone"],
                    relationship_type=c.get("relationship_type", "other"),
                    notes=c.get("notes", "")
                )
                for c in contacts_data
            ]

            logger.info(f"Loaded {len(self.contacts)} contacts from JSON config")

        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
            self.contacts = []

    def _create_default_config(self):
        """Create default contacts configuration file."""
        default_config = {
            "_comment": "Manual contact configuration for Sprint 1",
            "_instructions": "Add your contacts here. Format: +1XXXXXXXXXX",
            "contacts": []
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default config at {self.config_path}")

    def get_contact_by_name(self, name: str) -> Optional[Contact]:
        """
        Get contact by exact name match.

        Args:
            name: Contact name to search for

        Returns:
            Contact object if found, None otherwise

        Note:
            Sprint 1: Exact match only
            Sprint 2: Will add fuzzy matching
        """
        # Exact match (case-insensitive)
        for contact in self.contacts:
            if contact.name.lower() == name.lower():
                logger.info(f"Found contact: {contact.name} -> {contact.phone}")
                return contact

        # Try partial match (contains)
        for contact in self.contacts:
            if name.lower() in contact.name.lower():
                logger.info(f"Partial match: {contact.name} -> {contact.phone}")
                return contact

        logger.warning(f"Contact not found: {name}")
        return None

    def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """
        Get contact by phone number.

        Args:
            phone: Phone number to search for

        Returns:
            Contact object if found, None otherwise
        """
        # Normalize phone for comparison (remove non-digits)
        normalized_search = ''.join(c for c in phone if c.isdigit())

        for contact in self.contacts:
            normalized_contact = ''.join(c for c in contact.phone if c.isdigit())

            # Match if search phone is suffix of contact phone
            # (handles +1 country code differences)
            if (normalized_contact.endswith(normalized_search) or
                normalized_search.endswith(normalized_contact)):
                logger.info(f"Found contact by phone: {contact.name}")
                return contact

        logger.warning(f"No contact found for phone: {phone}")
        return None

    def list_contacts(self) -> List[Contact]:
        """
        Get all contacts.

        Returns:
            List of all Contact objects
        """
        return self.contacts

    def add_contact(
        self,
        name: str,
        phone: str,
        relationship_type: str = "other",
        notes: str = ""
    ) -> Contact:
        """
        Add a new contact.

        Args:
            name: Contact name
            phone: Phone number
            relationship_type: Type of relationship
            notes: Optional notes

        Returns:
            Created Contact object
        """
        if self.use_db:
            return self._add_contact_db(name, phone, relationship_type, notes)
        else:
            return self._add_contact_json(name, phone, relationship_type, notes)

    def _add_contact_db(
        self, name: str, phone: str, relationship_type: str, notes: str
    ) -> Contact:
        """Add contact to SQLite database."""
        try:
            conn = self._get_db_connection()
            cursor = conn.execute("""
                INSERT INTO contacts (name, phone, relationship_type, notes)
                VALUES (?, ?, ?, ?)
                RETURNING id
            """, (name, phone, relationship_type, notes))

            row = cursor.fetchone()
            contact_id = row[0] if row else None
            conn.commit()

            contact = Contact(
                id=contact_id,
                name=name,
                phone=phone,
                relationship_type=relationship_type,
                notes=notes
            )
            self.contacts.append(contact)

            # Also save to JSON as backup
            self._save_contacts_json()

            logger.info(f"Added contact to database: {name} (id={contact_id})")
            return contact

        except sqlite3.IntegrityError as e:
            logger.error(f"Contact with phone {phone} already exists: {e}")
            raise ValueError(f"Contact with phone {phone} already exists")
        except sqlite3.Error as e:
            logger.error(f"Database error adding contact: {e}")
            raise

    def _add_contact_json(
        self, name: str, phone: str, relationship_type: str, notes: str
    ) -> Contact:
        """Add contact to JSON config (fallback)."""
        contact = Contact(name=name, phone=phone, relationship_type=relationship_type, notes=notes)
        self.contacts.append(contact)
        self._save_contacts_json()
        logger.info(f"Added contact to JSON: {name}")
        return contact

    def _save_contacts_json(self):
        """Save contacts back to JSON configuration file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)
            else:
                data = {"contacts": []}

            # Only save JSON-compatible fields
            data["contacts"] = [
                {
                    "name": c.name,
                    "phone": c.phone,
                    "relationship_type": c.relationship_type,
                    "notes": c.notes
                }
                for c in self.contacts
            ]

            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved contacts to JSON config")

        except Exception as e:
            logger.error(f"Error saving contacts to JSON: {e}")

    # =========================================================================
    # Interaction Logging (Sprint 3)
    # =========================================================================

    def log_interaction(
        self,
        phone: str,
        direction: str,
        message_preview: str = "",
        channel: str = "imessage"
    ) -> bool:
        """
        Log a message interaction for CRM tracking.

        Args:
            phone: Phone number of the contact
            direction: 'sent' or 'received'
            message_preview: First ~100 chars of message
            channel: Communication channel (imessage, sms, whatsapp, email)

        Returns:
            True if logged successfully, False otherwise
        """
        if not self.use_db:
            logger.debug("Interaction logging requires database - skipping")
            return False

        try:
            conn = self._get_db_connection()

            # Find contact ID by phone
            cursor = conn.execute(
                "SELECT id FROM contacts WHERE phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            contact_id = row[0] if row else None

            # Truncate message preview
            preview = message_preview[:100] if message_preview else ""

            # Insert interaction
            conn.execute("""
                INSERT INTO message_interactions
                    (contact_id, phone, direction, message_preview, channel)
                VALUES (?, ?, ?, ?, ?)
            """, (contact_id, phone, direction, preview, channel))

            # Update contact's last_interaction and count
            if contact_id:
                conn.execute("""
                    UPDATE contacts
                    SET last_interaction = CURRENT_TIMESTAMP,
                        interaction_count = interaction_count + 1
                    WHERE id = ?
                """, (contact_id,))

            conn.commit()
            logger.debug(f"Logged {direction} interaction with {phone}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error logging interaction: {e}")
            return False

    def get_interaction_history(
        self,
        phone: Optional[str] = None,
        contact_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get interaction history for a contact.

        Args:
            phone: Filter by phone number
            contact_id: Filter by contact ID
            limit: Maximum number of interactions to return

        Returns:
            List of interaction records
        """
        if not self.use_db:
            return []

        try:
            conn = self._get_db_connection()

            query = """
                SELECT mi.*, c.name as contact_name
                FROM message_interactions mi
                LEFT JOIN contacts c ON mi.contact_id = c.id
                WHERE 1=1
            """
            params = []

            if phone:
                query += " AND mi.phone = ?"
                params.append(phone)
            if contact_id:
                query += " AND mi.contact_id = ?"
                params.append(contact_id)

            query += " ORDER BY mi.timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)

            return [dict(row) for row in cursor]

        except sqlite3.Error as e:
            logger.error(f"Error getting interaction history: {e}")
            return []

    def get_contacts_needing_followup(self, stale_days: int = 7, limit: int = 20) -> List[Contact]:
        """
        Get contacts that haven't been interacted with recently.

        Args:
            stale_days: Number of days since last interaction to consider stale
            limit: Maximum contacts to return

        Returns:
            List of contacts needing follow-up
        """
        if not self.use_db:
            return []

        try:
            conn = self._get_db_connection()
            cursor = conn.execute("""
                SELECT id, name, phone, relationship_type, notes,
                       last_interaction, interaction_count
                FROM contacts
                WHERE last_interaction IS NOT NULL
                  AND last_interaction < datetime('now', ? || ' days')
                ORDER BY last_interaction ASC
                LIMIT ?
            """, (f"-{stale_days}", limit))

            contacts = []
            for row in cursor:
                last_interaction = None
                if row["last_interaction"]:
                    try:
                        last_interaction = datetime.fromisoformat(row["last_interaction"])
                    except (ValueError, TypeError):
                        pass

                contacts.append(Contact(
                    id=row["id"],
                    name=row["name"],
                    phone=row["phone"],
                    relationship_type=row["relationship_type"] or "other",
                    notes=row["notes"] or "",
                    last_interaction=last_interaction,
                    interaction_count=row["interaction_count"] or 0
                ))

            return contacts

        except sqlite3.Error as e:
            logger.error(f"Error getting followup contacts: {e}")
            return []

    def close(self):
        """Close database connection."""
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None
