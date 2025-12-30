"""
Task Agent for AI Life Planner
Handles all task-related operations: create, complete, list, search, update tasks.

This agent integrates with the existing Database and Task model to provide
natural language task management capabilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from .base_agent import BaseAgent, AgentResponse
from ..core.models import Task


class TaskAgent(BaseAgent):
    """
    Specialized agent for task management.

    Handles intents:
    - add_task: Create a new task with NL parsing
    - complete_task: Mark task(s) as done
    - list_tasks: List tasks with various filters
    - search_tasks: Search tasks by text
    - update_task: Modify existing task properties

    Integrates with the Database layer for persistence and the Task model
    for data representation.
    """

    # Supported intents for this agent
    INTENTS = [
        "add_task",
        "complete_task",
        "list_tasks",
        "search_tasks",
        "update_task",
        "delete_task",
        "get_task"
    ]

    # Priority keywords for NL parsing (maps keywords to priority 1-5)
    PRIORITY_KEYWORDS = {
        5: ["urgent", "critical", "asap", "emergency", "immediately", "high priority"],
        4: ["important", "high", "soon"],
        3: ["normal", "medium", "moderate"],
        2: ["low", "whenever", "someday"],
        1: ["optional", "maybe", "if time", "backlog"]
    }

    # Relative date keywords
    DATE_KEYWORDS = {
        "today": 0,
        "tonight": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
        "next week": 7,
        "next monday": None,  # Handled specially
        "next tuesday": None,
        "next wednesday": None,
        "next thursday": None,
        "next friday": None,
        "next saturday": None,
        "next sunday": None,
    }

    def __init__(self, db, config):
        """Initialize the Task Agent."""
        super().__init__(db, config, "task")

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents."""
        return self.INTENTS

    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.INTENTS

    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a task-related intent.

        Routes to the appropriate handler based on intent type.

        Args:
            intent: One of the supported task intents
            context: Request context with parameters

        Returns:
            AgentResponse with operation result
        """
        self.log_action(f"processing_{intent}", {"context_keys": list(context.keys())})

        handlers = {
            "add_task": self._handle_add_task,
            "complete_task": self._handle_complete_task,
            "list_tasks": self._handle_list_tasks,
            "search_tasks": self._handle_search_tasks,
            "update_task": self._handle_update_task,
            "delete_task": self._handle_delete_task,
            "get_task": self._handle_get_task,
        }

        handler = handlers.get(intent)
        if not handler:
            return AgentResponse.error(f"Unknown intent: {intent}")

        try:
            return handler(context)
        except Exception as e:
            self.logger.error(f"Error processing {intent}: {e}", exc_info=True)
            return AgentResponse.error(f"Failed to process {intent}: {str(e)}")

    # =========================================================================
    # Intent Handlers
    # =========================================================================

    def _handle_add_task(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Handle task creation.

        Supports two modes:
        1. Structured: title, description, priority, due_date provided directly
        2. Natural language: text field parsed for task details

        Context params:
            text (str): Natural language task description
            OR
            title (str): Task title
            description (str, optional): Task description
            priority (int, optional): Priority 1-5
            due_date (str, optional): Due date ISO string
            project_id (int, optional): Associated project
            tags (list, optional): Task tags
        """
        # Check if we have natural language input
        if "text" in context and context["text"]:
            parsed = self._parse_task_from_text(context["text"])
            # Merge parsed values with any explicit overrides from context
            for key, value in parsed.items():
                if key not in context or context[key] is None:
                    context[key] = value

        # Validate required fields
        if not context.get("title"):
            return AgentResponse.error("Task title is required")

        # Determine priority: use context value if present and not None, else config default
        default_priority = self.get_config_value("default_task_priority", default=3) or 3
        priority = context.get("priority")
        if priority is None:
            priority = default_priority

        # Build task data
        task_data = {
            "title": context["title"],
            "description": context.get("description"),
            "priority": priority,
            "status": "todo",
            "project_id": context.get("project_id"),
            "para_category_id": context.get("para_category_id"),
            "due_date": self._parse_due_date(context.get("due_date")),
            "estimated_minutes": context.get("estimated_minutes"),
            "tags": json.dumps(context.get("tags", [])) if context.get("tags") else None,
            "context": json.dumps(context.get("task_context", {})) if context.get("task_context") else None,
        }

        # Insert into database
        try:
            task_id = self._insert_task(task_data)
            created_task = self._get_task_by_id(task_id)

            return AgentResponse.ok(
                message=f"Task created: '{task_data['title']}'",
                data={
                    "task_id": task_id,
                    "task": created_task
                },
                suggestions=[
                    f"List all tasks: 'show my tasks'",
                    f"Add due date: 'update task {task_id} due tomorrow'",
                    f"Set priority: 'mark task {task_id} as high priority'"
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return AgentResponse.error(f"Failed to create task: {str(e)}")

    def _handle_complete_task(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Mark task(s) as completed.

        Context params:
            task_id (int): Single task ID to complete
            OR
            task_ids (list): Multiple task IDs to complete
            OR
            search (str): Search text to find task to complete
        """
        task_ids = []

        if "task_id" in context:
            task_ids = [context["task_id"]]
        elif "task_ids" in context:
            task_ids = context["task_ids"]
        elif "search" in context:
            # Find task by search
            found_tasks = self._search_tasks_by_text(context["search"], limit=1)
            if found_tasks:
                task_ids = [found_tasks[0]["id"]]
            else:
                return AgentResponse.error(
                    f"No task found matching: '{context['search']}'"
                )
        else:
            return AgentResponse.error("No task specified to complete")

        completed = []
        failed = []

        for task_id in task_ids:
            try:
                success = self._update_task_status(task_id, "done")
                if success:
                    completed.append(task_id)
                else:
                    failed.append(task_id)
            except Exception as e:
                self.logger.error(f"Failed to complete task {task_id}: {e}")
                failed.append(task_id)

        if not completed:
            return AgentResponse.error(
                f"Failed to complete tasks: {failed}"
            )

        message = f"Completed {len(completed)} task(s)"
        if failed:
            message += f" ({len(failed)} failed)"

        return AgentResponse.ok(
            message=message,
            data={
                "completed_ids": completed,
                "failed_ids": failed
            },
            suggestions=["Show remaining tasks", "Review completed tasks today"]
        )

    def _handle_list_tasks(self, context: Dict[str, Any]) -> AgentResponse:
        """
        List tasks with optional filters.

        Context params:
            status (str or list): Filter by status (todo, in_progress, done, etc.)
            priority (int): Filter by priority
            project_id (int): Filter by project
            due_before (str): Tasks due before date
            due_after (str): Tasks due after date
            limit (int): Max tasks to return (default 20)
            include_completed (bool): Include done tasks (default False)
        """
        filters = {}

        # Status filter
        if "status" in context:
            filters["status"] = context["status"]
        elif not context.get("include_completed", False):
            # Default to non-completed tasks
            filters["exclude_status"] = ["done", "cancelled"]

        # Other filters
        if "priority" in context:
            filters["priority"] = context["priority"]
        if "project_id" in context:
            filters["project_id"] = context["project_id"]
        if "para_category_id" in context:
            filters["para_category_id"] = context["para_category_id"]
        if "due_before" in context:
            filters["due_before"] = self._parse_due_date(context["due_before"])
        if "due_after" in context:
            filters["due_after"] = self._parse_due_date(context["due_after"])

        limit = context.get("limit", 20)

        tasks = self._fetch_tasks(filters, limit)

        if not tasks:
            return AgentResponse.ok(
                message="No tasks found matching the criteria",
                data={"tasks": [], "count": 0}
            )

        return AgentResponse.ok(
            message=f"Found {len(tasks)} task(s)",
            data={
                "tasks": tasks,
                "count": len(tasks),
                "filters_applied": filters
            }
        )

    def _handle_search_tasks(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Search tasks by text.

        Context params:
            query (str): Search query
            limit (int): Max results (default 10)
            include_completed (bool): Include done tasks (default False)
        """
        validation = self.validate_required_params(context, ["query"])
        if validation:
            return validation

        query = context["query"]
        limit = context.get("limit", 10)
        include_completed = context.get("include_completed", False)

        tasks = self._search_tasks_by_text(
            query,
            limit=limit,
            include_completed=include_completed
        )

        return AgentResponse.ok(
            message=f"Found {len(tasks)} task(s) matching '{query}'",
            data={
                "tasks": tasks,
                "count": len(tasks),
                "query": query
            }
        )

    def _handle_update_task(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Update task properties.

        Context params:
            task_id (int): Task to update
            title (str, optional): New title
            description (str, optional): New description
            priority (int, optional): New priority
            status (str, optional): New status
            due_date (str, optional): New due date
            project_id (int, optional): New project association
            tags (list, optional): New tags
        """
        validation = self.validate_required_params(context, ["task_id"])
        if validation:
            return validation

        task_id = context["task_id"]

        # Build update data
        update_fields = {}
        if "title" in context:
            update_fields["title"] = context["title"]
        if "description" in context:
            update_fields["description"] = context["description"]
        if "priority" in context:
            update_fields["priority"] = context["priority"]
        if "status" in context:
            update_fields["status"] = context["status"]
        if "due_date" in context:
            update_fields["due_date"] = self._parse_due_date(context["due_date"])
        if "project_id" in context:
            update_fields["project_id"] = context["project_id"]
        if "tags" in context:
            update_fields["tags"] = json.dumps(context["tags"])
        if "estimated_minutes" in context:
            update_fields["estimated_minutes"] = context["estimated_minutes"]

        if not update_fields:
            return AgentResponse.error("No fields to update provided")

        try:
            success = self._update_task(task_id, update_fields)
            if success:
                updated_task = self._get_task_by_id(task_id)
                return AgentResponse.ok(
                    message=f"Task {task_id} updated",
                    data={"task": updated_task}
                )
            else:
                return AgentResponse.error(f"Task {task_id} not found")
        except Exception as e:
            return AgentResponse.error(f"Failed to update task: {str(e)}")

    def _handle_delete_task(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Delete a task (soft delete by marking as cancelled).

        Context params:
            task_id (int): Task to delete
        """
        validation = self.validate_required_params(context, ["task_id"])
        if validation:
            return validation

        task_id = context["task_id"]

        # Soft delete by marking as cancelled
        try:
            success = self._update_task_status(task_id, "cancelled")
            if success:
                return AgentResponse.ok(
                    message=f"Task {task_id} cancelled",
                    data={"task_id": task_id}
                )
            else:
                return AgentResponse.error(f"Task {task_id} not found")
        except Exception as e:
            return AgentResponse.error(f"Failed to delete task: {str(e)}")

    def _handle_get_task(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Get a single task by ID.

        Context params:
            task_id (int): Task ID to retrieve
        """
        validation = self.validate_required_params(context, ["task_id"])
        if validation:
            return validation

        task = self._get_task_by_id(context["task_id"])
        if task:
            return AgentResponse.ok(
                message=f"Task: {task['title']}",
                data={"task": task}
            )
        else:
            return AgentResponse.error(f"Task {context['task_id']} not found")

    # =========================================================================
    # Natural Language Parsing
    # =========================================================================

    def _parse_task_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract task properties.

        Extracts:
        - Title (main task description)
        - Priority (from keywords)
        - Due date (from relative/absolute dates)
        - Tags (from hashtags)
        - Estimated time (from duration mentions)

        Args:
            text: Natural language task description

        Returns:
            Dictionary with parsed task properties
        """
        result = {
            "title": text,
            "priority": None,
            "due_date": None,
            "tags": [],
            "estimated_minutes": None
        }

        working_text = text.lower()

        # Extract priority from keywords (find highest priority and remove all matching keywords)
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in working_text:
                    if result["priority"] is None:
                        result["priority"] = priority
                    # Remove ALL priority keywords from title (not just the first match)
                    result["title"] = re.sub(
                        rf'\b{re.escape(keyword)}\b', '', result["title"], flags=re.IGNORECASE
                    ).strip()

        # Extract due date
        due_date, title_cleaned = self._extract_due_date(result["title"])
        if due_date:
            result["due_date"] = due_date
            result["title"] = title_cleaned

        # Extract hashtags as tags
        tags = re.findall(r'#(\w+)', text)
        if tags:
            result["tags"] = tags
            result["title"] = re.sub(r'#\w+', '', result["title"]).strip()

        # Extract time estimates (e.g., "30 minutes", "2 hours", "1h")
        time_patterns = [
            (r'(\d+)\s*hours?', lambda m: int(m.group(1)) * 60),
            (r'(\d+)\s*h\b', lambda m: int(m.group(1)) * 60),
            (r'(\d+)\s*minutes?', lambda m: int(m.group(1))),
            (r'(\d+)\s*mins?', lambda m: int(m.group(1))),
            (r'(\d+)\s*m\b', lambda m: int(m.group(1))),
        ]
        for pattern, converter in time_patterns:
            match = re.search(pattern, working_text)
            if match:
                result["estimated_minutes"] = converter(match)
                result["title"] = re.sub(pattern, '', result["title"], flags=re.IGNORECASE).strip()
                break

        # Clean up title (remove extra spaces, orphan # symbols, leading/trailing punctuation)
        result["title"] = re.sub(r'#\s*(?!\w)', '', result["title"])  # Remove orphan # symbols
        result["title"] = re.sub(r'\s+', ' ', result["title"]).strip(' ,-:#')

        return result

    def _extract_due_date(self, text: str) -> Tuple[Optional[str], str]:
        """
        Extract due date from text and return cleaned text.

        Args:
            text: Text that may contain date references

        Returns:
            Tuple of (ISO date string or None, cleaned text)
        """
        text_lower = text.lower()
        today = datetime.now(timezone.utc).date()

        # Check for relative date keywords
        date_patterns = [
            (r'\btoday\b', today),
            (r'\btonight\b', today),
            (r'\btomorrow\b', today + timedelta(days=1)),
            (r'\bday after tomorrow\b', today + timedelta(days=2)),
            (r'\bnext week\b', today + timedelta(days=7)),
        ]

        for pattern, date_value in date_patterns:
            if re.search(pattern, text_lower):
                cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                return date_value.isoformat(), cleaned

        # Check for "by <day>" or "on <day>"
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, day in enumerate(days_of_week):
            patterns = [
                rf'\b(by|on|next)\s+{day}\b',
                rf'\bdue\s+{day}\b',
            ]
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Calculate next occurrence of this day
                    days_ahead = idx - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    target_date = today + timedelta(days=days_ahead)
                    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                    return target_date.isoformat(), cleaned

        # Check for "in X days"
        in_days_match = re.search(r'\bin\s+(\d+)\s+days?\b', text_lower)
        if in_days_match:
            days = int(in_days_match.group(1))
            target_date = today + timedelta(days=days)
            cleaned = re.sub(r'\bin\s+\d+\s+days?\b', '', text, flags=re.IGNORECASE).strip()
            return target_date.isoformat(), cleaned

        # Check for explicit date formats (YYYY-MM-DD, MM/DD, etc.)
        explicit_patterns = [
            (r'\b(\d{4}-\d{2}-\d{2})\b', '%Y-%m-%d'),
            (r'\b(\d{1,2}/\d{1,2}/\d{4})\b', '%m/%d/%Y'),
            (r'\b(\d{1,2}/\d{1,2})\b', '%m/%d'),  # Assumes current year
        ]
        for pattern, date_format in explicit_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    if date_format == '%m/%d':
                        date_str = f"{date_str}/{today.year}"
                        date_format = '%m/%d/%Y'
                    parsed_date = datetime.strptime(date_str, date_format).date()
                    cleaned = text[:match.start()] + text[match.end():]
                    return parsed_date.isoformat(), cleaned.strip()
                except ValueError:
                    continue

        return None, text

    def _parse_due_date(self, due_date: Any) -> Optional[str]:
        """
        Parse and normalize due date input.

        Args:
            due_date: String date, datetime, or None

        Returns:
            ISO format datetime string or None
        """
        if due_date is None:
            return None
        if isinstance(due_date, datetime):
            return due_date.isoformat()
        if isinstance(due_date, str):
            # Already ISO format
            if 'T' in due_date or len(due_date) == 10:
                return due_date
            # Try parsing relative dates
            extracted, _ = self._extract_due_date(due_date)
            return extracted
        return None

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _insert_task(self, task_data: Dict[str, Any]) -> int:
        """Insert a new task and return its ID."""
        query = """
            INSERT INTO tasks (
                title, description, status, priority, project_id,
                para_category_id, due_date, estimated_minutes, tags, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task_data["title"],
            task_data.get("description"),
            task_data.get("status", "todo"),
            task_data.get("priority", 3),
            task_data.get("project_id"),
            task_data.get("para_category_id"),
            task_data.get("due_date"),
            task_data.get("estimated_minutes"),
            task_data.get("tags"),
            task_data.get("context"),
        )
        return self.db.execute_write(query, params)

    def _get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single task by ID."""
        query = "SELECT * FROM tasks WHERE id = ?"
        row = self.db.execute_one(query, (task_id,))
        return self.db.row_to_dict(row)

    def _update_task_status(self, task_id: int, status: str) -> bool:
        """Update task status and set completed_at if done."""
        if status == "done":
            query = """
                UPDATE tasks
                SET status = ?, completed_at = strftime('%Y-%m-%d %H:%M:%f', 'now', 'utc')
                WHERE id = ?
            """
        else:
            query = "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?"
        result = self.db.execute_write(query, (status, task_id))
        return result > 0

    def _update_task(self, task_id: int, fields: Dict[str, Any]) -> bool:
        """Update specified task fields."""
        if not fields:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        params = tuple(fields.values()) + (task_id,)

        result = self.db.execute_write(query, params)
        return result > 0

    def _fetch_tasks(self, filters: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch tasks with filters."""
        conditions = []
        params = []

        if "status" in filters:
            if isinstance(filters["status"], list):
                placeholders = ",".join("?" * len(filters["status"]))
                conditions.append(f"status IN ({placeholders})")
                params.extend(filters["status"])
            else:
                conditions.append("status = ?")
                params.append(filters["status"])

        if "exclude_status" in filters:
            placeholders = ",".join("?" * len(filters["exclude_status"]))
            conditions.append(f"status NOT IN ({placeholders})")
            params.extend(filters["exclude_status"])

        if "priority" in filters:
            conditions.append("priority = ?")
            params.append(filters["priority"])

        if "project_id" in filters:
            conditions.append("project_id = ?")
            params.append(filters["project_id"])

        if "para_category_id" in filters:
            conditions.append("para_category_id = ?")
            params.append(filters["para_category_id"])

        if "due_before" in filters:
            conditions.append("due_date <= ?")
            params.append(filters["due_before"])

        if "due_after" in filters:
            conditions.append("due_date >= ?")
            params.append(filters["due_after"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM tasks
            WHERE {where_clause}
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date ASC,
                priority DESC,
                created_at DESC
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.execute(query, tuple(params))
        return self.db.rows_to_dicts(rows)

    def _search_tasks_by_text(self, query: str, limit: int = 10,
                               include_completed: bool = False) -> List[Dict[str, Any]]:
        """Search tasks by title and description."""
        search_term = f"%{query}%"

        status_filter = "" if include_completed else "AND status NOT IN ('done', 'cancelled')"

        sql = f"""
            SELECT * FROM tasks
            WHERE (title LIKE ? OR description LIKE ?)
            {status_filter}
            ORDER BY
                CASE
                    WHEN title LIKE ? THEN 1  -- Exact match in title
                    WHEN title LIKE ? THEN 2  -- Starts with
                    ELSE 3
                END,
                priority DESC,
                due_date ASC
            LIMIT ?
        """
        params = (
            search_term,
            search_term,
            query,
            f"{query}%",
            limit
        )

        rows = self.db.execute(sql, params)
        return self.db.rows_to_dicts(rows)
