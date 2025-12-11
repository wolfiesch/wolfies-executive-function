"""
Data models for AI Life Planner
Defines core data structures for tasks, projects, notes, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class ParaCategory:
    """PARA category (Project, Area, Resource, Archive)"""
    id: Optional[int] = None
    name: str = ""
    para_type: str = "area"  # 'project', 'area', 'resource', 'archive'
    description: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParaCategory':
        """Create ParaCategory from database row dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            para_type=data.get('para_type', 'area'),
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            created_at=cls._parse_datetime(data.get('created_at')),
            updated_at=cls._parse_datetime(data.get('updated_at'))
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from database"""
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        return None


@dataclass
class Project:
    """Project data model"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    status: str = "active"  # 'active', 'on_hold', 'completed', 'cancelled'
    para_category_id: Optional[int] = None
    start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    archived: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project from database row dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description'),
            status=data.get('status', 'active'),
            para_category_id=data.get('para_category_id'),
            start_date=cls._parse_date(data.get('start_date')),
            target_end_date=cls._parse_date(data.get('target_end_date')),
            actual_end_date=cls._parse_date(data.get('actual_end_date')),
            archived=bool(data.get('archived', False)),
            created_at=cls._parse_datetime(data.get('created_at')),
            updated_at=cls._parse_datetime(data.get('updated_at')),
            metadata=cls._parse_json(data.get('metadata'))
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from database"""
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from database"""
        if date_str:
            try:
                return datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse JSON string from database"""
        if json_str:
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


@dataclass
class Task:
    """Task data model"""
    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    status: str = "todo"  # 'todo', 'in_progress', 'waiting', 'done', 'cancelled'
    priority: int = 3  # 1-5, where 5 is highest priority
    para_category_id: Optional[int] = None
    project_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    due_date: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    context: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create Task from database row dictionary"""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description'),
            status=data.get('status', 'todo'),
            priority=data.get('priority', 3),
            para_category_id=data.get('para_category_id'),
            project_id=data.get('project_id'),
            parent_task_id=data.get('parent_task_id'),
            estimated_minutes=data.get('estimated_minutes'),
            actual_minutes=data.get('actual_minutes'),
            due_date=cls._parse_datetime(data.get('due_date')),
            scheduled_start=cls._parse_datetime(data.get('scheduled_start')),
            scheduled_end=cls._parse_datetime(data.get('scheduled_end')),
            completed_at=cls._parse_datetime(data.get('completed_at')),
            created_at=cls._parse_datetime(data.get('created_at')),
            updated_at=cls._parse_datetime(data.get('updated_at')),
            tags=cls._parse_json_list(data.get('tags')),
            context=cls._parse_json(data.get('context'))
        )

    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if self.due_date and self.status not in ['done', 'cancelled']:
            return datetime.utcnow() > self.due_date
        return False

    def is_scheduled(self) -> bool:
        """Check if task has scheduled time"""
        return self.scheduled_start is not None and self.scheduled_end is not None

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from database"""
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse JSON string from database"""
        if json_str:
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json_list(json_str: Optional[str]) -> List[str]:
        """Parse JSON array string from database"""
        if json_str:
            try:
                result = json.loads(json_str)
                return result if isinstance(result, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []


@dataclass
class Note:
    """Note data model"""
    id: Optional[int] = None
    title: str = ""
    file_path: str = ""
    note_type: str = "note"  # 'note', 'journal', 'meeting', 'reference'
    para_category_id: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    word_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """Create Note from database row dictionary"""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            file_path=data.get('file_path', ''),
            note_type=data.get('note_type', 'note'),
            para_category_id=data.get('para_category_id'),
            tags=cls._parse_json_list(data.get('tags')),
            created_at=cls._parse_datetime(data.get('created_at')),
            updated_at=cls._parse_datetime(data.get('updated_at')),
            word_count=data.get('word_count', 0),
            metadata=cls._parse_json(data.get('metadata'))
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from database"""
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse JSON string from database"""
        if json_str:
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json_list(json_str: Optional[str]) -> List[str]:
        """Parse JSON array string from database"""
        if json_str:
            try:
                result = json.loads(json_str)
                return result if isinstance(result, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []


@dataclass
class CalendarEvent:
    """Calendar event data model"""
    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: bool = False
    calendar_source: str = "internal"
    external_id: Optional[str] = None
    status: str = "confirmed"  # 'confirmed', 'tentative', 'cancelled'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from database row dictionary"""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description'),
            location=data.get('location'),
            start_time=cls._parse_datetime(data.get('start_time')),
            end_time=cls._parse_datetime(data.get('end_time')),
            all_day=bool(data.get('all_day', False)),
            calendar_source=data.get('calendar_source', 'internal'),
            external_id=data.get('external_id'),
            status=data.get('status', 'confirmed'),
            created_at=cls._parse_datetime(data.get('created_at')),
            updated_at=cls._parse_datetime(data.get('updated_at')),
            metadata=cls._parse_json(data.get('metadata'))
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from database"""
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _parse_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse JSON string from database"""
        if json_str:
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
