"""
Dashboard module for AI Life Planner.

Provides unified view aggregation, priority scoring, and CLI formatting
for the Today dashboard.
"""

from .prioritizer import (
    Prioritizer,
    ScoredTask,
    calculate_urgency_score,
    calculate_importance_score,
    calculate_time_fit_score,
    calculate_context_score,
)
from .aggregator import (
    DashboardAggregator,
    DashboardData,
    DailyStats,
    TimeAnalysis,
)
from .formatter import DashboardFormatter

__all__ = [
    # Prioritizer
    'Prioritizer',
    'ScoredTask',
    'calculate_urgency_score',
    'calculate_importance_score',
    'calculate_time_fit_score',
    'calculate_context_score',
    # Aggregator
    'DashboardAggregator',
    'DashboardData',
    'DailyStats',
    'TimeAnalysis',
    # Formatter
    'DashboardFormatter',
]
