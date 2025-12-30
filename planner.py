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
from typing import Any, Dict, Optional
import json
import re

from src.core import Database, Config, Task, CalendarEvent
from src.dashboard import DashboardAggregator, DashboardFormatter
from src.agents import MasterAgent, AgentResponse

# Initialize CLI app and console
app = typer.Typer(help="AI Life Planner - Your personal task and project manager")
event_app = typer.Typer(help="Calendar event management")
app.add_typer(event_app, name="event")

console = Console()
db = Database()
config = Config()

# Lazy-loaded MasterAgent (initialized on first use)
_master_agent: Optional[MasterAgent] = None


def get_master_agent() -> MasterAgent:
    """
    Get or initialize the MasterAgent instance.

    Uses lazy loading to avoid startup overhead when agent commands aren't used.
    This is the 'Lazy Initialization' pattern - we defer the expensive operation
    (agent initialization) until it's actually needed.
    """
    global _master_agent
    if _master_agent is None:
        _master_agent = MasterAgent(db, config)
    return _master_agent


def format_agent_response(response: AgentResponse) -> None:
    """
    Format and display an AgentResponse using Rich console.

    Renders:
    - Success/error status with appropriate colors
    - Main message
    - Data in a table or formatted output if present
    - Suggestions as bullet points

    Args:
        response: The AgentResponse to display
    """
    # Status indicator and message
    if response.success:
        console.print(f"[green]✓[/green] {response.message}")
    else:
        console.print(f"[red]✗[/red] {response.message}")

    # Display data if present
    if response.data:
        _render_response_data(response.data)

    # Display suggestions if present
    if response.suggestions:
        console.print()
        console.print("[dim]Suggestions:[/dim]")
        for suggestion in response.suggestions:
            console.print(f"  [dim]•[/dim] {suggestion}")


