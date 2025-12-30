"""
Rich formatter module for AI Life Planner Dashboard.

Handles all Rich-based CLI formatting for the dashboard display.
Creates beautiful, information-dense terminal output.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from src.core.models import Task, CalendarEvent
from src.dashboard.aggregator import DashboardData, DailyStats, TimeAnalysis
from src.dashboard.prioritizer import ScoredTask


# Status icons for tasks
STATUS_ICONS = {
    "todo": "[dim]○[/dim]",
    "in_progress": "[yellow]◐[/yellow]",
    "waiting": "[blue]◎[/blue]",
    "done": "[green]✓[/green]",
    "cancelled": "[red]✗[/red]",
}

# Priority colors
PRIORITY_COLORS = {
    5: "red bold",
    4: "yellow",
    3: "white",
    2: "dim",
    1: "dim",
}


class DashboardFormatter:
    """
    Rich-based formatter for the Today dashboard.

    Creates beautiful terminal output using Rich panels, tables, and styling.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize formatter.

        Args:
            console: Rich Console instance (creates default if not provided)
        """
        self.console = console or Console()

    def _format_priority(self, priority: int) -> str:
        """Format priority as colored badge."""
        color = PRIORITY_COLORS.get(priority, "white")
        return f"[{color}]P{priority}[/{color}]"

    def _format_time_duration(self, minutes: int) -> str:
        """Format duration in human-readable format."""
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"

    def _format_due_date(self, task: Task, now: datetime) -> str:
        """Format due date with color based on urgency."""
        if task.due_date is None:
            return "[dim]---[/dim]"

        due = task.due_date
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        # Calculate days difference
        days_diff = (due.replace(hour=0, minute=0, second=0) - today_start).days

        if days_diff < 0:
            # Overdue
            abs_days = abs(days_diff)
            if abs_days == 1:
                return "[red bold]1 day ago[/red bold]"
            return f"[red bold]{abs_days} days ago[/red bold]"
        elif days_diff == 0:
            return "[yellow bold]Due today[/yellow bold]"
        elif days_diff == 1:
            return "[yellow]Due tmrw[/yellow]"
        elif days_diff <= 7:
            return f"[white]Due {due.strftime('%a')}[/white]"
        else:
            return f"[dim]{due.strftime('%b %d')}[/dim]"

    def format_header(self, data: DashboardData) -> Panel:
        """
        Create header panel with date and greeting.

        Args:
            data: Dashboard data

        Returns:
            Rich Panel with header content
        """
        date_str = data.date.strftime("%A, %B %d, %Y")
        content = Text()
        content.append(f"{data.greeting}\n", style="bold")
        content.append(date_str, style="dim")

        return Panel(
            content,
            title="[bold]Today[/bold]",
            title_align="center",
            border_style="blue",
            padding=(0, 2),
        )

    def format_overdue_warning(self, overdue: List[Task]) -> Optional[Panel]:
        """
        Create red warning panel for overdue tasks.

        Args:
            overdue: List of overdue tasks

        Returns:
            Rich Panel or None if no overdue tasks
        """
        if not overdue:
            return None

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Icon", width=2)
        table.add_column("ID", width=4)
        table.add_column("Title", ratio=1)
        table.add_column("Overdue", width=12, justify="right")
        table.add_column("Priority", width=4, justify="right")

        for task in overdue[:5]:  # Limit to 5
            icon = STATUS_ICONS.get(task.status, "○")
            due_str = self._format_due_date(task, datetime.now(timezone.utc))
            priority_str = self._format_priority(task.priority)

            table.add_row(
                icon,
                f"[dim]#{task.id}[/dim]",
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                due_str,
                priority_str,
            )

        if len(overdue) > 5:
            table.add_row("", "", f"[dim]+ {len(overdue) - 5} more...[/dim]", "", "")

        return Panel(
            table,
            title=f"[red bold]⚠ Overdue ({len(overdue)})[/red bold]",
            border_style="red",
            padding=(0, 1),
        )

    def format_top_priorities(self, priorities: List[ScoredTask]) -> Panel:
        """
        Create panel showing top prioritized tasks.

        Args:
            priorities: List of scored and prioritized tasks

        Returns:
            Rich Panel with priority list
        """
        if not priorities:
            content = Text("[dim]No active tasks[/dim]", justify="center")
            return Panel(
                content,
                title="[bold]Focus Today[/bold]",
                border_style="green",
                padding=(0, 1),
            )

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("#", width=2)
        table.add_column("ID", width=4)
        table.add_column("Title", ratio=1)
        table.add_column("Due", width=12, justify="right")
        table.add_column("Priority", width=4, justify="right")
        table.add_column("Est", width=5, justify="right")

        now = datetime.now(timezone.utc)
        for i, scored in enumerate(priorities[:5], 1):
            task = scored.task
            icon = STATUS_ICONS.get(task.status, "○")
            due_str = self._format_due_date(task, now)
            priority_str = self._format_priority(task.priority)
            est_str = (
                f"[dim]~{self._format_time_duration(task.estimated_minutes)}[/dim]"
                if task.estimated_minutes
                else "[dim]---[/dim]"
            )

            table.add_row(
                f"[bold]{i}.[/bold]",
                f"[dim]#{task.id}[/dim]",
                task.title[:35] + "..." if len(task.title) > 35 else task.title,
                due_str,
                priority_str,
                est_str,
            )

        return Panel(
            table,
            title="[bold]Focus Today[/bold]",
            border_style="green",
            padding=(0, 1),
        )

    def format_events_timeline(self, events: List[CalendarEvent]) -> Panel:
        """
        Create vertical timeline of today's events.

        Args:
            events: List of calendar events

        Returns:
            Rich Panel with event timeline
        """
        if not events:
            content = Text("[dim]No events scheduled[/dim]", justify="center")
            return Panel(
                content,
                title="[bold]Calendar[/bold]",
                border_style="cyan",
                padding=(0, 1),
            )

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Time", width=18, no_wrap=True)
        table.add_column("Title", ratio=1)
        table.add_column("Location", width=12, justify="right")

        for event in events:
            if event.all_day:
                time_str = "[cyan]All day[/cyan]"
            elif event.start_time and event.end_time:
                start = event.start_time.strftime("%I:%M%p").lstrip("0").lower()
                end = event.end_time.strftime("%I:%M%p").lstrip("0").lower()
                time_str = f"[cyan]{start}[/cyan] - {end}"
            else:
                time_str = "[dim]---[/dim]"

            location = (
                f"[dim]{event.location[:12]}...[/dim]"
                if event.location and len(event.location) > 12
                else f"[dim]{event.location or ''}[/dim]"
            )

            table.add_row(
                time_str,
                event.title[:30] + "..." if len(event.title) > 30 else event.title,
                location,
            )

        # Summary line
        total_events = len(events)
        total_minutes = sum(
            int((e.end_time - e.start_time).total_seconds() / 60)
            for e in events
            if e.start_time and e.end_time and not e.all_day
        )
        summary = f"[dim]{total_events} event{'s' if total_events != 1 else ''}"
        if total_minutes > 0:
            summary += f" • {self._format_time_duration(total_minutes)} committed"
        summary += "[/dim]"

        table.add_row("", "", "")
        table.add_row("", summary, "")

        return Panel(
            table,
            title="[bold]Calendar[/bold]",
            border_style="cyan",
            padding=(0, 1),
        )

    def format_time_budget(self, time_analysis: TimeAnalysis) -> Panel:
        """
        Create panel showing time budget for the day.

        Args:
            time_analysis: Time analysis data

        Returns:
            Rich Panel with time budget
        """
        lines = []

        # Work hours
        start_str = time_analysis.work_hours_start.strftime("%I:%M %p").lstrip("0")
        end_str = time_analysis.work_hours_end.strftime("%I:%M %p").lstrip("0")
        work_duration = self._format_time_duration(time_analysis.total_work_minutes)
        lines.append(f"Work Hours    {start_str} - {end_str}  [dim]({work_duration})[/dim]")

        # Events committed
        events_duration = self._format_time_duration(time_analysis.events_minutes)
        lines.append(f"Events        [cyan]{events_duration}[/cyan] committed")

        # Tasks estimated
        tasks_duration = self._format_time_duration(time_analysis.tasks_estimated_minutes)
        lines.append(f"Tasks         [yellow]{tasks_duration}[/yellow] estimated")

        # Separator
        lines.append("[dim]" + "─" * 40 + "[/dim]")

        # Free time
        free_duration = self._format_time_duration(time_analysis.free_minutes)
        if time_analysis.free_minutes > 60:
            lines.append(f"Free Time     [green bold]~{free_duration}[/green bold]")
        elif time_analysis.free_minutes > 0:
            lines.append(f"Free Time     [yellow]~{free_duration}[/yellow]")
        else:
            lines.append(f"Free Time     [red bold]Overbooked![/red bold]")

        content = "\n".join(lines)

        return Panel(
            content,
            title="[bold]Time Budget[/bold]",
            border_style="magenta",
            padding=(0, 1),
        )

    def format_task_list(
        self,
        tasks: List[Task],
        title: str,
        max_items: int = 7
    ) -> Optional[Panel]:
        """
        Create panel with task list.

        Args:
            tasks: List of tasks to display
            title: Panel title
            max_items: Maximum items to show

        Returns:
            Rich Panel or None if no tasks
        """
        if not tasks:
            return None

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Icon", width=2)
        table.add_column("ID", width=4)
        table.add_column("Title", ratio=1)
        table.add_column("Due", width=12, justify="right")
        table.add_column("Priority", width=4, justify="right")

        now = datetime.now(timezone.utc)
        for task in tasks[:max_items]:
            icon = STATUS_ICONS.get(task.status, "○")
            due_str = self._format_due_date(task, now)
            priority_str = self._format_priority(task.priority)

            table.add_row(
                icon,
                f"[dim]#{task.id}[/dim]",
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                due_str,
                priority_str,
            )

        if len(tasks) > max_items:
            table.add_row(
                "",
                "",
                f"[dim]+ {len(tasks) - max_items} more...[/dim]",
                "",
                "",
            )

        return Panel(
            table,
            title=f"[bold]{title} ({len(tasks)})[/bold]",
            border_style="white",
            padding=(0, 1),
        )

    def format_stats_bar(self, stats: DailyStats) -> str:
        """
        Create bottom stats bar.

        Args:
            stats: Daily statistics

        Returns:
            Formatted stats string
        """
        parts = []

        # Completed
        parts.append(f"[green]✓ {stats.tasks_completed_today} done[/green]")

        # Remaining
        parts.append(f"[white]○ {stats.tasks_remaining} remaining[/white]")

        # Overdue
        if stats.tasks_overdue > 0:
            parts.append(f"[red]⚠ {stats.tasks_overdue} overdue[/red]")

        # Completion rate
        if stats.completion_rate > 0:
            parts.append(f"[dim]{stats.completion_rate:.0f}% done[/dim]")

        return " │ ".join(parts)

    def render_dashboard(
        self,
        data: DashboardData,
        verbose: bool = False
    ) -> None:
        """
        Render the complete dashboard to console.

        Args:
            data: Complete dashboard data
            verbose: Show additional details if True
        """
        # Header
        self.console.print(self.format_header(data))
        self.console.print()

        # Overdue warning (if any)
        overdue_panel = self.format_overdue_warning(data.tasks_overdue)
        if overdue_panel:
            self.console.print(overdue_panel)
            self.console.print()

        # Top priorities
        self.console.print(self.format_top_priorities(data.top_priorities))
        self.console.print()

        # Calendar
        self.console.print(self.format_events_timeline(data.events))
        self.console.print()

        # Time budget
        self.console.print(self.format_time_budget(data.time_analysis))
        self.console.print()

        # Additional task lists in verbose mode
        if verbose:
            # Scheduled tasks
            scheduled_panel = self.format_task_list(
                data.tasks_scheduled,
                "Scheduled Today"
            )
            if scheduled_panel:
                self.console.print(scheduled_panel)
                self.console.print()

            # Due today
            due_panel = self.format_task_list(
                data.tasks_due,
                "Due Today"
            )
            if due_panel:
                self.console.print(due_panel)
                self.console.print()

        # Stats bar
        self.console.print("─" * 60)
        self.console.print(self.format_stats_bar(data.stats), justify="center")
        self.console.print("─" * 60)
