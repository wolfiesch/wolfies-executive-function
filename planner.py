#!/usr/bin/env python3
"""
AI Life Planner - Command Line Interface
Simple CLI for managing tasks, projects, calendar events, and notes
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
import re

from src.core import Database, Config, Task, CalendarEvent
from src.dashboard import DashboardAggregator, DashboardFormatter

# Initialize CLI app and console
app = typer.Typer(help="AI Life Planner - Your personal task and project manager")
event_app = typer.Typer(help="Calendar event management")
app.add_typer(event_app, name="event")

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


def parse_time_expression(time_str: str) -> Optional[datetime]:
    """
    Parse various time formats for event creation.

    Supports:
        - "2pm", "2:30pm", "14:00" - Today at specified time
        - "tomorrow 3pm" - Tomorrow at 3pm
        - "monday 10am" - Next Monday at 10am
        - "12/20 2pm" - Specific date at 2pm

    Returns:
        datetime or None if parsing fails
    """
    time_str = time_str.lower().strip()
    now = datetime.now()

    # Pattern for time: "2pm", "2:30pm", "14:00", "2:30 pm"
    time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'

    def extract_time(s: str) -> Optional[tuple]:
        """Extract hour and minute from time string."""
        match = re.search(time_pattern, s, re.IGNORECASE)
        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        meridiem = match.group(3)

        # Handle 12-hour format
        if meridiem:
            if meridiem.lower() == 'pm' and hour < 12:
                hour += 12
            elif meridiem.lower() == 'am' and hour == 12:
                hour = 0

        # Validate
        if hour > 23 or minute > 59:
            return None

        return (hour, minute)

    # Try to extract date component
    date_part = now.date()

    # Check for "tomorrow"
    if 'tomorrow' in time_str:
        date_part = (now + timedelta(days=1)).date()
        time_str = time_str.replace('tomorrow', '').strip()

    # Check for day of week
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for day in days:
        if day in time_str:
            target_day = days.index(day)
            current_day = now.weekday()
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            date_part = (now + timedelta(days=days_ahead)).date()
            time_str = time_str.replace(day, '').strip()
            break

    # Check for date like "12/20" or "12-20"
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', time_str)
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        try:
            date_part = now.replace(month=month, day=day).date()
            # If date is in past, assume next year
            if date_part < now.date():
                date_part = date_part.replace(year=date_part.year + 1)
        except ValueError:
            pass
        time_str = re.sub(r'\d{1,2}[/-]\d{1,2}', '', time_str).strip()

    # Extract time component
    time_tuple = extract_time(time_str)
    if not time_tuple:
        return None

    hour, minute = time_tuple

    return datetime.combine(date_part, datetime.min.time().replace(hour=hour, minute=minute))


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
    estimate: Optional[int] = typer.Option(None, "--estimate", "-e", help="Estimated minutes"),
):
    """
    Add a new task

    Examples:
      planner add "Call John about project"
      planner add "Review proposal" --due tomorrow --priority 5
      planner add "Write report" -d friday -p 4 --estimate 120
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
            INSERT INTO tasks (title, priority, due_date, project_id, estimated_minutes, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                priority,
                due_date.isoformat() if due_date else None,
                project_id,
                estimate,
                json.dumps([])
            )
        )

        # Display success
        console.print(f"[green]✓[/green] Added task #{task_id}: {title}")
        if due_date:
            console.print(f"  Due: {due_date.strftime('%A, %B %d')}")
        if priority != 3:
            console.print(f"  Priority: {priority}")
        if estimate:
            console.print(f"  Estimate: {estimate} minutes")

    except Exception as e:
        console.print(f"[red]Error adding task: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def today(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed task breakdowns"),
):
    """
    Show today's unified dashboard

    Displays your day at a glance:
    - Top priorities (smart-ranked)
    - Calendar events timeline
    - Overdue tasks warning
    - Available time analysis
    - Progress stats
    """
    try:
        # Use the new dashboard
        aggregator = DashboardAggregator(db, config)
        data = aggregator.aggregate()

        formatter = DashboardFormatter(console)
        formatter.render_dashboard(data, verbose=verbose)

    except Exception as e:
        console.print(f"[red]Error loading dashboard: {e}[/red]")
        import traceback
        traceback.print_exc()
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