def _render_response_data(data: Dict[str, Any]) -> None:
    """
    Render response data in an appropriate format.

    Detects the data type and renders it accordingly:
    - Single task: Formatted task display
    - List of tasks: Table view
    - Single event: Formatted event display
    - List of events: Table view
    - Generic data: JSON-like display

    Args:
        data: The data dictionary from AgentResponse
    """
    # Handle task lists
    if "tasks" in data and isinstance(data["tasks"], list):
        tasks = data["tasks"]
        if not tasks:
            return

        console.print()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task", min_width=30)
        table.add_column("Priority", justify="center", width=8)
        table.add_column("Due", width=12)
        table.add_column("Status", width=12)

        for task in tasks:
            task_id = str(task.get("id", ""))
            title = task.get("title", "")
            priority = task.get("priority", 3)
            priority_str = f"P{priority}" if priority != 3 else "-"

            # Format due date
            due_date = task.get("due_date")
            if due_date:
                try:
                    dt = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    due_str = dt.strftime("%m/%d")
                except (ValueError, AttributeError):
                    due_str = str(due_date)[:10]
            else:
                due_str = "-"

            status = task.get("status", "todo")
            status_icons = {
                "todo": "[white]○ todo[/white]",
                "in_progress": "[yellow]◐ in progress[/yellow]",
                "waiting": "[blue]◎ waiting[/blue]",
                "done": "[green]✓ done[/green]",
                "cancelled": "[dim]✗ cancelled[/dim]"
            }
            status_str = status_icons.get(status, status)

            table.add_row(task_id, title, priority_str, due_str, status_str)

        console.print(table)
        return

    # Handle single task
    if "task" in data and isinstance(data["task"], dict):
        task = data["task"]
        console.print()
        console.print(Panel(
            _format_single_task(task),
            title=f"Task #{task.get('id', 'N/A')}",
            border_style="cyan"
        ))
        return

    # Handle event lists
    if "events" in data and isinstance(data["events"], list):
        events = data["events"]
        if not events:
            return

        console.print()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Event", min_width=25)
        table.add_column("When", width=20)
        table.add_column("Location", width=15)

        for event in events:
            event_id = str(event.get("id", ""))
            title = event.get("title", "")

            start_time = event.get("start_time")
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    when_str = dt.strftime("%m/%d %I:%M %p")
                except (ValueError, AttributeError):
                    when_str = str(start_time)[:16]
            else:
                when_str = "-"

            location = event.get("location", "-") or "-"

            table.add_row(event_id, title, when_str, location)

        console.print(table)
        return

    # Handle single event
    if "event" in data and isinstance(data["event"], dict):
        event = data["event"]
        console.print()
        console.print(Panel(
            _format_single_event(event),
            title=f"Event #{event.get('id', 'N/A')}",
            border_style="cyan"
        ))
        return

    # Handle notes list
    if "notes" in data and isinstance(data["notes"], list):
        notes = data["notes"]
        if not notes:
            return

        console.print()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", min_width=30)
        table.add_column("Type", width=12)
        table.add_column("Created", width=12)

        for note in notes:
            note_id = str(note.get("id", ""))
            title = note.get("title", "")
            note_type = note.get("type", "note")

            created = note.get("created_at")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created_str = dt.strftime("%m/%d/%y")
                except (ValueError, AttributeError):
                    created_str = str(created)[:10]
            else:
                created_str = "-"

            table.add_row(note_id, title, note_type, created_str)

        console.print(table)
        return

    # Handle goals list
    if "goals" in data and isinstance(data["goals"], list):
        goals = data["goals"]
        if not goals:
            return

        console.print()
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Goal", min_width=30)
        table.add_column("Progress", width=12)
        table.add_column("Target", width=12)

        for goal in goals:
            goal_id = str(goal.get("id", ""))
            title = goal.get("title", "")

            current = goal.get("current_value", 0)
            target = goal.get("target_value", 100)
            if target > 0:
                pct = int((current / target) * 100)
                progress_str = f"{pct}%"
            else:
                progress_str = "-"

            target_date = goal.get("target_date")
            if target_date:
                try:
                    dt = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                    target_str = dt.strftime("%m/%d/%y")
                except (ValueError, AttributeError):
                    target_str = str(target_date)[:10]
            else:
                target_str = "-"

            table.add_row(goal_id, title, progress_str, target_str)

        console.print(table)
        return

    # Generic data display for other cases
    # Only show if there's meaningful data beyond meta fields
    meaningful_keys = [k for k in data.keys() if k not in ("count", "filters_applied", "query")]
    if meaningful_keys:
        # Show count if present
        if "count" in data:
            console.print(f"  [dim]Count: {data['count']}[/dim]")

        # Show completed/failed IDs for batch operations
        if "completed_ids" in data:
            console.print(f"  [green]Completed:[/green] {', '.join(map(str, data['completed_ids']))}")
        if "failed_ids" in data and data["failed_ids"]:
            console.print(f"  [red]Failed:[/red] {', '.join(map(str, data['failed_ids']))}")

        # Show task_id for newly created items
        if "task_id" in data and "task" not in data:
            console.print(f"  [dim]Task ID: {data['task_id']}[/dim]")
        if "event_id" in data and "event" not in data:
            console.print(f"  [dim]Event ID: {data['event_id']}[/dim]")
        if "note_id" in data and "note" not in data:
            console.print(f"  [dim]Note ID: {data['note_id']}[/dim]")
        if "goal_id" in data and "goal" not in data:
            console.print(f"  [dim]Goal ID: {data['goal_id']}[/dim]")


def _format_single_task(task: Dict[str, Any]) -> str:
    """Format a single task for detailed display."""
    lines = []
    lines.append(f"[bold]{task.get('title', 'Untitled')}[/bold]")

    if task.get("description"):
        lines.append(f"  {task['description']}")

    lines.append("")

    status = task.get("status", "todo")
    status_icons = {"todo": "○", "in_progress": "◐", "waiting": "◎", "done": "✓", "cancelled": "✗"}
    lines.append(f"Status: {status_icons.get(status, '?')} {status}")

    priority = task.get("priority", 3)
    lines.append(f"Priority: P{priority}")

    if task.get("due_date"):
        lines.append(f"Due: {task['due_date'][:10]}")

    if task.get("estimated_minutes"):
        lines.append(f"Estimate: {task['estimated_minutes']} minutes")

    if task.get("tags"):
        try:
            tags = json.loads(task["tags"]) if isinstance(task["tags"], str) else task["tags"]
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
        except (json.JSONDecodeError, TypeError):
            pass

    return "\n".join(lines)


