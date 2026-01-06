"""
Message template system for iMessage Gateway.

Provides reusable message templates with variable substitution:
- Built-in templates (thank you, birthday, follow-up, etc.)
- Custom template creation
- Variable interpolation ({name}, {topic}, {date}, etc.)

CHANGELOG (recent first, max 5 entries)
01/04/2026 - Initial implementation with JSON storage (Claude)
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Default templates config path
DEFAULT_TEMPLATES_PATH = Path(__file__).parent.parent / "config" / "templates.json"


@dataclass
class Template:
    """Represents a message template."""
    id: str
    name: str
    template: str
    description: str
    variables: List[str] = field(default_factory=list)
    is_custom: bool = False
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the template to a JSON-friendly dict."""
        return {
            "id": self.id,
            "name": self.name,
            "template": self.template,
            "description": self.description,
            "variables": self.variables,
            "is_custom": self.is_custom,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def render(self, **kwargs) -> str:
        """
        Render template with variable substitution.

        Args:
            **kwargs: Variable values (name="John", topic="the meeting")

        Returns:
            Rendered message string

        Raises:
            ValueError: If required variable is missing
        """
        result = self.template

        # Check for missing required variables
        missing = []
        for var in self.variables:
            if var not in kwargs or not kwargs[var]:
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Substitute variables
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result

    def get_variable_prompts(self) -> Dict[str, str]:
        """Get user-friendly prompts for each variable."""
        prompts = {
            "name": "Contact's name",
            "topic": "What topic/subject?",
            "date": "Date (e.g., tomorrow, Jan 5)",
            "time": "Time (e.g., 15 minutes, 2pm)",
            "custom": "Custom text",
        }
        return {var: prompts.get(var, f"Value for {var}") for var in self.variables}


class TemplateManager:
    """
    Manages message templates.

    Provides functionality to:
    - List available templates
    - Render templates with variables
    - Create custom templates
    - Delete custom templates
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize template manager.

        Args:
            config_path: Path to templates.json config file
        """
        self.config_path = config_path or DEFAULT_TEMPLATES_PATH
        self.templates: Dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self):
        """Load templates from JSON config file."""
        if not self.config_path.exists():
            logger.warning(f"Templates config not found: {self.config_path}")
            self._create_default_config()
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            templates_data = data.get("templates", {})
            for template_id, template_info in templates_data.items():
                self.templates[template_id] = Template(
                    id=template_id,
                    name=template_info.get("name", template_id),
                    template=template_info.get("template", ""),
                    description=template_info.get("description", ""),
                    variables=template_info.get("variables", []),
                    is_custom=template_info.get("is_custom", False),
                )

            logger.info(f"Loaded {len(self.templates)} templates")

        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self.templates = {}

    def _create_default_config(self):
        """Create default templates configuration file."""
        default_config = {
            "_comment": "Message templates for quick responses",
            "templates": {}
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default config at {self.config_path}")

    def _save_templates(self):
        """Save templates to JSON config file."""
        try:
            # Load existing data to preserve comments
            if self.config_path.exists():
                with open(self.config_path) as f:
                    data = json.load(f)
            else:
                data = {"_comment": "Message templates for quick responses", "templates": {}}

            # Update templates
            data["templates"] = {}
            for template_id, template in self.templates.items():
                data["templates"][template_id] = {
                    "name": template.name,
                    "template": template.template,
                    "description": template.description,
                    "variables": template.variables,
                }
                if template.is_custom:
                    data["templates"][template_id]["is_custom"] = True

            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved templates to config")

        except Exception as e:
            logger.error(f"Error saving templates: {e}")

    def list_templates(self, include_custom: bool = True) -> List[Template]:
        """
        List all available templates.

        Args:
            include_custom: Include custom templates (default: True)

        Returns:
            List of Template objects sorted by name
        """
        templates = list(self.templates.values())
        if not include_custom:
            templates = [t for t in templates if not t.is_custom]
        return sorted(templates, key=lambda t: t.name)

    def get_template(self, template_id: str) -> Optional[Template]:
        """
        Get a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Template object or None if not found
        """
        return self.templates.get(template_id)

    def find_template(self, query: str) -> Optional[Template]:
        """
        Find a template by ID or partial name match.

        Args:
            query: Template ID or name to search for

        Returns:
            Best matching Template or None
        """
        # Exact ID match
        if query in self.templates:
            return self.templates[query]

        # Exact name match (case-insensitive)
        query_lower = query.lower()
        for template in self.templates.values():
            if template.name.lower() == query_lower:
                return template

        # Partial name match
        for template in self.templates.values():
            if query_lower in template.name.lower():
                return template

        # Partial ID match
        for template_id, template in self.templates.items():
            if query_lower in template_id.lower():
                return template

        return None

    def render_template(
        self,
        template_id: str,
        contact_name: Optional[str] = None,
        **variables
    ) -> str:
        """
        Render a template with variables.

        Args:
            template_id: Template identifier
            contact_name: Contact's name (auto-fills {name} variable)
            **variables: Additional variable values

        Returns:
            Rendered message string

        Raises:
            ValueError: If template not found or missing variables
        """
        template = self.find_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        # Auto-fill name from contact
        if contact_name and "name" not in variables:
            variables["name"] = contact_name

        return template.render(**variables)

    def create_template(
        self,
        template_id: str,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[List[str]] = None,
    ) -> Template:
        """
        Create a custom template.

        Args:
            template_id: Unique identifier (lowercase, hyphenated)
            name: Display name
            template: Template string with {variables}
            description: Description of when to use
            variables: List of variable names (auto-detected if not provided)

        Returns:
            Created Template object

        Raises:
            ValueError: If template_id already exists
        """
        # Normalize ID
        template_id = template_id.lower().replace(" ", "-")

        if template_id in self.templates:
            raise ValueError(f"Template '{template_id}' already exists")

        # Auto-detect variables from template string
        if variables is None:
            variables = re.findall(r'\{(\w+)\}', template)
            variables = list(set(variables))  # Deduplicate

        new_template = Template(
            id=template_id,
            name=name,
            template=template,
            description=description,
            variables=variables,
            is_custom=True,
            created_at=datetime.now(),
        )

        self.templates[template_id] = new_template
        self._save_templates()

        logger.info(f"Created custom template: {template_id}")
        return new_template

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a custom template.

        Args:
            template_id: Template identifier

        Returns:
            True if deleted, False if not found or not custom

        Raises:
            ValueError: If trying to delete a built-in template
        """
        template = self.templates.get(template_id)
        if not template:
            return False

        if not template.is_custom:
            raise ValueError(f"Cannot delete built-in template '{template_id}'")

        del self.templates[template_id]
        self._save_templates()

        logger.info(f"Deleted custom template: {template_id}")
        return True

    def suggest_template(self, context: str) -> Optional[Template]:
        """
        Suggest a template based on context/keywords.

        Args:
            context: Message context or keywords

        Returns:
            Suggested Template or None
        """
        context_lower = context.lower()

        # Keyword mapping
        keyword_map = {
            "thank": "thank-you",
            "thanks": "thank-you",
            "appreciate": "thank-you",
            "birthday": "birthday",
            "born": "birthday",
            "follow up": "follow-up",
            "following up": "follow-up",
            "check in": "thinking-of-you",
            "checking in": "thinking-of-you",
            "late": "running-late",
            "delayed": "running-late",
            "congrat": "congratulations",
            "awesome": "congratulations",
            "sorry": "sorry",
            "apologize": "sorry",
            "remind": "reminder",
            "don't forget": "reminder",
            "morning": "good-morning",
            "good morning": "good-morning",
            "meeting": "thanks-for-time",
        }

        for keyword, template_id in keyword_map.items():
            if keyword in context_lower:
                return self.templates.get(template_id)

        return None
