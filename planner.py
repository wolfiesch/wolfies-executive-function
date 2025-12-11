#!/usr/bin/env python3
"""
AI Life Planner - Command Line Interface
Simple CLI for managing tasks, projects, and notes
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta
from typing import Optional
import json

from src.core import Database, Config, Task

# Initialize CLI app and console
app = typer.Typer(help="AI Life Planner - Your personal task and project manager")
console = Console()
db = Database()
config = Config()


# ============================================================================
# Helper Functions
# ============================================================================

def parse_relative_date(date_str: str) -> Optional[datetime]:
    """
    Parse relative date strings like 'today', 'tomorrow', 'monday'
    Returns datetime object or None
    """
    date_str = date_str.lower().strip()
    now = datetime.now()

    if date_str in ['today', 'td']:
        return now
    elif date_str in ['tomorrow', 'tmr', 'tom']:
        return now + timedelta(days=1)
    elif date_str in ['yesterday', 'yday']:
        return now - timedelta(days=1)

    # Days of week
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if date_str in days:
        target_day = days.index(date_str)
        current_day = now.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return now + timedelta(days=days_ahead)

    return None


def format_task(task: Task, include_id: bool = True) -> str:
    """Format task for display"""
    status_icons = {
        'todo': '○',
        'in_progress': '◐',
        'waiting': '◎',
        'done': '✓',
        'cancelled': '✗'
    }

    icon = status_icons.get(task.status, '○')
    priority_str = f"P{task.priority}" if task.priority != 3 else ""

    parts = []
    if include_id:
        parts.append(f"[dim]#{task.id}[/dim]")
    parts.append(f"{icon} {task.title}")
    if priority_str:
        parts.append(f"[yellow]{priority_str}[/yellow]")

    result = " ".join(parts)

    # Add due date if exists
    if task.due_date:
        if task.is_overdue():
            result += f" [red]⚠ Due {task.due_date.strftime('%m/%d')}[/red]"
        else:
            result += f" [cyan]Due {task.due_date.strftime('%m/%d')}[/cyan]"

    return result


# ============================================================================
# CLI Commands
# ============================================================================

@app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="Due date (today, tomorrow, monday, etc.)"),
    priority: int = typer.Option(3, "--priority", "-p", help="Priority (1-5, 5 is highest)"),
    project: Optional[str] = typer.Option(None, "--project", help="Project name"),
):
    """
    Add a new task

    Examples:
      planner add "Call John about project"
      planner add "Review proposal" --due tomorrow --priority 5
      planner add "Write report" -d friday -p 4
    """
    try:
        # Parse due date
        due_date = None
        if due:
            due_date = parse_relative_date(due)
            if not due_date:
                console.print(f"[red]Could not parse date: {due}[/red]")
                raise typer.Exit(1)

        # Get project ID if specified
        project_id = None
        if project:
            result = db.execute_one(
                "SELECT id FROM projects WHERE name LIKE ? AND status = 'active'",
                (f"%{project}%",)
            )
            if result:
                project_id = result['id']
            else:
                console.print(f"[yellow]Warning: Project '{project}' not found. Creating task without project.[/yellow]")

        # Insert task
        task_id = db.execute_write(
            """
            INSERT INTO tasks (title, priority, due_date, project_id, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                priority,
                due_date.isoformat() if due_date else None,
                project_id,
                json.dumps([])
            )
        )

        # Display success
        console.print(f"[green]✓[/green] Added task #{task_id}: {title}")
        if due_date:
            console.print(f"  Due: {due_date.strftime('%A, %B %d')}")
        if priority != 3:
            console.print(f"  Priority: {priority}")

    except Exception as e:
        console.print(f"[red]Error adding task: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def today():
    """
    Show today's tasks and schedule

    Displays:
    - Tasks due today or overdue
    - Tasks scheduled for today
    - High priority tasks without a due date
    """
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Query tasks
        tasks = db.execute(
            """
            SELECT * FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
              AND (
                  (due_date >= ? AND due_date < ?)
                  OR (due_date < ? AND status != 'done')
                  OR (scheduled_start >= ? AND scheduled_start < ?)
                  OR (priority >= 4 AND due_date IS NULL)
              )
            ORDER BY
                CASE WHEN due_date < ? THEN 0 ELSE 1 END,
                priority DESC,
                due_date ASC
            """,
            (
                today_start.isoformat(),
                today_end.isoformat(),
                today_start.isoformat(),
                today_start.isoformat(),
                today_end.isoformat(),
                today_start.isoformat()
            )
        )

        if not tasks:
            console.print(Panel(
                "[green]No tasks for today! 🎉[/green]",
                title="Today",
                border_style="green"
            ))
            return

        # Display tasks
        task_objects = [Task.from_dict(dict(row)) for row in tasks]

        console.print(Panel(
            f"[bold]{now.strftime('%A, %B %d, %Y')}[/bold]",
            title="Today",
            border_style="cyan"
        ))
        console.print()

        # Separate overdue and regular tasks
        overdue = [t for t in task_objects if t.is_overdue()]
        current = [t for t in task_objects if not t.is_overdue()]

        if overdue:
            console.print("[bold red]Overdue:[/bold red]")
            for task in overdue:
                console.print(f"  {format_task(task)}")
            console.print()

        if current:
            console.print("[bold]Today's Tasks:[/bold]")
            for task in current:
                console.print(f"  {format_task(task)}")

        console.print()
        console.print(f"[dim]Total: {len(task_objects)} tasks[/dim]")

    except Exception as e:
        console.print(f"[red]Error fetching tasks: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def done(task_id: int = typer.Argument(..., help="Task ID to mark as done")):
    """
    Mark a task as done

    Example:
      planner done 5
    """
    try:
        # Get task
        task_row = db.execute_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not task_row:
            console.print(f"[red]Task #{task_id} not found[/red]")
            raise typer.Exit(1)

        task = Task.from_dict(dict(task_row))

        # Update task
        db.execute_write(
            """
            UPDATE tasks
            SET status = 'done', completed_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), task_id)
        )

        console.print(f"[green]✓[/green] Completed: {task.title}")

    except Exception as e:
        console.print(f"[red]Error marking task as done: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (todo, in_progress, done)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project name"),
    all: bool = typer.Option(False, "--all", "-a", help="Show all tasks including done"),
):
    """
    List all tasks

    Examples:
      planner list
      planner list --status todo
      planner list --project "Life Planner"
      planner list --all
    """
    try:
        # Build query
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if not all:
            query += " AND status NOT IN ('done', 'cancelled')"

        if status:
            query += " AND status = ?"
            params.append(status)

        if project:
            # Get project ID
            project_row = db.execute_one(
                "SELECT id FROM projects WHERE name LIKE ?",
                (f"%{project}%",)
            )
            if project_row:
                query += " AND project_id = ?"
                params.append(project_row['id'])

        query += " ORDER BY priority DESC, due_date ASC, created_at DESC"

        # Execute query
        tasks = db.execute(query, tuple(params))

        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return

        # Display tasks
        task_objects = [Task.from_dict(dict(row)) for row in tasks]

        console.print(f"\n[bold]Tasks ({len(task_objects)}):[/bold]\n")

        for task in task_objects:
            console.print(f"  {format_task(task)}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error listing tasks: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show task statistics"""
    try:
        total = db.count("tasks")
        done = db.count("tasks", "status = 'done'")
        todo = db.count("tasks", "status = 'todo'")
        in_progress = db.count("tasks", "status = 'in_progress'")

        console.print("\n[bold]Task Statistics:[/bold]\n")
        console.print(f"  Total tasks: {total}")
        console.print(f"  ✓ Done: {done}")
        console.print(f"  ○ To-do: {todo}")
        console.print(f"  ◐ In progress: {in_progress}")

        if total > 0:
            completion_rate = (done / total) * 100
            console.print(f"\n  Completion rate: {completion_rate:.1f}%")

        console.print()

    except Exception as e:
        console.print(f"[red]Error fetching statistics: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
