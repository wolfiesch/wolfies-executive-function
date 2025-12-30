"""
Review Agent for AI Life Planner
Handles daily/weekly reviews, reflections, and pattern insights.

This agent provides:
- Daily review summaries (tasks completed, events, goal progress)
- Weekly review summaries with completion rates and trends
- Reflection/journal entry storage with mood tracking
- Productivity pattern insights
- Contextual reflection prompt generation

Reviews and reflections are stored in the notes table with specific metadata
structures that enable aggregation and trend analysis.

Design Decision: Reviews are stored as notes (type='note' with review metadata)
rather than a separate table. This allows:
- Consistent content management with NoteAgent
- Full-text search across all notes including reviews
- Markdown file storage for human readability
- Flexible metadata for different review types
"""

from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from .base_agent import BaseAgent, AgentResponse


class ReviewAgent(BaseAgent):
    """
    Specialized agent for daily/weekly reviews and reflections.

    Handles intents:
    - daily_review: Generate summary of today's activity
    - weekly_review: Generate weekly summary with trends
    - add_reflection: Store a reflection/journal entry
    - get_insights: Analyze patterns and trends
    - generate_prompts: Create contextual reflection prompts

    Data Storage:
    Reviews and reflections are stored in the notes table with:
    - note_type: 'note' (standard)
    - metadata.type: 'review' or 'reflection'
    - metadata.review_type: 'daily' or 'weekly' (for reviews)
    - metadata.period: date range covered
    - metadata.metrics: aggregated statistics
    - metadata.mood: sentiment indicator (for reflections)

    Metadata Structure for Reviews:
        {
            "type": "review",
            "review_type": "daily|weekly",
            "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
            "metrics": {
                "tasks_completed": int,
                "tasks_remaining": int,
                "completion_rate": float,
                "events_attended": int,
                "goal_progress": [{"goal_id": int, "name": str, "delta": int}]
            },
            "highlights": ["..."],
            "areas_for_improvement": ["..."],
            "mood": "productive|neutral|stressed|etc"
        }

    Metadata Structure for Reflections:
        {
            "type": "reflection",
            "mood": "happy|neutral|stressed|etc",
            "mood_score": 1-5,
            "date": "YYYY-MM-DD",
            "linked_to_review": optional review_id
        }
    """

    # Supported intents for this agent
    INTENTS = [
        "daily_review",
        "weekly_review",
        "add_reflection",
        "get_insights",
        "generate_prompts",
    ]

    # Mood keywords for sentiment detection (maps to mood_score 1-5)
    MOOD_KEYWORDS = {
        5: ["amazing", "excellent", "fantastic", "wonderful", "great", "awesome", "thrilled", "excited"],
        4: ["good", "productive", "accomplished", "satisfied", "happy", "positive", "content"],
        3: ["okay", "neutral", "fine", "normal", "average", "so-so", "alright"],
        2: ["tired", "stressed", "overwhelmed", "frustrated", "anxious", "concerned", "busy"],
        1: ["terrible", "awful", "exhausted", "depressed", "burned out", "struggling", "down"],
    }

    # Mood score to label mapping
    MOOD_LABELS = {
        5: "excellent",
        4: "good",
        3: "neutral",
        2: "stressed",
        1: "struggling",
    }

    # Reflection prompts categorized by context
    REFLECTION_PROMPTS = {
        "general": [
            "What went well today?",
            "What could have gone better?",
            "What am I grateful for?",
            "What did I learn today?",
            "What's one thing I want to improve tomorrow?",
        ],
        "productive": [
            "What made today so productive?",
            "How can I replicate this success?",
            "What obstacles did I overcome?",
            "Who helped me succeed today?",
        ],
        "struggling": [
            "What's causing the most stress right now?",
            "What would make tomorrow better?",
            "Who can I reach out to for support?",
            "What's one small win I can celebrate?",
            "What do I need to let go of?",
        ],
        "weekly": [
            "What were the top 3 accomplishments this week?",
            "What patterns do I notice in my productivity?",
            "What goals need more attention?",
            "How did I take care of my wellbeing?",
            "What do I want to focus on next week?",
        ],
        "goal_focused": [
            "Which goal made the most progress this week?",
            "What's blocking my goal progress?",
            "What's the next milestone I'm working toward?",
            "Do my daily actions align with my goals?",
        ],
    }

    def __init__(self, db, config):
        """Initialize the Review Agent."""
        super().__init__(db, config, "review")

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intents."""
        return self.INTENTS

    def can_handle(self, intent: str, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given intent."""
        return intent in self.INTENTS

    def process(self, intent: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Process a review-related intent.

        Routes to the appropriate handler based on intent type.

        Args:
            intent: One of the supported review intents
            context: Request context with parameters

        Returns:
            AgentResponse with operation result
        """
        self.log_action(f"processing_{intent}", {"context_keys": list(context.keys())})

        handlers = {
            "daily_review": self._handle_daily_review,
            "weekly_review": self._handle_weekly_review,
            "add_reflection": self._handle_add_reflection,
            "get_insights": self._handle_get_insights,
            "generate_prompts": self._handle_generate_prompts,
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

    def _handle_daily_review(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Generate a summary of today's (or specified date's) activity.

        Aggregates:
        - Tasks completed vs remaining
        - Events attended
        - Goal progress updates
        - Suggested reflection prompts

        Context params:
            date (str, optional): Date to review (default: today), format YYYY-MM-DD
            save_review (bool, optional): Whether to save review as a note (default: True)
            include_suggestions (bool, optional): Include reflection prompts (default: True)
        """
        # Determine the review date
        review_date = self._parse_date(context.get("date"))
        if not review_date:
            review_date = datetime.now(timezone.utc).date()

        date_str = review_date.isoformat()
        save_review = context.get("save_review", True)
        include_suggestions = context.get("include_suggestions", True)

        # Aggregate task data for the day
        task_metrics = self._get_task_metrics_for_date(review_date)

        # Aggregate event data for the day
        event_metrics = self._get_event_metrics_for_date(review_date)

        # Get goal progress (any goals with progress logged today)
        goal_progress = self._get_goal_progress_for_date(review_date)

        # Calculate completion rate
        total_tasks = task_metrics["completed"] + task_metrics["remaining"]
        completion_rate = (
            task_metrics["completed"] / total_tasks if total_tasks > 0 else 0.0
        )

        # Build review summary
        review_data = {
            "type": "review",
            "review_type": "daily",
            "period": {"start": date_str, "end": date_str},
            "metrics": {
                "tasks_completed": task_metrics["completed"],
                "tasks_remaining": task_metrics["remaining"],
                "tasks_created": task_metrics.get("created", 0),
                "completion_rate": round(completion_rate, 3),
                "events_attended": event_metrics["attended"],
                "events_total": event_metrics["total"],
                "goal_progress": goal_progress,
            },
            "task_details": {
                "completed_tasks": task_metrics.get("completed_list", []),
                "high_priority_remaining": task_metrics.get("high_priority_remaining", []),
            },
            "highlights": self._extract_highlights(task_metrics, event_metrics, goal_progress),
            "areas_for_improvement": self._identify_improvement_areas(
                task_metrics, event_metrics, completion_rate
            ),
        }

        # Generate contextual prompts
        prompts = []
        if include_suggestions:
            prompts = self._generate_daily_prompts(review_data)

        # Optionally save the review as a note
        review_note_id = None
        if save_review:
            review_note_id = self._save_review_as_note(review_data, "daily", review_date)

        # Build human-readable summary message
        summary_lines = [
            f"Daily Review for {date_str}",
            f"Tasks: {task_metrics['completed']} completed, {task_metrics['remaining']} remaining ({int(completion_rate * 100)}% completion rate)",
            f"Events: {event_metrics['attended']} of {event_metrics['total']} attended",
        ]

        if goal_progress:
            summary_lines.append(f"Goal Progress: {len(goal_progress)} goal(s) updated")

        summary_message = "\n".join(summary_lines)

        return AgentResponse.ok(
            message=summary_message,
            data={
                "review": review_data,
                "review_note_id": review_note_id,
                "reflection_prompts": prompts,
                "date": date_str,
            },
            suggestions=prompts[:3] if prompts else [
                "Add a reflection: 'reflect on today'",
                "View weekly review: 'show weekly review'",
            ]
        )

    def _handle_weekly_review(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Generate weekly summary with completion rates and trends.

        Aggregates:
        - Week's completion statistics
        - Goal progress trends
        - Highlights and accomplishments
        - Upcoming priorities

        Context params:
            week_start (str, optional): Start date of week (default: last Monday)
            save_review (bool, optional): Whether to save review as a note (default: True)
            include_comparison (bool, optional): Compare with previous week (default: True)
        """
        # Determine week boundaries
        week_start = self._parse_date(context.get("week_start"))
        if not week_start:
            # Default to the Monday of the current week
            today = datetime.now(timezone.utc).date()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)

        week_end = week_start + timedelta(days=6)

        save_review = context.get("save_review", True)
        include_comparison = context.get("include_comparison", True)

        # Aggregate metrics for the week
        weekly_task_metrics = self._get_task_metrics_for_range(week_start, week_end)
        weekly_event_metrics = self._get_event_metrics_for_range(week_start, week_end)
        weekly_goal_progress = self._get_goal_progress_for_range(week_start, week_end)

        # Calculate daily breakdown for trends
        daily_breakdown = self._get_daily_breakdown(week_start, week_end)

        # Calculate completion rate
        total_tasks = weekly_task_metrics["completed"] + weekly_task_metrics["remaining"]
        completion_rate = (
            weekly_task_metrics["completed"] / total_tasks if total_tasks > 0 else 0.0
        )

        # Get previous week metrics for comparison
        previous_week_data = None
        if include_comparison:
            prev_start = week_start - timedelta(days=7)
            prev_end = week_start - timedelta(days=1)
            prev_task_metrics = self._get_task_metrics_for_range(prev_start, prev_end)
            prev_total = prev_task_metrics["completed"] + prev_task_metrics["remaining"]
            prev_completion_rate = (
                prev_task_metrics["completed"] / prev_total if prev_total > 0 else 0.0
            )
            previous_week_data = {
                "tasks_completed": prev_task_metrics["completed"],
                "completion_rate": round(prev_completion_rate, 3),
                "completion_rate_change": round(completion_rate - prev_completion_rate, 3),
            }

        # Identify best/worst days
        best_day = max(daily_breakdown, key=lambda d: d["completed"]) if daily_breakdown else None
        worst_day = min(daily_breakdown, key=lambda d: d["completed"]) if daily_breakdown else None

        # Build review summary
        review_data = {
            "type": "review",
            "review_type": "weekly",
            "period": {"start": week_start.isoformat(), "end": week_end.isoformat()},
            "metrics": {
                "tasks_completed": weekly_task_metrics["completed"],
                "tasks_remaining": weekly_task_metrics["remaining"],
                "tasks_created": weekly_task_metrics.get("created", 0),
                "completion_rate": round(completion_rate, 3),
                "events_attended": weekly_event_metrics["attended"],
                "events_total": weekly_event_metrics["total"],
                "goal_progress": weekly_goal_progress,
            },
            "trends": {
                "daily_breakdown": daily_breakdown,
                "best_day": best_day,
                "worst_day": worst_day,
                "previous_week_comparison": previous_week_data,
            },
            "highlights": self._extract_weekly_highlights(
                weekly_task_metrics, weekly_goal_progress, daily_breakdown
            ),
            "areas_for_improvement": self._identify_weekly_improvements(
                daily_breakdown, completion_rate
            ),
            "upcoming_priorities": self._get_upcoming_priorities(),
        }

        # Optionally save the review as a note
        review_note_id = None
        if save_review:
            review_note_id = self._save_review_as_note(review_data, "weekly", week_start)

        # Build human-readable summary message
        summary_lines = [
            f"Weekly Review: {week_start.isoformat()} to {week_end.isoformat()}",
            f"Tasks: {weekly_task_metrics['completed']} completed ({int(completion_rate * 100)}% completion rate)",
            f"Events: {weekly_event_metrics['attended']} attended",
        ]

        if previous_week_data:
            change = previous_week_data["completion_rate_change"]
            direction = "up" if change > 0 else "down"
            summary_lines.append(
                f"Trend: {abs(int(change * 100))}% {direction} from last week"
            )

        if weekly_goal_progress:
            summary_lines.append(f"Goal Progress: {len(weekly_goal_progress)} goal(s) advanced")

        summary_message = "\n".join(summary_lines)

        return AgentResponse.ok(
            message=summary_message,
            data={
                "review": review_data,
                "review_note_id": review_note_id,
                "period": {
                    "start": week_start.isoformat(),
                    "end": week_end.isoformat(),
                },
            },
            suggestions=[
                "Add weekly reflection: 'reflect on this week'",
                "View daily reviews: 'show daily review'",
                "Get productivity insights: 'show my productivity patterns'",
            ]
        )

    def _handle_add_reflection(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Store a reflection/journal entry.

        Parses text for mood indicators and stores with timestamp.
        Links to daily context when applicable.

        Context params:
            text (str): Reflection text content (required)
            mood (str, optional): Explicit mood indicator
            date (str, optional): Date for the reflection (default: today)
            tags (list, optional): Additional tags
        """
        if not context.get("text"):
            return AgentResponse.error("Reflection text is required")

        reflection_text = context["text"]
        reflection_date = self._parse_date(context.get("date"))
        if not reflection_date:
            reflection_date = datetime.now(timezone.utc).date()

        # Parse mood from text if not explicitly provided
        explicit_mood = context.get("mood")
        if explicit_mood:
            mood_label = explicit_mood.lower()
            mood_score = self._mood_label_to_score(mood_label)
        else:
            mood_score, mood_label = self._detect_mood_from_text(reflection_text)

        # Build tags
        tags = context.get("tags", [])
        if "reflection" not in tags:
            tags.append("reflection")
        if mood_label:
            tags.append(f"mood:{mood_label}")

        # Check for existing daily review to link
        linked_review_id = self._get_review_id_for_date(reflection_date)

        # Build reflection metadata
        metadata = {
            "type": "reflection",
            "mood": mood_label,
            "mood_score": mood_score,
            "date": reflection_date.isoformat(),
            "linked_to_review": linked_review_id,
        }

        # Generate title
        now = datetime.now(timezone.utc)
        title = f"Reflection - {reflection_date.isoformat()}"

        # Check if there's already a reflection for today - append if so
        existing_reflection = self._get_reflection_for_date(reflection_date)
        if existing_reflection:
            return self._append_to_reflection(existing_reflection, reflection_text, mood_label)

        # Create note for new reflection
        try:
            note_id = self._create_reflection_note(
                title=title,
                content=reflection_text,
                metadata=metadata,
                tags=tags,
                reflection_date=reflection_date,
            )

            return AgentResponse.ok(
                message=f"Reflection saved for {reflection_date.isoformat()} (mood: {mood_label})",
                data={
                    "note_id": note_id,
                    "mood": mood_label,
                    "mood_score": mood_score,
                    "date": reflection_date.isoformat(),
                    "linked_review_id": linked_review_id,
                },
                suggestions=[
                    "View today's review: 'show daily review'",
                    "Add more thoughts: 'add reflection ...'",
                    "See mood trends: 'show my mood patterns'",
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to save reflection: {e}")
            return AgentResponse.error(f"Failed to save reflection: {str(e)}")

    def _handle_get_insights(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Analyze patterns and trends in productivity and wellbeing.

        Insights include:
        - Best days/times for productivity
        - Goal momentum analysis
        - Overdue task trends
        - Mood patterns (if reflections exist)

        Context params:
            days (int, optional): Number of days to analyze (default: 30)
            insight_type (str, optional): Focus area - 'productivity', 'goals', 'mood', 'all'
        """
        days = context.get("days", 30)
        insight_type = context.get("insight_type", "all")

        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)

        insights = {"period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days}}

        # Productivity patterns
        if insight_type in ["productivity", "all"]:
            productivity_insights = self._analyze_productivity_patterns(start_date, end_date)
            insights["productivity"] = productivity_insights

        # Goal momentum
        if insight_type in ["goals", "all"]:
            goal_insights = self._analyze_goal_momentum(start_date, end_date)
            insights["goals"] = goal_insights

        # Mood patterns
        if insight_type in ["mood", "all"]:
            mood_insights = self._analyze_mood_patterns(start_date, end_date)
            insights["mood"] = mood_insights

        # Overdue trends
        if insight_type in ["productivity", "all"]:
            overdue_insights = self._analyze_overdue_trends()
            insights["overdue"] = overdue_insights

        # Generate summary message
        summary_parts = [f"Insights for the past {days} days:"]

        if "productivity" in insights:
            prod = insights["productivity"]
            if prod.get("best_day"):
                summary_parts.append(f"Best day: {prod['best_day']['day_name']} ({prod['best_day']['avg_completed']:.1f} tasks avg)")
            summary_parts.append(f"Average daily completion: {prod.get('avg_daily_completion', 0):.1f} tasks")

        if "goals" in insights:
            goals = insights["goals"]
            summary_parts.append(f"Active goals: {goals.get('active_count', 0)}, At risk: {goals.get('at_risk_count', 0)}")

        if "mood" in insights and insights["mood"].get("avg_mood_score"):
            mood = insights["mood"]
            summary_parts.append(f"Average mood: {mood['avg_mood_label']} ({mood['avg_mood_score']:.1f}/5)")

        return AgentResponse.ok(
            message="\n".join(summary_parts),
            data={"insights": insights},
            suggestions=[
                "View detailed daily review: 'show daily review'",
                "See goal progress: 'review my goals'",
                "Add a reflection: 'reflect on how I'm doing'",
            ]
        )

    def _handle_generate_prompts(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Generate contextual reflection prompts based on current state.

        Uses recent activity and patterns to suggest relevant reflection questions.

        Context params:
            prompt_type (str, optional): 'general', 'productive', 'struggling', 'weekly', 'goal_focused'
            count (int, optional): Number of prompts to generate (default: 5)
            auto_detect (bool, optional): Auto-detect context for prompts (default: True)
        """
        prompt_type = context.get("prompt_type")
        count = context.get("count", 5)
        auto_detect = context.get("auto_detect", True)

        # Auto-detect appropriate prompt category based on recent activity
        if auto_detect and not prompt_type:
            prompt_type = self._detect_prompt_context()

        if not prompt_type or prompt_type not in self.REFLECTION_PROMPTS:
            prompt_type = "general"

        # Get prompts from the category
        available_prompts = self.REFLECTION_PROMPTS.get(prompt_type, self.REFLECTION_PROMPTS["general"])

        # Select prompts (rotate through if needed)
        selected_prompts = available_prompts[:count]
        if len(selected_prompts) < count:
            # Add general prompts to fill
            remaining = count - len(selected_prompts)
            general_prompts = [p for p in self.REFLECTION_PROMPTS["general"] if p not in selected_prompts]
            selected_prompts.extend(general_prompts[:remaining])

        return AgentResponse.ok(
            message=f"Reflection prompts ({prompt_type} context):",
            data={
                "prompts": selected_prompts,
                "prompt_type": prompt_type,
                "count": len(selected_prompts),
            },
            suggestions=[
                f"Respond to a prompt: 'reflect: {selected_prompts[0]}'" if selected_prompts else "Add reflection",
            ]
        )

    # =========================================================================
    # Data Aggregation Methods
    # =========================================================================

    def _get_task_metrics_for_date(self, target_date: date) -> Dict[str, Any]:
        """Get task metrics for a specific date."""
        date_str = target_date.isoformat()
        next_day = (target_date + timedelta(days=1)).isoformat()

        # Tasks completed on this date
        completed_query = """
            SELECT id, title, priority FROM tasks
            WHERE completed_at >= ? AND completed_at < ?
            ORDER BY priority DESC
        """
        completed_rows = self.db.execute(completed_query, (date_str, next_day))
        completed_tasks = self.db.rows_to_dicts(completed_rows)

        # Tasks remaining (not done, due on or before this date, or created today)
        remaining_query = """
            SELECT id, title, priority FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND (due_date <= ? OR (date(created_at) = ?))
            ORDER BY priority DESC, due_date ASC
        """
        remaining_rows = self.db.execute(remaining_query, (date_str, date_str))
        remaining_tasks = self.db.rows_to_dicts(remaining_rows)

        # Tasks created on this date
        created_query = """
            SELECT COUNT(*) FROM tasks
            WHERE date(created_at) = ?
        """
        created_row = self.db.execute_one(created_query, (date_str,))
        created_count = created_row[0] if created_row else 0

        # High priority remaining tasks
        high_priority = [t for t in remaining_tasks if t.get("priority", 3) >= 4]

        return {
            "completed": len(completed_tasks),
            "remaining": len(remaining_tasks),
            "created": created_count,
            "completed_list": [{"id": t["id"], "title": t["title"]} for t in completed_tasks[:10]],
            "high_priority_remaining": [{"id": t["id"], "title": t["title"]} for t in high_priority[:5]],
        }

    def _get_task_metrics_for_range(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get task metrics for a date range."""
        start_str = start_date.isoformat()
        end_str = (end_date + timedelta(days=1)).isoformat()

        # Tasks completed in range
        completed_query = """
            SELECT COUNT(*) FROM tasks
            WHERE completed_at >= ? AND completed_at < ?
        """
        completed_row = self.db.execute_one(completed_query, (start_str, end_str))
        completed_count = completed_row[0] if completed_row else 0

        # Tasks created in range that are still remaining
        remaining_query = """
            SELECT COUNT(*) FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND created_at >= ? AND created_at < ?
        """
        remaining_row = self.db.execute_one(remaining_query, (start_str, end_str))
        remaining_count = remaining_row[0] if remaining_row else 0

        # Tasks created in range
        created_query = """
            SELECT COUNT(*) FROM tasks
            WHERE created_at >= ? AND created_at < ?
        """
        created_row = self.db.execute_one(created_query, (start_str, end_str))
        created_count = created_row[0] if created_row else 0

        return {
            "completed": completed_count,
            "remaining": remaining_count,
            "created": created_count,
        }

    def _get_event_metrics_for_date(self, target_date: date) -> Dict[str, Any]:
        """Get event metrics for a specific date."""
        date_str = target_date.isoformat()
        next_day = (target_date + timedelta(days=1)).isoformat()

        # Events on this date
        query = """
            SELECT id, title, status FROM calendar_events
            WHERE date(start_time) = ?
        """
        rows = self.db.execute(query, (date_str,))
        events = self.db.rows_to_dicts(rows)

        attended = len([e for e in events if e.get("status") != "cancelled"])
        total = len(events)

        return {"attended": attended, "total": total}

    def _get_event_metrics_for_range(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get event metrics for a date range."""
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        query = """
            SELECT id, status FROM calendar_events
            WHERE date(start_time) >= ? AND date(start_time) <= ?
        """
        rows = self.db.execute(query, (start_str, end_str))
        events = self.db.rows_to_dicts(rows)

        attended = len([e for e in events if e.get("status") != "cancelled"])
        total = len(events)

        return {"attended": attended, "total": total}

    def _get_goal_progress_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get goals with progress logged on a specific date."""
        date_str = target_date.isoformat()

        # Find projects that are goals with progress logs on this date
        query = """
            SELECT id, name, metadata FROM projects
            WHERE json_extract(metadata, '$.is_goal') = 1
            AND json_extract(metadata, '$.progress_log') IS NOT NULL
        """
        rows = self.db.execute(query)
        goals = self.db.rows_to_dicts(rows)

        progress_updates = []
        for goal in goals:
            try:
                metadata = json.loads(goal.get("metadata", "{}")) if goal.get("metadata") else {}
                progress_log = metadata.get("progress_log", [])

                # Find progress entries for the target date
                for entry in progress_log:
                    if entry.get("date") == date_str:
                        progress_updates.append({
                            "goal_id": goal["id"],
                            "name": goal["name"],
                            "note": entry.get("note", ""),
                            "percentage": entry.get("percentage", 0),
                        })
                        break
            except (json.JSONDecodeError, TypeError):
                continue

        return progress_updates

    def _get_goal_progress_for_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get goals with progress logged in a date range."""
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        query = """
            SELECT id, name, metadata FROM projects
            WHERE json_extract(metadata, '$.is_goal') = 1
            AND json_extract(metadata, '$.progress_log') IS NOT NULL
        """
        rows = self.db.execute(query)
        goals = self.db.rows_to_dicts(rows)

        progress_updates = []
        for goal in goals:
            try:
                metadata = json.loads(goal.get("metadata", "{}")) if goal.get("metadata") else {}
                progress_log = metadata.get("progress_log", [])

                # Find progress entries in the date range
                start_progress = None
                end_progress = None

                for entry in progress_log:
                    entry_date = entry.get("date", "")
                    if entry_date >= start_str and entry_date <= end_str:
                        if start_progress is None or entry_date < start_progress.get("date", ""):
                            start_progress = entry
                        if end_progress is None or entry_date > end_progress.get("date", ""):
                            end_progress = entry

                if start_progress or end_progress:
                    start_pct = start_progress.get("percentage", 0) if start_progress else 0
                    end_pct = end_progress.get("percentage", metadata.get("overall_progress", 0)) if end_progress else metadata.get("overall_progress", 0)

                    progress_updates.append({
                        "goal_id": goal["id"],
                        "name": goal["name"],
                        "start_percentage": start_pct,
                        "end_percentage": end_pct,
                        "delta": end_pct - start_pct,
                    })
            except (json.JSONDecodeError, TypeError):
                continue

        return progress_updates

    def _get_daily_breakdown(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get daily task completion breakdown for a date range."""
        breakdown = []
        current = start_date

        while current <= end_date:
            metrics = self._get_task_metrics_for_date(current)
            breakdown.append({
                "date": current.isoformat(),
                "day_name": current.strftime("%A"),
                "completed": metrics["completed"],
                "remaining": metrics["remaining"],
            })
            current += timedelta(days=1)

        return breakdown

    # =========================================================================
    # Insight Analysis Methods
    # =========================================================================

    def _analyze_productivity_patterns(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze productivity patterns over a date range."""
        daily_breakdown = self._get_daily_breakdown(start_date, end_date)

        if not daily_breakdown:
            return {"message": "Not enough data for analysis"}

        # Calculate averages by day of week
        day_totals = {}
        for entry in daily_breakdown:
            day_name = entry["day_name"]
            if day_name not in day_totals:
                day_totals[day_name] = {"completed": 0, "count": 0}
            day_totals[day_name]["completed"] += entry["completed"]
            day_totals[day_name]["count"] += 1

        day_averages = [
            {
                "day_name": day,
                "avg_completed": totals["completed"] / totals["count"] if totals["count"] > 0 else 0,
            }
            for day, totals in day_totals.items()
        ]
        day_averages.sort(key=lambda x: x["avg_completed"], reverse=True)

        best_day = day_averages[0] if day_averages else None
        worst_day = day_averages[-1] if day_averages else None

        # Overall average
        total_completed = sum(e["completed"] for e in daily_breakdown)
        avg_daily = total_completed / len(daily_breakdown) if daily_breakdown else 0

        return {
            "avg_daily_completion": avg_daily,
            "total_completed": total_completed,
            "best_day": best_day,
            "worst_day": worst_day,
            "by_day_of_week": day_averages,
        }

    def _analyze_goal_momentum(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze goal progress momentum."""
        # Get all active goals
        query = """
            SELECT id, name, metadata, target_end_date FROM projects
            WHERE json_extract(metadata, '$.is_goal') = 1
            AND (archived = 0 OR archived IS NULL)
            AND status = 'active'
        """
        rows = self.db.execute(query)
        goals = self.db.rows_to_dicts(rows)

        active_count = len(goals)
        at_risk_count = 0
        progressing_count = 0
        stalled_count = 0

        goal_details = []
        today = datetime.now(timezone.utc).date()

        for goal in goals:
            try:
                metadata = json.loads(goal.get("metadata", "{}")) if goal.get("metadata") else {}
                progress_log = metadata.get("progress_log", [])
                overall_progress = metadata.get("overall_progress", 0)

                # Check for recent progress (in last 7 days)
                recent_progress = any(
                    entry.get("date", "") >= (today - timedelta(days=7)).isoformat()
                    for entry in progress_log
                )

                if recent_progress:
                    progressing_count += 1
                else:
                    stalled_count += 1

                # Check if at risk (behind schedule)
                target_date_str = goal.get("target_end_date")
                if target_date_str:
                    try:
                        target_date = datetime.fromisoformat(target_date_str).date() if isinstance(target_date_str, str) else target_date_str
                        days_remaining = (target_date - today).days
                        if days_remaining < 14 and overall_progress < 75:
                            at_risk_count += 1
                    except (ValueError, TypeError):
                        pass

                goal_details.append({
                    "goal_id": goal["id"],
                    "name": goal["name"],
                    "progress": overall_progress,
                    "recent_activity": recent_progress,
                })

            except (json.JSONDecodeError, TypeError):
                continue

        return {
            "active_count": active_count,
            "at_risk_count": at_risk_count,
            "progressing_count": progressing_count,
            "stalled_count": stalled_count,
            "goal_details": goal_details[:10],  # Top 10
        }

    def _analyze_mood_patterns(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze mood patterns from reflections."""
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Find reflection notes in the date range
        query = """
            SELECT metadata FROM notes
            WHERE json_extract(metadata, '$.type') = 'reflection'
            AND date(created_at) >= ? AND date(created_at) <= ?
        """
        rows = self.db.execute(query, (start_str, end_str))

        mood_scores = []
        for row in rows:
            try:
                metadata = json.loads(row[0]) if row[0] else {}
                mood_score = metadata.get("mood_score")
                if mood_score:
                    mood_scores.append(mood_score)
            except (json.JSONDecodeError, TypeError, IndexError):
                continue

        if not mood_scores:
            return {"message": "No mood data available", "reflection_count": 0}

        avg_score = sum(mood_scores) / len(mood_scores)
        avg_label = self.MOOD_LABELS.get(round(avg_score), "neutral")

        return {
            "avg_mood_score": round(avg_score, 2),
            "avg_mood_label": avg_label,
            "reflection_count": len(mood_scores),
            "mood_distribution": {
                "excellent": mood_scores.count(5),
                "good": mood_scores.count(4),
                "neutral": mood_scores.count(3),
                "stressed": mood_scores.count(2),
                "struggling": mood_scores.count(1),
            },
        }

    def _analyze_overdue_trends(self) -> Dict[str, Any]:
        """Analyze overdue task patterns."""
        today = datetime.now(timezone.utc).date().isoformat()

        # Overdue tasks
        overdue_query = """
            SELECT id, title, due_date, priority FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND due_date < ?
            ORDER BY priority DESC, due_date ASC
        """
        rows = self.db.execute(overdue_query, (today,))
        overdue_tasks = self.db.rows_to_dicts(rows)

        # Group by how overdue
        severely_overdue = []  # > 7 days
        moderately_overdue = []  # 3-7 days
        recently_overdue = []  # 1-3 days

        for task in overdue_tasks:
            due_date = task.get("due_date", "")
            if due_date:
                try:
                    due = datetime.fromisoformat(due_date).date() if isinstance(due_date, str) else due_date
                    days_overdue = (datetime.now(timezone.utc).date() - due).days
                    task_info = {"id": task["id"], "title": task["title"], "days_overdue": days_overdue}

                    if days_overdue > 7:
                        severely_overdue.append(task_info)
                    elif days_overdue > 3:
                        moderately_overdue.append(task_info)
                    else:
                        recently_overdue.append(task_info)
                except (ValueError, TypeError):
                    continue

        return {
            "total_overdue": len(overdue_tasks),
            "severely_overdue": len(severely_overdue),
            "moderately_overdue": len(moderately_overdue),
            "recently_overdue": len(recently_overdue),
            "top_overdue_tasks": (severely_overdue + moderately_overdue + recently_overdue)[:5],
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_highlights(
        self,
        task_metrics: Dict[str, Any],
        event_metrics: Dict[str, Any],
        goal_progress: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract highlights from daily metrics."""
        highlights = []

        if task_metrics["completed"] >= 5:
            highlights.append(f"Completed {task_metrics['completed']} tasks!")

        if task_metrics.get("completed_list"):
            top_task = task_metrics["completed_list"][0]["title"]
            highlights.append(f"Finished: {top_task}")

        if event_metrics["attended"] > 0:
            highlights.append(f"Attended {event_metrics['attended']} event(s)")

        for progress in goal_progress:
            highlights.append(f"Made progress on goal: {progress['name']}")

        return highlights[:5]  # Cap at 5

    def _extract_weekly_highlights(
        self,
        task_metrics: Dict[str, Any],
        goal_progress: List[Dict[str, Any]],
        daily_breakdown: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract highlights from weekly metrics."""
        highlights = []

        if task_metrics["completed"] >= 10:
            highlights.append(f"Completed {task_metrics['completed']} tasks this week!")

        # Find best day
        if daily_breakdown:
            best_day = max(daily_breakdown, key=lambda d: d["completed"])
            if best_day["completed"] > 0:
                highlights.append(f"Best day: {best_day['day_name']} ({best_day['completed']} tasks)")

        # Goal progress
        for progress in goal_progress:
            if progress.get("delta", 0) > 0:
                highlights.append(f"Advanced {progress['name']} by {progress['delta']}%")

        return highlights[:5]

    def _identify_improvement_areas(
        self,
        task_metrics: Dict[str, Any],
        event_metrics: Dict[str, Any],
        completion_rate: float,
    ) -> List[str]:
        """Identify areas for improvement from daily metrics."""
        areas = []

        if completion_rate < 0.5 and task_metrics["remaining"] > 3:
            areas.append("Consider breaking large tasks into smaller ones")

        if task_metrics.get("high_priority_remaining"):
            areas.append(f"{len(task_metrics['high_priority_remaining'])} high-priority tasks still pending")

        if task_metrics["created"] > task_metrics["completed"]:
            areas.append("More tasks created than completed - review priorities")

        return areas[:3]

    def _identify_weekly_improvements(
        self, daily_breakdown: List[Dict[str, Any]], completion_rate: float
    ) -> List[str]:
        """Identify areas for improvement from weekly metrics."""
        areas = []

        if completion_rate < 0.5:
            areas.append("Completion rate below 50% - consider reducing commitments")

        # Find days with zero completions
        zero_days = [d for d in daily_breakdown if d["completed"] == 0]
        if len(zero_days) >= 2:
            day_names = [d["day_name"] for d in zero_days[:2]]
            areas.append(f"No tasks completed on {', '.join(day_names)}")

        # Check for inconsistency
        if daily_breakdown:
            completions = [d["completed"] for d in daily_breakdown]
            if max(completions) > 0 and min(completions) == 0:
                areas.append("Inconsistent daily productivity - aim for steady progress")

        return areas[:3]

    def _get_upcoming_priorities(self) -> List[Dict[str, Any]]:
        """Get upcoming high-priority tasks and deadlines."""
        today = datetime.now(timezone.utc).date().isoformat()
        next_week = (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()

        query = """
            SELECT id, title, due_date, priority FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND (priority >= 4 OR (due_date >= ? AND due_date <= ?))
            ORDER BY priority DESC, due_date ASC
            LIMIT 10
        """
        rows = self.db.execute(query, (today, next_week))
        tasks = self.db.rows_to_dicts(rows)

        return [{"id": t["id"], "title": t["title"], "due_date": t.get("due_date"), "priority": t.get("priority")} for t in tasks]

    def _generate_daily_prompts(self, review_data: Dict[str, Any]) -> List[str]:
        """Generate contextual prompts based on daily review data."""
        metrics = review_data.get("metrics", {})
        completion_rate = metrics.get("completion_rate", 0)

        if completion_rate >= 0.7:
            return self.REFLECTION_PROMPTS["productive"][:3]
        elif completion_rate < 0.3:
            return self.REFLECTION_PROMPTS["struggling"][:3]
        else:
            return self.REFLECTION_PROMPTS["general"][:3]

    def _detect_prompt_context(self) -> str:
        """Detect appropriate prompt context based on recent activity."""
        today = datetime.now(timezone.utc).date()
        metrics = self._get_task_metrics_for_date(today)

        total_tasks = metrics["completed"] + metrics["remaining"]
        completion_rate = metrics["completed"] / total_tasks if total_tasks > 0 else 0

        if completion_rate >= 0.7:
            return "productive"
        elif completion_rate < 0.3 and total_tasks > 3:
            return "struggling"

        # Check if it's end of week
        if today.weekday() >= 4:  # Friday or later
            return "weekly"

        return "general"

    def _detect_mood_from_text(self, text: str) -> Tuple[int, str]:
        """Detect mood from reflection text using keyword analysis."""
        text_lower = text.lower()

        # Check each mood level
        for score, keywords in self.MOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    label = self.MOOD_LABELS.get(score, "neutral")
                    return score, label

        # Default to neutral
        return 3, "neutral"

    def _mood_label_to_score(self, label: str) -> int:
        """Convert mood label to numeric score."""
        label_lower = label.lower()
        for score, mood_label in self.MOOD_LABELS.items():
            if mood_label == label_lower:
                return score

        # Check if label matches any keyword
        for score, keywords in self.MOOD_KEYWORDS.items():
            if label_lower in keywords:
                return score

        return 3  # Default neutral

    def _parse_date(self, date_input: Any) -> Optional[date]:
        """Parse date input to date object."""
        if date_input is None:
            return None
        if isinstance(date_input, date):
            return date_input
        if isinstance(date_input, datetime):
            return date_input.date()
        if isinstance(date_input, str):
            try:
                return datetime.fromisoformat(date_input).date()
            except ValueError:
                # Try other formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        return datetime.strptime(date_input, fmt).date()
                    except ValueError:
                        continue
        return None

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _save_review_as_note(
        self, review_data: Dict[str, Any], review_type: str, review_date: date
    ) -> Optional[int]:
        """Save a review as a note in the database."""
        title = f"{'Daily' if review_type == 'daily' else 'Weekly'} Review - {review_date.isoformat()}"

        # Generate markdown content
        content = self._generate_review_markdown(review_data, review_type)

        # Create file path
        file_path = self._generate_review_file_path(review_type, review_date)

        try:
            # Write content to file
            from pathlib import Path
            notes_dir = self.config.get_notes_directory()
            full_path = notes_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

            # Check if review already exists for this path
            existing = self.db.execute_one(
                "SELECT id FROM notes WHERE file_path = ?", (file_path,)
            )

            tags = json.dumps(["review", f"{review_type}-review"])
            metadata = json.dumps(review_data)
            word_count = len(content.split())

            if existing:
                # Update existing review
                query = """
                    UPDATE notes SET title = ?, tags = ?, metadata = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                """
                self.db.execute_write(query, (title, tags, metadata, word_count, file_path))
                return existing[0] if hasattr(existing, '__getitem__') else existing
            else:
                # Insert new note record
                query = """
                    INSERT INTO notes (title, file_path, note_type, tags, metadata, word_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                note_id = self.db.execute_write(query, (title, file_path, "note", tags, metadata, word_count))
                return note_id

        except Exception as e:
            self.logger.error(f"Failed to save review as note: {e}")
            return None

    def _generate_review_markdown(self, review_data: Dict[str, Any], review_type: str) -> str:
        """Generate markdown content for a review."""
        period = review_data.get("period", {})
        metrics = review_data.get("metrics", {})

        lines = [
            "---",
            f"type: {review_type}_review",
            f"date: {period.get('start', '')}",
            "---",
            "",
            f"# {'Daily' if review_type == 'daily' else 'Weekly'} Review",
            "",
            f"**Period:** {period.get('start', '')} to {period.get('end', '')}",
            "",
            "## Metrics",
            "",
            f"- Tasks Completed: {metrics.get('tasks_completed', 0)}",
            f"- Tasks Remaining: {metrics.get('tasks_remaining', 0)}",
            f"- Completion Rate: {int(metrics.get('completion_rate', 0) * 100)}%",
            f"- Events Attended: {metrics.get('events_attended', 0)}",
            "",
        ]

        # Goal progress
        goal_progress = metrics.get("goal_progress", [])
        if goal_progress:
            lines.extend(["## Goal Progress", ""])
            for gp in goal_progress:
                lines.append(f"- {gp.get('name', 'Goal')}: {gp.get('percentage', gp.get('delta', 0))}%")
            lines.append("")

        # Highlights
        highlights = review_data.get("highlights", [])
        if highlights:
            lines.extend(["## Highlights", ""])
            for h in highlights:
                lines.append(f"- {h}")
            lines.append("")

        # Areas for improvement
        areas = review_data.get("areas_for_improvement", [])
        if areas:
            lines.extend(["## Areas for Improvement", ""])
            for a in areas:
                lines.append(f"- {a}")
            lines.append("")

        # Weekly-specific sections
        if review_type == "weekly":
            trends = review_data.get("trends", {})
            if trends.get("best_day"):
                lines.extend([
                    "## Productivity Trends",
                    "",
                    f"- Best Day: {trends['best_day'].get('day_name', '')}",
                ])
                if trends.get("worst_day"):
                    lines.append(f"- Needs Improvement: {trends['worst_day'].get('day_name', '')}")
                lines.append("")

            upcoming = review_data.get("upcoming_priorities", [])
            if upcoming:
                lines.extend(["## Upcoming Priorities", ""])
                for p in upcoming[:5]:
                    lines.append(f"- {p.get('title', 'Task')}")
                lines.append("")

        return "\n".join(lines)

    def _generate_review_file_path(self, review_type: str, review_date: date) -> str:
        """Generate file path for a review note."""
        date_str = review_date.strftime("%Y-%m-%d")
        return f"reviews/{date_str}_{review_type}_review.md"

    def _get_review_id_for_date(self, target_date: date) -> Optional[int]:
        """Get the review note ID for a specific date if it exists."""
        date_str = target_date.isoformat()
        query = """
            SELECT id FROM notes
            WHERE json_extract(metadata, '$.type') = 'review'
            AND json_extract(metadata, '$.period.start') = ?
        """
        row = self.db.execute_one(query, (date_str,))
        return row[0] if row else None

    def _get_reflection_for_date(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get reflection note for a specific date if it exists."""
        date_str = target_date.isoformat()
        query = """
            SELECT * FROM notes
            WHERE json_extract(metadata, '$.type') = 'reflection'
            AND json_extract(metadata, '$.date') = ?
            LIMIT 1
        """
        row = self.db.execute_one(query, (date_str,))
        return self.db.row_to_dict(row)

    def _create_reflection_note(
        self,
        title: str,
        content: str,
        metadata: Dict[str, Any],
        tags: List[str],
        reflection_date: date,
    ) -> int:
        """Create a new reflection note."""
        # Generate file path
        date_str = reflection_date.strftime("%Y-%m-%d")
        file_path = f"reflections/{date_str}_reflection.md"

        # Create markdown content
        markdown_content = self._create_reflection_markdown(title, content, metadata, tags)

        # Write file
        from pathlib import Path
        notes_dir = self.config.get_notes_directory()
        full_path = notes_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(markdown_content, encoding="utf-8")

        # Insert note record
        query = """
            INSERT INTO notes (title, file_path, note_type, tags, metadata, word_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        tags_json = json.dumps(tags)
        metadata_json = json.dumps(metadata)
        word_count = len(content.split())

        return self.db.execute_write(query, (title, file_path, "note", tags_json, metadata_json, word_count))

    def _create_reflection_markdown(
        self, title: str, content: str, metadata: Dict[str, Any], tags: List[str]
    ) -> str:
        """Create markdown content for a reflection."""
        now = datetime.now(timezone.utc).isoformat()
        mood = metadata.get("mood", "neutral")

        lines = [
            "---",
            f"title: {title}",
            "type: reflection",
            f"date: {metadata.get('date', '')}",
            f"mood: {mood}",
            f"created: {now}",
            f"tags: [{', '.join(tags)}]",
            "---",
            "",
            f"# {title}",
            "",
            f"**Mood:** {mood}",
            "",
            content,
        ]

        return "\n".join(lines)

    def _append_to_reflection(
        self, reflection: Dict[str, Any], new_content: str, mood: Optional[str]
    ) -> AgentResponse:
        """Append content to an existing reflection."""
        try:
            from pathlib import Path
            notes_dir = self.config.get_notes_directory()
            full_path = notes_dir / reflection["file_path"]

            existing_content = full_path.read_text(encoding="utf-8") if full_path.exists() else ""

            # Add timestamp and new entry
            now = datetime.now(timezone.utc)
            new_entry = f"\n\n---\n\n**{now.strftime('%H:%M')}**"
            if mood:
                new_entry += f" (mood: {mood})"
            new_entry += f"\n\n{new_content}"

            full_path.write_text(existing_content + new_entry, encoding="utf-8")

            # Update word count
            total_words = len((existing_content + new_entry).split())
            self._update_note(reflection["id"], {"word_count": total_words})

            return AgentResponse.ok(
                message="Added to today's reflection",
                data={
                    "note_id": reflection["id"],
                    "mood": mood,
                },
                suggestions=["View daily review: 'show daily review'"]
            )
        except Exception as e:
            return AgentResponse.error(f"Failed to append to reflection: {str(e)}")

    def _update_note(self, note_id: int, fields: Dict[str, Any]) -> bool:
        """Update specified note fields."""
        if not fields:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        query = f"UPDATE notes SET {set_clause} WHERE id = ?"
        params = tuple(fields.values()) + (note_id,)

        result = self.db.execute_write(query, params)
        return result > 0
