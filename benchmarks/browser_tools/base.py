"""Base class for browser automation tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrowserBenchmarkResult:
    """Single browser benchmark measurement."""
    tool: str  # "playwright_mcp" | "browser_gateway" | "claude_in_chrome"
    operation: str  # "navigate" | "extract" | "form_fill" | "screenshot"
    test_case: str
    iteration: int
    latency_ms: float
    success: bool
    is_cold_start: bool = False
    payload_size: int | None = None
    token_estimate: int | None = None
    extracted_data: dict | None = None
    error: str | None = None


@dataclass
class BrowserBenchmarkSummary:
    """Statistical summary for a tool/operation combination."""
    tool: str
    operation: str
    test_case: str
    count: int
    success_rate: float
    cold_start_mean_ms: float
    warm_mean_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    avg_tokens: float
    avg_response_size: int


def estimate_tokens(text: str) -> int:
    """Estimate tokens using ~4 chars per token heuristic."""
    return len(text) // 4


class BrowserTool(ABC):
    """Abstract base class for browser automation tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier for benchmarks."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is available and configured."""
        pass

    @abstractmethod
    def navigate(self, url: str) -> BrowserBenchmarkResult:
        """Navigate to a URL and wait for page load."""
        pass

    @abstractmethod
    def extract(self, extraction_config: dict) -> BrowserBenchmarkResult:
        """Extract data from current page."""
        pass

    @abstractmethod
    def fill_form(self, fields: dict) -> BrowserBenchmarkResult:
        """Fill form fields on current page."""
        pass

    @abstractmethod
    def click(self, selector: str) -> BrowserBenchmarkResult:
        """Click an element on current page."""
        pass

    @abstractmethod
    def screenshot(self, output_path: str) -> BrowserBenchmarkResult:
        """Capture screenshot of current page."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up browser resources."""
        pass
