"""Playwright MCP wrapper for browser benchmarks.

Uses npx @playwright/mcp@latest as stdio MCP server.
Each operation spawns a new MCP session (cold start model).
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .base import BrowserTool, BrowserBenchmarkResult, estimate_tokens


class PlaywrightMCPTool(BrowserTool):
    """Playwright MCP browser tool via npx."""

    def __init__(self):
        self._cold_start = True

    @property
    def name(self) -> str:
        return "playwright_mcp"

    def is_available(self) -> bool:
        """Check if npx and playwright mcp are available."""
        try:
            result = subprocess.run(
                ["npx", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _call_mcp_tool(self, tool_name: str, params: dict, operation: str, test_case: str, iteration: int) -> BrowserBenchmarkResult:
        """Call a Playwright MCP tool via stdio."""
        start = time.perf_counter()

        # MCP client code that spawns Playwright MCP server
        client_code = f'''
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("{tool_name}", {json.dumps(params)})
            print(json.dumps({{"content": result.content[0].text if result.content else "", "success": True}}))

asyncio.run(main())
'''
        try:
            proc = subprocess.run(
                ["python3", "-c", client_code],
                capture_output=True,
                timeout=60,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            is_cold = self._cold_start
            self._cold_start = False

            if proc.returncode == 0:
                try:
                    output = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
                    response_text = output.get("content", proc.stdout)
                except json.JSONDecodeError:
                    response_text = proc.stdout

                return BrowserBenchmarkResult(
                    tool=self.name,
                    operation=operation,
                    test_case=test_case,
                    iteration=iteration,
                    latency_ms=elapsed_ms,
                    success=True,
                    is_cold_start=is_cold,
                    payload_size=len(proc.stdout) if proc.stdout else 0,
                    token_estimate=estimate_tokens(tool_name + json.dumps(params) + proc.stdout),
                )
            else:
                return BrowserBenchmarkResult(
                    tool=self.name,
                    operation=operation,
                    test_case=test_case,
                    iteration=iteration,
                    latency_ms=elapsed_ms,
                    success=False,
                    is_cold_start=is_cold,
                    error=proc.stderr[:500] if proc.stderr else "Unknown error",
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
        """Navigate to URL via Playwright MCP."""
        return self._call_mcp_tool(
            "browser_navigate",
            {"url": url},
            "navigate",
            test_case,
            iteration,
        )

    def extract(self, extraction_config: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Extract page content via browser_snapshot."""
        return self._call_mcp_tool(
            "browser_snapshot",
            {},
            "extract",
            test_case,
            iteration,
        )

    def fill_form(self, fields: dict, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Fill form fields. Expects fields like {"selector": "value"}."""
        # Fill the first field as a representative operation
        for selector, value in fields.items():
            return self._call_mcp_tool(
                "browser_fill",
                {"selector": selector, "value": value},
                "form_fill",
                test_case,
                iteration,
            )
        return BrowserBenchmarkResult(
            tool=self.name, operation="form_fill", test_case=test_case,
            iteration=iteration, latency_ms=0, success=False,
            error="No fields provided",
        )

    def click(self, selector: str, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Click element via Playwright MCP."""
        return self._call_mcp_tool(
            "browser_click",
            {"selector": selector},
            "click",
            test_case,
            iteration,
        )

    def screenshot(self, output_path: str, test_case: str = "default", iteration: int = 0) -> BrowserBenchmarkResult:
        """Capture screenshot via Playwright MCP."""
        return self._call_mcp_tool(
            "browser_screenshot",
            {},
            "screenshot",
            test_case,
            iteration,
        )

    def close(self) -> None:
        """Playwright MCP spawns fresh each time, no cleanup needed."""
        self._cold_start = True
