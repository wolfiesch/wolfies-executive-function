#!/usr/bin/env python3
"""
Example usage of the AI Life Planner core modules
Demonstrates basic CRUD operations for tasks, projects, and notes
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Database, Config, Task, Project, ParaCategory


def main():
    print("=" * 60)
    print("AI Life Planner - Example Usage")
    print("=" * 60)
    print()

    # Initialize database and config
    db = Database()
    config = Config()

    # ====================================================================
    # Example 1: Query PARA categories
    # ====================================================================
    print("1. PARA Categories")
    print("-" * 60)

    categories = db.execute("SELECT * FROM para_categories ORDER BY name")
    for row in categories:
        cat = ParaCategory.from_dict(dict(row))
        print(f"  [{cat.id}] {cat.name} ({cat.para_type})")
        if cat.description:
            print(f"      {cat.description}")

    # Get the "Professional" category ID for later use
    prof_cat = db.execute_one(
        "SELECT * FROM para_categories WHERE name = ?", ("Professional",)
    )
    prof_cat_id = prof_cat['id'] if prof_cat else None

    print()

    # ====================================================================
    # Example 2: Create a project
    # ====================================================================
    print("2. Creating a Project")
    print("-" * 60)

    project_id = db.execute_write(
        """
        INSERT INTO projects (name, description, status, para_category_id, start_date, target_end_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "Build AI Life Planner",
            "Create a comprehensive life planning system with AI assistance",
            "active",
            prof_cat_id,
            datetime.now(timezone.utc).date().isoformat(),
            (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()
        )
    )

    print(f"  ✓ Created project with ID: {project_id}")

    # Retrieve the project
    project_row = db.execute_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if project_row:
        project = Project.from_dict(dict(project_row))
        print(f"  - Name: {project.name}")
        print(f"  - Status: {project.status}")
        print(f"  - Target end: {project.target_end_date}")

    print()

    # ====================================================================
    # Example 3: Create tasks
    # ====================================================================
    print("3. Creating Tasks")
    print("-" * 60)

    tasks_data = [
        ("Set up database schema", "Create SQLite database with core tables", "done", 5),
        ("Build CLI interface", "Create command-line interface for task management", "todo", 4),
        ("Add natural language parsing", "Parse user input for task creation", "todo", 3),
        ("Write documentation", "Create user guide and API docs", "todo", 2),
    ]

    task_ids = []
    for title, description, status, priority in tasks_data:
        task_id = db.execute_write(
            """
            INSERT INTO tasks (
                title, description, status, priority, project_id, para_category_id,
                estimated_minutes, due_date, tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                status,
                priority,
                project_id,
                prof_cat_id,
                60,  # 1 hour estimate
                (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                json.dumps(["development", "ai", "productivity"])
            )
        )
        task_ids.append(task_id)
        status_emoji = "✓" if status == "done" else "○"
        print(f"  {status_emoji} [{task_id}] {title} (Priority: {priority})")

    print()

    # ====================================================================
    # Example 4: Query tasks
    # ====================================================================
    print("4. Querying Tasks")
    print("-" * 60)

    # Get all active tasks for the project
    tasks = db.execute(
        """
        SELECT * FROM tasks
        WHERE project_id = ? AND status != 'done'
        ORDER BY priority DESC, created_at ASC
        """,
        (project_id,)
    )

    print(f"  Active tasks for project '{project.name}':")
    for row in tasks:
        task = Task.from_dict(dict(row))
        print(f"  [{task.id}] {task.title}")
        print(f"      Priority: {task.priority}, Status: {task.status}")
        if task.tags:
            print(f"      Tags: {', '.join(task.tags)}")

    print()

    # ====================================================================
    # Example 5: Update a task
    # ====================================================================
    print("5. Updating a Task")
    print("-" * 60)

    # Mark the first todo task as in_progress
    first_todo = db.execute_one(
        "SELECT * FROM tasks WHERE status = 'todo' ORDER BY priority DESC LIMIT 1"
    )

    if first_todo:
        db.execute_write(
            """
            UPDATE tasks
            SET status = ?, scheduled_start = ?, scheduled_end = ?
            WHERE id = ?
            """,
            (
                "in_progress",
                datetime.now(timezone.utc).isoformat(),
                (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                first_todo['id']
            )
        )
        print(f"  ✓ Started task: {first_todo['title']}")
        print(f"    Status changed: todo → in_progress")

    print()

    # ====================================================================
    # Example 6: Statistics
    # ====================================================================
    print("6. Project Statistics")
    print("-" * 60)

    total_tasks = db.count("tasks", "project_id = ?", (project_id,))
    done_tasks = db.count("tasks", "project_id = ? AND status = 'done'", (project_id,))
    in_progress = db.count("tasks", "project_id = ? AND status = 'in_progress'", (project_id,))

    print(f"  Total tasks: {total_tasks}")
    print(f"  Completed: {done_tasks}")
    print(f"  In progress: {in_progress}")
    print(f"  Remaining: {total_tasks - done_tasks}")

    if total_tasks > 0:
        completion_rate = (done_tasks / total_tasks) * 100
        print(f"  Completion rate: {completion_rate:.1f}%")

    print()
    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
