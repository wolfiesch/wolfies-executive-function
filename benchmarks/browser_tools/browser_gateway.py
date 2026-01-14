"""Browser Gateway wrapper for browser benchmarks.

NOTE: browser-gateway skill is not fully implemented yet.
This wrapper is a placeholder for when it becomes available.

Expected CLI commands (from README):
- browser-gateway open <url>
- browser-gateway snapshot
- browser-gateway click @e5
- browser-gateway fill @e12 "text"
- browser-gateway screenshot <path>
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from shutil import which

from .base import BrowserTool, BrowserBenchmarkResult, estimate_tokens


class BrowserGatewayTool(BrowserTool):
    """Browser Gateway CLI wrapper.

    Uses warm daemon for low-latency browser operations.
    Currently NOT IMPLEMENTED - placeholder for future use.
    """

    def __init__(self):
        self._cold_start = True
        self._cli_path = which("browser-gateway")

    @property
    def name(self) -> str:
        return "browser_gateway"

    def is_available(self) -> bool:
        """Check if browser-gateway CLI is available."""
        if self._cli_path:
            return True
        # Check FGP project directory (release binary)
        fgp_cli = Path.home() / "projects" / "fgp" / "browser" / "target" / "release" / "browser-gateway"
        if fgp_cli.exists():
            self._cli_path = str(fgp_cli)
            return True
        # Check skill directory
        skill_cli = Path.home() / ".claude" / "skills" / "browser-gateway" / "cli" / "browser-gateway"
        if skill_cli.exists():
            self._cli_path = str(skill_cli)
            return True
        return False

    def _run_command(self, args: list[str], operation: str, test_case: str, iteration: int) -> BrowserBenchmarkResult:
        """Run browser-gateway CLI command."""
        if not self.is_available():
            return BrowserBenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                is_cold_start=self._cold_start,
                error="browser-gateway CLI not installed",
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
        """Navigate to URL via browser-gateway."""
        return self._run_command(["open", url], "navigate", test_case, iteration)

    def extract(self, extraction_config: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Get ARIA snapshot from current page."""
        return self._run_command(["snapshot"], "extract", test_case, iteration)

    def fill_form(self, fields: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Fill form field. Expects fields like {"@e12": "value"}."""
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
        """Browser-gateway daemon handles cleanup."""
        self._cold_start = True
