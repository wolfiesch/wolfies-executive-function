#!/usr/bin/env python3
"""
HN Workflow Benchmark - Comprehensive Browser Automation Comparison

Compares 3 browser automation approaches on a realistic 4-step workflow:
1. Navigate to Hacker News
2. Snapshot front page (ARIA tree)
3. Click first story's comments link
4. Snapshot comments page

Tools tested:
- FGP Browser (UNIX socket daemon) - fastest
- agent-browser (Vercel CLI daemon) - mid-tier
- Playwright MCP (cold-start stdio) - slowest baseline

Usage:
    python3 hn_workflow_benchmark.py
    python3 hn_workflow_benchmark.py --iterations 3
    python3 hn_workflow_benchmark.py --tool fgp  # Run only FGP

CHANGELOG (recent first, max 5 entries)
01/14/2026 - Initial implementation for comprehensive browser benchmark (Claude)
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Any, Callable

# Constants
FGP_BROWSER_SOCKET = Path.home() / ".fgp" / "services" / "browser" / "daemon.sock"
FGP_BROWSER_CLI = Path.home() / "projects" / "fgp" / "browser" / "target" / "release" / "browser-gateway"
RESULTS_DIR = Path(__file__).parent / "results"
HN_URL = "https://news.ycombinator.com"

# Selector for "comments" link (stays on HN, avoids external sites)
# Different tools handle multi-match selectors differently:
# - FGP/Playwright: Click first match with broad selector
# - agent-browser: Requires unique selector or ARIA ref
HN_COMMENTS_SELECTOR_BROAD = "td.subtext a[href^='item']"  # For FGP, Playwright


@dataclass
class StepResult:
    """Result of a single workflow step."""
    step_name: str
    latency_ms: float
    success: bool
    payload_size: int = 0
    error: str | None = None


@dataclass
class WorkflowResult:
    """Result of a complete workflow run."""
    tool: str  # "fgp" | "agent_browser" | "playwright_mcp"
    iteration: int
    steps: list[StepResult]
    total_latency_ms: float
    step_count: int
    success: bool
    error: str | None = None

    @property
    def avg_step_latency_ms(self) -> float:
        if not self.steps:
            return 0.0
        return self.total_latency_ms / len(self.steps)


@dataclass
class ToolSummary:
    """Statistical summary for a tool across all iterations."""
    tool: str
    iterations: int
    step_count: int
    success_rate: float
    mean_total_ms: float
    median_total_ms: float
    min_total_ms: float
    max_total_ms: float
    mean_per_step_ms: float
    step_breakdown: dict[str, float]  # step_name -> mean latency


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    generated_at: str
    iterations: int
    workflow: str
    results: list[WorkflowResult] = field(default_factory=list)
    summaries: list[ToolSummary] = field(default_factory=list)


def _percentile(data: list[float], p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


# ============================================================================
# FGP BROWSER CLIENT
# ============================================================================

class FGPBrowserClient:
    """Client for FGP Browser daemon via UNIX socket."""

    def __init__(self, socket_path: Path = FGP_BROWSER_SOCKET):
        self.socket_path = socket_path

    def is_available(self) -> bool:
        """Check if daemon socket exists."""
        return self.socket_path.exists()

    def call(self, method: str, params: dict | None = None) -> tuple[dict, float]:
        """Call a method on the daemon, return (result, latency_ms)."""
        start = time.perf_counter()

        request = {
            "id": str(uuid.uuid4()),
            "v": 1,
            "method": method,
            "params": params or {},
        }

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(self.socket_path))
            sock.sendall((json.dumps(request) + "\n").encode())

            response_data = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            sock.close()
            latency_ms = (time.perf_counter() - start) * 1000

            response = json.loads(response_data.decode().strip())
            if not response.get("ok"):
                raise Exception(response.get("error", {}).get("message", "Unknown error"))

            return response.get("result", {}), latency_ms

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            raise Exception(f"FGP call failed: {e}") from e


# ============================================================================
# WORKFLOW IMPLEMENTATIONS
# ============================================================================

def workflow_hn_fgp(client: FGPBrowserClient) -> list[StepResult]:
    """
    HN workflow using FGP Browser daemon.
    4 steps: navigate -> snapshot -> click comments -> snapshot comments
    """
    steps = []

    # Step 1: Navigate to HN
    try:
        _, latency = client.call("browser.open", {"url": HN_URL})
        steps.append(StepResult("navigate_hn", latency, True))
    except Exception as e:
        steps.append(StepResult("navigate_hn", 0, False, error=str(e)))
        return steps

    # Step 2: Snapshot front page
    try:
        result, latency = client.call("browser.snapshot", {})
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("snapshot_list", latency, True, payload_size=payload))
    except Exception as e:
        steps.append(StepResult("snapshot_list", 0, False, error=str(e)))
        return steps

    # Step 3: Click first comments link (stays on HN)
    try:
        _, latency = client.call("browser.click", {"selector": HN_COMMENTS_SELECTOR_BROAD})
        steps.append(StepResult("click_comments", latency, True))
    except Exception as e:
        steps.append(StepResult("click_comments", 0, False, error=str(e)))
        return steps

    # Brief wait for page load
    time.sleep(0.3)

    # Step 4: Snapshot comments page
    try:
        result, latency = client.call("browser.snapshot", {})
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("snapshot_comments", latency, True, payload_size=payload))
    except Exception as e:
        steps.append(StepResult("snapshot_comments", 0, False, error=str(e)))

    return steps


def workflow_hn_agent_browser() -> list[StepResult]:
    """
    HN workflow using agent-browser CLI.
    Each command is a subprocess call.
    """
    steps = []
    cli = which("agent-browser")

    if not cli:
        return [StepResult("setup", 0, False, error="agent-browser not found")]

    def run_cmd(args: list[str]) -> tuple[bool, float, int, str | None]:
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [cli] + args,
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed = (time.perf_counter() - start) * 1000
            success = proc.returncode == 0
            payload = len(proc.stdout) if proc.stdout else 0
            error = proc.stderr[:200] if not success and proc.stderr else None
            return success, elapsed, payload, error
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed, 0, "Timeout after 30s"
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed, 0, str(e)[:200]

    # Step 1: Navigate
    success, latency, _, error = run_cmd(["open", HN_URL])
    steps.append(StepResult("navigate_hn", latency, success, error=error))
    if not success:
        return steps

    # Step 2: Snapshot
    success, latency, payload, error = run_cmd(["snapshot"])
    steps.append(StepResult("snapshot_list", latency, success, payload_size=payload, error=error))
    if not success:
        return steps

    # Step 3: Click first comments link using Playwright's >> nth=0 selector
    # Filter for item links (comments), not user links which come first in subtext
    success, latency, _, error = run_cmd(["click", "td.subtext a[href^='item'] >> nth=0"])
    steps.append(StepResult("click_comments", latency, success, error=error))
    if not success:
        return steps

    time.sleep(0.3)

    # Step 4: Snapshot comments
    success, latency, payload, error = run_cmd(["snapshot"])
    steps.append(StepResult("snapshot_comments", latency, success, payload_size=payload, error=error))

    return steps


def workflow_hn_playwright_mcp() -> list[StepResult]:
    """
    HN workflow using Playwright MCP.
    Each operation spawns a new MCP server (cold start model).
    """
    steps = []

    def call_mcp(tool_name: str, params: dict) -> tuple[bool, float, int, str | None]:
        """Call Playwright MCP tool via stdio."""
        start = time.perf_counter()

        # MCP client code
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
            content = result.content[0].text if result.content else ""
            print(json.dumps({{"content": content, "success": True}}))

asyncio.run(main())
'''
        try:
            proc = subprocess.run(
                ["python3", "-c", client_code],
                capture_output=True,
                timeout=60,
                text=True,
            )
            elapsed = (time.perf_counter() - start) * 1000

            if proc.returncode == 0:
                try:
                    output = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
                    payload = len(output.get("content", ""))
                except json.JSONDecodeError:
                    payload = len(proc.stdout) if proc.stdout else 0
                return True, elapsed, payload, None
            else:
                return False, elapsed, 0, proc.stderr[:200] if proc.stderr else "Unknown error"

        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed, 0, "Timeout after 60s"
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed, 0, str(e)[:200]

    # Step 1: Navigate
    success, latency, _, error = call_mcp("browser_navigate", {"url": HN_URL})
    steps.append(StepResult("navigate_hn", latency, success, error=error))
    if not success:
        return steps

    # Step 2: Snapshot
    success, latency, payload, error = call_mcp("browser_snapshot", {})
    steps.append(StepResult("snapshot_list", latency, success, payload_size=payload, error=error))
    if not success:
        return steps

    # Step 3: Click (Playwright clicks first match)
    success, latency, _, error = call_mcp("browser_click", {"selector": HN_COMMENTS_SELECTOR_BROAD})
    steps.append(StepResult("click_comments", latency, success, error=error))
    if not success:
        return steps

    time.sleep(0.3)

    # Step 4: Snapshot
    success, latency, payload, error = call_mcp("browser_snapshot", {})
    steps.append(StepResult("snapshot_comments", latency, success, payload_size=payload, error=error))

    return steps


# ============================================================================
# BENCHMARK RUNNER
# ============================================================================

TOOLS: dict[str, Callable[[], list[StepResult]]] = {
    "fgp": lambda: workflow_hn_fgp(FGPBrowserClient()),
    "agent_browser": workflow_hn_agent_browser,
    "playwright_mcp": workflow_hn_playwright_mcp,
}


def check_tool_available(tool: str) -> tuple[bool, str]:
    """Check if a tool is available."""
    if tool == "fgp":
        if FGP_BROWSER_SOCKET.exists():
            return True, "daemon running"
        return False, f"daemon not running (socket: {FGP_BROWSER_SOCKET})"

    elif tool == "agent_browser":
        cli = which("agent-browser")
        if cli:
            return True, f"found at {cli}"
        return False, "not installed"

    elif tool == "playwright_mcp":
        try:
            result = subprocess.run(["npx", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return True, "npx available"
            return False, "npx not working"
        except Exception as e:
            return False, str(e)

    return False, "unknown tool"


def run_workflow(tool: str, iteration: int) -> WorkflowResult:
    """Run a single workflow iteration."""
    start = time.perf_counter()

    try:
        workflow_fn = TOOLS[tool]
        steps = workflow_fn()
        total_latency = (time.perf_counter() - start) * 1000
        success = all(s.success for s in steps)

        return WorkflowResult(
            tool=tool,
            iteration=iteration,
            steps=steps,
            total_latency_ms=total_latency,
            step_count=len(steps),
            success=success,
        )
    except Exception as e:
        total_latency = (time.perf_counter() - start) * 1000
        return WorkflowResult(
            tool=tool,
            iteration=iteration,
            steps=[],
            total_latency_ms=total_latency,
            step_count=0,
            success=False,
            error=str(e),
        )


def compute_summary(results: list[WorkflowResult], tool: str) -> ToolSummary:
    """Compute statistical summary for a tool."""
    filtered = [r for r in results if r.tool == tool and r.success]
    all_for_tool = [r for r in results if r.tool == tool]

    if not filtered:
        return ToolSummary(
            tool=tool,
            iterations=len(all_for_tool),
            step_count=0,
            success_rate=0.0,
            mean_total_ms=0.0,
            median_total_ms=0.0,
            min_total_ms=0.0,
            max_total_ms=0.0,
            mean_per_step_ms=0.0,
            step_breakdown={},
        )

    total_latencies = [r.total_latency_ms for r in filtered]

    # Step breakdown
    step_latencies: dict[str, list[float]] = {}
    for result in filtered:
        for step in result.steps:
            if step.step_name not in step_latencies:
                step_latencies[step.step_name] = []
            step_latencies[step.step_name].append(step.latency_ms)

    step_breakdown = {name: statistics.mean(lats) for name, lats in step_latencies.items()}

    return ToolSummary(
        tool=tool,
        iterations=len(all_for_tool),
        step_count=filtered[0].step_count if filtered else 0,
        success_rate=len(filtered) / len(all_for_tool) if all_for_tool else 0.0,
        mean_total_ms=statistics.mean(total_latencies),
        median_total_ms=statistics.median(total_latencies),
        min_total_ms=min(total_latencies),
        max_total_ms=max(total_latencies),
        mean_per_step_ms=statistics.mean(total_latencies) / filtered[0].step_count if filtered else 0.0,
        step_breakdown=step_breakdown,
    )


def generate_markdown_report(report: BenchmarkReport) -> str:
    """Generate markdown summary."""
    lines = [
        "# HN Workflow Benchmark Results",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Iterations:** {report.iterations}",
        f"**Workflow:** {report.workflow}",
        "",
        "## Summary",
        "",
        "| Tool | Total (mean) | Per Step | Success | vs MCP |",
        "|------|--------------|----------|---------|--------|",
    ]

    # Find MCP baseline
    mcp_summary = next((s for s in report.summaries if s.tool == "playwright_mcp"), None)
    mcp_baseline = mcp_summary.mean_total_ms if mcp_summary and mcp_summary.mean_total_ms > 0 else 1

    for summary in report.summaries:
        if summary.mean_total_ms > 0:
            speedup = mcp_baseline / summary.mean_total_ms
            lines.append(
                f"| {summary.tool} | {summary.mean_total_ms:.0f}ms | "
                f"{summary.mean_per_step_ms:.0f}ms | {summary.success_rate*100:.0f}% | "
                f"**{speedup:.1f}x** |"
            )
        else:
            lines.append(
                f"| {summary.tool} | N/A | N/A | {summary.success_rate*100:.0f}% | N/A |"
            )

    lines.extend([
        "",
        "## Step Breakdown",
        "",
    ])

    for summary in report.summaries:
        if summary.step_breakdown:
            lines.append(f"### {summary.tool}")
            lines.append("")
            lines.append("| Step | Latency (mean) |")
            lines.append("|------|----------------|")
            for step_name, latency in summary.step_breakdown.items():
                lines.append(f"| {step_name} | {latency:.0f}ms |")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="HN Workflow Benchmark")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per tool")
    parser.add_argument("--tool", type=str, help="Run only specific tool (fgp, agent_browser, playwright_mcp)")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    print("HN Workflow Benchmark")
    print("=" * 60)
    print(f"Workflow: Navigate -> Snapshot -> Click Comments -> Snapshot")
    print(f"Iterations: {args.iterations}")
    print()

    # Pre-flight checks
    print("Pre-flight checks:")
    tools_to_run = [args.tool] if args.tool else list(TOOLS.keys())
    available_tools = []

    for tool in tools_to_run:
        available, msg = check_tool_available(tool)
        status = "OK" if available else "SKIP"
        print(f"  [{status}] {tool}: {msg}")
        if available:
            available_tools.append(tool)

    if not available_tools:
        print("\nNo tools available. Exiting.")
        sys.exit(1)

    print()

    # Run benchmarks
    results: list[WorkflowResult] = []

    for tool in available_tools:
        print(f"[{tool}]")

        for i in range(args.iterations):
            result = run_workflow(tool, i + 1)
            results.append(result)

            status = "OK" if result.success else "FAIL"
            step_times = " -> ".join(f"{s.latency_ms:.0f}ms" for s in result.steps)
            print(f"  Iter {i+1}: {result.total_latency_ms:.0f}ms total [{status}] ({step_times})")

            if not result.success and result.error:
                print(f"         Error: {result.error}")

            # Delay between iterations
            time.sleep(1)

        print()

    # Compute summaries
    summaries = [compute_summary(results, tool) for tool in available_tools]

    # Create report
    report = BenchmarkReport(
        generated_at=datetime.now().isoformat(),
        iterations=args.iterations,
        workflow="HN: navigate -> snapshot -> click comments -> snapshot",
        results=results,
        summaries=summaries,
    )

    # Print report
    print("=" * 60)
    print(generate_markdown_report(report))

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output or RESULTS_DIR / f"hn_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_dict = {
        "generated_at": report.generated_at,
        "iterations": report.iterations,
        "workflow": report.workflow,
        "results": [
            {
                "tool": r.tool,
                "iteration": r.iteration,
                "steps": [asdict(s) for s in r.steps],
                "total_latency_ms": r.total_latency_ms,
                "step_count": r.step_count,
                "success": r.success,
                "error": r.error,
            }
            for r in report.results
        ],
        "summaries": [asdict(s) for s in report.summaries],
    }

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
