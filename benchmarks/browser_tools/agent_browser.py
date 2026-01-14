"""Agent-browser (Vercel) wrapper for browser benchmarks.

@anthropic/agent-browser - Fast browser automation CLI used by v0.dev
https://github.com/vercel-labs/agent-browser
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from shutil import which

from .base import BrowserTool, BrowserBenchmarkResult, estimate_tokens


class AgentBrowserTool(BrowserTool):
    """Agent-browser CLI wrapper.

    This is the Vercel agent-browser package - a Playwright-based browser
    automation tool optimized for AI agents.
    """

    def __init__(self):
        self._cold_start = True
        self._cli_path = which("agent-browser")

    @property
    def name(self) -> str:
        return "agent_browser"

    def is_available(self) -> bool:
        """Check if agent-browser CLI is available."""
        return self._cli_path is not None

    def _run_command(self, args: list[str], operation: str, test_case: str, iteration: int) -> BrowserBenchmarkResult:
        """Run agent-browser CLI command."""
        if not self.is_available():
            return BrowserBenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                is_cold_start=self._cold_start,
                error="agent-browser CLI not installed",
            )

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [self._cli_path] + args,
                capture_output=True,
                timeout=60,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            is_cold = self._cold_start
            self._cold_start = False

            return BrowserBenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                is_cold_start=is_cold,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                token_estimate=estimate_tokens(" ".join(args) + proc.stdout),
                error=proc.stderr[:500] if proc.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return BrowserBenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=elapsed_ms,
                success=False,
                is_cold_start=self._cold_start,
                error="Timeout after 60s",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return BrowserBenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=elapsed_ms,
                success=False,
                is_cold_start=self._cold_start,
                error=str(e)[:500],
            )

    def navigate(self, url: str, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Navigate to URL via agent-browser."""
        return self._run_command(["open", url], "navigate", test_case, iteration)

    def extract(self, extraction_config: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Get ARIA snapshot from current page."""
        return self._run_command(["snapshot"], "extract", test_case, iteration)

    def fill_form(self, fields: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Fill form field."""
        for selector, value in fields.items():
            return self._run_command(["fill", selector, value], "form_fill", test_case, iteration)
        return BrowserBenchmarkResult(
            tool=self.name, operation="form_fill", test_case=test_case,
            iteration=iteration, latency_ms=0, success=False,
            error="No fields provided",
        )

    def click(self, selector: str, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Click element."""
        return self._run_command(["click", selector], "click", test_case, iteration)

    def screenshot(self, output_path: str, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Capture screenshot."""
        return self._run_command(["screenshot", output_path], "screenshot", test_case, iteration)

    def close(self) -> None:
        """Close browser session."""
        try:
            subprocess.run([self._cli_path, "close"], capture_output=True, timeout=5)
        except:
            pass
        self._cold_start = True