@app.command("list")
def list_tasks(
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


# ============================================================================
# Event Subcommands
# ============================================================================

@event_app.command("add")
def event_add(
    title: str = typer.Argument(..., help="Event title"),
    start: str = typer.Option(..., "--start", "-s", help="Start time (e.g., '2pm', 'tomorrow 3pm', 'monday 10am')"),
    duration: int = typer.Option(60, "--duration", "-d", help="Duration in minutes (default: 60)"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    description: Optional[str] = typer.Option(None, "--desc", help="Event description"),
    all_day: bool = typer.Option(False, "--all-day", help="All-day event"),
):
    """
    Add a new calendar event

    Examples:
      planner event add "Team Meeting" --start "2pm" --duration 60
      planner event add "Lunch with John" -s "tomorrow 12:30pm" -d 90 -l "Cafe Roma"
      planner event add "Conference" --start "monday 9am" --all-day
    """
    try:
        # Parse start time
        start_time = parse_time_expression(start)
        if not start_time:
            console.print(f"[red]Could not parse time: {start}[/red]")
            console.print("[dim]Try formats like: 2pm, 2:30pm, tomorrow 3pm, monday 10am[/dim]")
            raise typer.Exit(1)

        # Calculate end time
        if all_day:
            end_time = start_time.replace(hour=23, minute=59)
        else:
            end_time = start_time + timedelta(minutes=duration)

        # Insert event
        event_id = db.execute_write(
            """
            INSERT INTO calendar_events (title, description, location, start_time, end_time, all_day, calendar_source, status)
            VALUES (?, ?, ?, ?, ?, ?, 'internal', 'confirmed')
            """,
            (
                title,
                description,
                location,
                start_time.isoformat(),
                end_time.isoformat(),
                1 if all_day else 0,
            )
        )

        # Display success
        console.print(f"[green]✓[/green] Added event #{event_id}: {title}")
        if all_day:
            console.print(f"  Date: {start_time.strftime('%A, %B %d')} (all day)")
        else:
            console.print(f"  Time: {start_time.strftime('%A, %B %d at %I:%M %p')} - {end_time.strftime('%I:%M %p')}")
        if location:
            console.print(f"  Location: {location}")

    except Exception as e:
        console.print(f"[red]Error adding event: {e}[/red]")
        raise typer.Exit(1)


@event_app.command("list")
def event_list(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to show (default: 7)"),
):
    """
    List upcoming calendar events

    Examples:
      planner event list
      planner event list --days 14
    """
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now + timedelta(days=days)

        # Query events (include all of today's events, even past ones)
        events = db.execute(
            """
            SELECT * FROM calendar_events
            WHERE status != 'cancelled'
            AND start_time >= ? AND start_time <= ?
            ORDER BY start_time ASC
            """,
            (today_start.isoformat(), end_date.isoformat())
        )

        if not events:
            console.print(f"[yellow]No events in the next {days} days[/yellow]")
            return

        # Display events
        console.print(f"\n[bold]Upcoming Events (next {days} days):[/bold]\n")

        current_date = None
        for row in events:
            event = CalendarEvent.from_dict(dict(row))

            # Group by date
            event_date = event.start_time.date() if event.start_time else None
            if event_date != current_date:
                current_date = event_date
                console.print(f"\n  [bold cyan]{event.start_time.strftime('%A, %B %d')}[/bold cyan]")

            # Format time
            if event.all_day:
                time_str = "[dim]All day[/dim]"
            elif event.start_time and event.end_time:
                time_str = f"{event.start_time.strftime('%I:%M %p').lstrip('0')} - {event.end_time.strftime('%I:%M %p').lstrip('0')}"
            else:
                time_str = "[dim]---[/dim]"

            location_str = f" [dim]@ {event.location}[/dim]" if event.location else ""
            console.print(f"    [dim]#{event.id}[/dim] {time_str}  {event.title}{location_str}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error listing events: {e}[/red]")
        raise typer.Exit(1)


@event_app.command("delete")
def event_delete(
    event_id: int = typer.Argument(..., help="Event ID to delete"),
):
    """
    Delete a calendar event

    Example:
      planner event delete 5
    """
    try:
        # Get event
        event_row = db.execute_one("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        if not event_row:
            console.print(f"[red]Event #{event_id} not found[/red]")
            raise typer.Exit(1)

        event = CalendarEvent.from_dict(dict(event_row))

        # Delete event
        db.execute_write("DELETE FROM calendar_events WHERE id = ?", (event_id,))

        console.print(f"[green]✓[/green] Deleted event: {event.title}")

    except Exception as e:
        console.print(f"[red]Error deleting event: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
