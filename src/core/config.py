"""
Configuration management for AI Life Planner
Handles loading and saving user preferences and settings
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for the life planner system"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Path to configuration directory (defaults to ./config)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.config_dir / "settings.json"
        self.para_file = self.config_dir / "para_categories.json"
        self.preferences_file = self.config_dir / "preferences.json"

        # Load configurations
        self.settings = self._load_json(self.settings_file, self._default_settings())
        self.para_config = self._load_json(self.para_file, self._default_para_config())
        self.preferences = self._load_json(self.preferences_file, self._default_preferences())

    def _load_json(self, file_path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        """Load JSON file or return default if file doesn't exist"""
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            # Create file with defaults
            self._save_json(file_path, default)
            return default

    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _default_settings(self) -> Dict[str, Any]:
        """Default system settings"""
        return {
            "database_path": "data/database/planner.db",
            "notes_directory": "data/notes",
            "attachments_directory": "data/attachments",
            "timezone": "America/Los_Angeles",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M",
            "first_day_of_week": "monday"
        }

    def _default_para_config(self) -> Dict[str, Any]:
        """Default PARA method configuration"""
        return {
            "areas": [
                {"name": "Personal", "description": "Personal life and self-development"},
                {"name": "Professional", "description": "Work and career"},
                {"name": "Health", "description": "Physical and mental health"},
                {"name": "Relationships", "description": "Family, friends, and social connections"},
                {"name": "Finance", "description": "Money management and investments"},
                {"name": "Learning", "description": "Education and skill development"}
            ],
            "auto_archive_completed_projects": True,
            "archive_after_days": 30
        }

    def _default_preferences(self) -> Dict[str, Any]:
        """Default user preferences"""
        return {
            "daily_review_time": "09:00",
            "weekly_review_day": "sunday",
            "weekly_review_time": "18:00",
            "work_hours_start": "09:00",
            "work_hours_end": "17:00",
            "deep_work_block_duration": 120,
            "break_duration": 15,
            "default_task_priority": 3,
            "notifications_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00"
        }

    def get(self, key: str, section: str = "settings", default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key
            section: Configuration section ('settings', 'para', 'preferences')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        section_map = {
            "settings": self.settings,
            "para": self.para_config,
            "preferences": self.preferences
        }

        return section_map.get(section, {}).get(key, default)

    def set(self, key: str, value: Any, section: str = "settings") -> None:
        """
        Set configuration value and save to disk

        Args:
            key: Configuration key
            value: Value to set
            section: Configuration section ('settings', 'para', 'preferences')
        """
        section_map = {
            "settings": (self.settings, self.settings_file),
            "para": (self.para_config, self.para_file),
            "preferences": (self.preferences, self.preferences_file)
        }

        if section in section_map:
            config_dict, file_path = section_map[section]
            config_dict[key] = value
            self._save_json(file_path, config_dict)

    def get_database_path(self) -> Path:
        """Get full path to database file"""
        base_path = Path(__file__).parent.parent.parent
        return base_path / self.settings["database_path"]

    def get_notes_directory(self) -> Path:
        """Get full path to notes directory"""
        base_path = Path(__file__).parent.parent.parent
        return base_path / self.settings["notes_directory"]

    def get_attachments_directory(self) -> Path:
        """Get full path to attachments directory"""
        base_path = Path(__file__).parent.parent.parent
        return base_path / self.settings["attachments_directory"]