def _format_single_event(event: Dict[str, Any]) -> str:
    """Format a single event for detailed display."""
    lines = []
    lines.append(f"[bold]{event.get('title', 'Untitled')}[/bold]")

    if event.get("description"):
        lines.append(f"  {event['description']}")

    lines.append("")

    if event.get("start_time"):
        try:
            dt = datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
            lines.append(f"Start: {dt.strftime('%A, %B %d at %I:%M %p')}")
        except (ValueError, AttributeError):
            lines.append(f"Start: {event['start_time']}")

    if event.get("end_time"):
        try:
            dt = datetime.fromisoformat(event["end_time"].replace("Z", "+00:00"))
            lines.append(f"End: {dt.strftime('%I:%M %p')}")
        except (ValueError, AttributeError):
            lines.append(f"End: {event['end_time']}")

    if event.get("location"):
        lines.append(f"Location: {event['location']}")

    if event.get("all_day"):
        lines.append("All day event")

    return "\n".join(lines)


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
def ask(
    query: str = typer.Argument(..., help="Natural language request"),
):
    """
    Process a natural language request through the AI agent system

    The ask command routes your request to the appropriate specialized agent
    (task, calendar, note, or goal) based on what you're asking for.

    Examples:
      planner ask "Add a task to call John tomorrow at 2pm"
      planner ask "What's on my calendar this week?"
      planner ask "Create a note about the meeting discussion"
      planner ask "How am I doing on my fitness goal?"
      planner ask "Buy groceries"
      planner ask "Remind me to send the report by Friday"
    """
    try:
        agent = get_master_agent()
        response = agent.process(query)

        # Format and display the response
        format_agent_response(response)

        # Add to conversation history for context
        agent.add_to_conversation_history("user", query)
        agent.add_to_conversation_history("assistant", response.message)

    except Exception as e:
        console.print(f"[red]Error processing request: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def chat():
    """
    Start an interactive chat session with the AI life planner

    Enter natural language requests and get responses from the agent system.
    Type 'exit', 'quit', or 'bye' to end the session.
    Type 'help' for available commands.

    Example session:
      > Add a task to review the proposal
      > What tasks do I have?
      > Mark task 5 as done
      > exit
    """
    console.print(Panel(
        "[bold cyan]AI Life Planner Chat[/bold cyan]\n\n"
        "Enter natural language requests to manage your tasks, calendar, notes, and goals.\n"
        "Type [bold]'exit'[/bold], [bold]'quit'[/bold], or [bold]'bye'[/bold] to end the session.\n"
        "Type [bold]'help'[/bold] for tips.",
        border_style="cyan"
    ))
    console.print()

    agent = get_master_agent()
    exit_commands = {"exit", "quit", "bye", "q", ":q", ":q!"}

    while True:
        try:
            # Get user input with styled prompt
            user_input = console.input("[bold green]>[/bold green] ").strip()

            # Check for empty input
            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in exit_commands:
                console.print("[dim]Goodbye![/dim]")
                break

            # Check for help command
            if user_input.lower() == "help":
                _show_chat_help()
                continue

            # Check for clear command
            if user_input.lower() == "clear":
                console.clear()
                continue

            # Process through the agent
            response = agent.process(user_input)

            # Format and display the response
            console.print()
            format_agent_response(response)
            console.print()

            # Add to conversation history
            agent.add_to_conversation_history("user", user_input)
            agent.add_to_conversation_history("assistant", response.message)

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' to quit[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Try rephrasing your request[/dim]")
            continue


def _show_chat_help():
    """Display help information for chat mode."""
    help_text = """
[bold cyan]Chat Commands:[/bold cyan]
  [bold]exit, quit, bye[/bold]  - End the chat session
  [bold]help[/bold]             - Show this help message
  [bold]clear[/bold]            - Clear the screen

[bold cyan]Task Examples:[/bold cyan]
  "Add a task to buy groceries tomorrow"
  "Remind me to call John by Friday"
  "What tasks do I have?"
  "Show my tasks"
  "Mark task 5 as done"
  "Complete the grocery task"

[bold cyan]Calendar Examples:[/bold cyan]
  "Schedule a meeting tomorrow at 2pm"
  "What's on my calendar this week?"
  "Show my schedule"
  "Block 2 hours for deep work"

[bold cyan]Note Examples:[/bold cyan]
  "Create a note about the meeting"
  "Jot down: project ideas for Q1"
  "Show my notes"

[bold cyan]Goal Examples:[/bold cyan]
  "Create a goal to exercise 3 times per week"
  "How am I doing on my fitness goal?"
  "Log progress: ran 5 miles today"
"""
    console.print(help_text)


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
