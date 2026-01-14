#!/usr/bin/env python3
"""
Gmail Workflow Benchmark - API vs Browser Automation Comparison

Compares FGP's Gmail API daemon with browser automation on email workflows:

1. FGP Gmail API:
   - List inbox (get recent emails)
   - Read first email content

2. Browser automation (public mail simulator):
   - Navigate to mail page
   - Click first email
   - Extract content

Note: Google blocks automated browsers (Playwright/Chromium) from signing in,
so we use a public mail simulator for browser comparison.

Usage:
    python3 gmail_workflow_benchmark.py --iterations 3

CHANGELOG (recent first, max 5 entries)
01/14/2026 - Initial implementation (Claude)
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Any

# Constants
FGP_GMAIL_SOCKET = Path.home() / ".fgp" / "services" / "gmail" / "daemon.sock"
FGP_BROWSER_SOCKET = Path.home() / ".fgp" / "services" / "browser" / "daemon.sock"
RESULTS_DIR = Path(__file__).parent / "results"


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
    tool: str
    method: str  # "api" or "browser"
    iteration: int
    steps: list[StepResult]
    total_latency_ms: float
    step_count: int
    success: bool
    error: str | None = None


@dataclass
class ToolSummary:
    """Statistical summary for a tool."""
    tool: str
    method: str
    iterations: int
    step_count: int
    success_rate: float
    mean_total_ms: float
    median_total_ms: float
    min_total_ms: float
    max_total_ms: float
    mean_per_step_ms: float
    step_breakdown: dict[str, float]


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    generated_at: str
    iterations: int
    results: list[WorkflowResult] = field(default_factory=list)
    summaries: list[ToolSummary] = field(default_factory=list)


class FGPClient:
    """Generic FGP daemon client."""

    def __init__(self, socket_path: Path):
        self.socket_path = socket_path

    def is_available(self) -> bool:
        return self.socket_path.exists()

    def call(self, method: str, params: dict | None = None) -> tuple[dict, float]:
        """Call daemon method, return (result, latency_ms)."""
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


def workflow_gmail_api(gmail_client: FGPClient) -> list[StepResult]:
    """
    Gmail workflow using FGP Gmail API daemon.
    Steps: List inbox -> Read first email
    """
    steps = []

    # Step 1: List inbox (get 5 recent emails)
    try:
        result, latency = gmail_client.call("gmail.inbox", {"max_results": 5})
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("list_inbox", latency, True, payload_size=payload))

        # Get first email ID for step 2
        emails = result.get("emails", [])
        if not emails:
            steps.append(StepResult("read_email", 0, False, error="No emails found"))
            return steps
        first_email_id = emails[0].get("id")

    except Exception as e:
        steps.append(StepResult("list_inbox", 0, False, error=str(e)))
        return steps

    # Step 2: Read first email thread content
    try:
        thread_id = emails[0].get("thread_id")
        result, latency = gmail_client.call("gmail.thread", {"thread_id": thread_id})
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("read_email", latency, True, payload_size=payload))
    except Exception as e:
        steps.append(StepResult("read_email", 0, False, error=str(e)))

    return steps


def workflow_browser_mail(browser_client: FGPClient) -> list[StepResult]:
    """
    Mail-like workflow using FGP Browser daemon.
    Uses temp-mail.org as a public mail interface for comparison.
    Steps: Navigate -> Snapshot inbox -> Click email -> Snapshot content
    """
    steps = []

    # Using a public temporary email service for browser comparison
    # This simulates the same "open inbox, click email, read content" workflow

    # Step 1: Navigate to temp mail
    try:
        _, latency = browser_client.call("browser.open", {"url": "https://mail.tm/"})
        steps.append(StepResult("navigate_mail", latency, True))
    except Exception as e:
        steps.append(StepResult("navigate_mail", 0, False, error=str(e)))
        return steps

    time.sleep(0.5)  # Wait for page load

    # Step 2: Snapshot the mail interface
    try:
        result, latency = browser_client.call("browser.snapshot", {})
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("snapshot_inbox", latency, True, payload_size=payload))
    except Exception as e:
        steps.append(StepResult("snapshot_inbox", 0, False, error=str(e)))

    return steps


def workflow_browser_hn_email_pattern(browser_client: FGPClient) -> list[StepResult]:
    """
    Email-like workflow using HN (already authenticated benchmark).
    2-step workflow: List (snapshot) -> Read detail (click + snapshot)

    This provides a fair browser comparison without auth issues.
    """
    steps = []

    # Step 1: Navigate and snapshot (like listing inbox)
    try:
        _, latency = browser_client.call("browser.open", {"url": "https://news.ycombinator.com"})
        steps.append(StepResult("list_inbox_equiv", latency, True))
    except Exception as e:
        steps.append(StepResult("list_inbox_equiv", 0, False, error=str(e)))
        return steps

    # Step 2: Read detail (click + snapshot - like reading email)
    try:
        _, latency = browser_client.call("browser.click", {"selector": "td.subtext a[href^='item']"})
        time.sleep(0.3)
        result, latency2 = browser_client.call("browser.snapshot", {})
        total_latency = latency + latency2
        payload = len(json.dumps(result)) if result else 0
        steps.append(StepResult("read_email_equiv", total_latency, True, payload_size=payload))
    except Exception as e:
        steps.append(StepResult("read_email_equiv", 0, False, error=str(e)))

    return steps


def compute_summary(results: list[WorkflowResult], tool: str, method: str) -> ToolSummary:
    """Compute statistical summary."""
    filtered = [r for r in results if r.tool == tool and r.method == method and r.success]
    all_results = [r for r in results if r.tool == tool and r.method == method]

    if not filtered:
        return ToolSummary(
            tool=tool,
            method=method,
            iterations=len(all_results),
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

    step_latencies: dict[str, list[float]] = {}
    for result in filtered:
        for step in result.steps:
            if step.step_name not in step_latencies:
                step_latencies[step.step_name] = []
            step_latencies[step.step_name].append(step.latency_ms)

    step_breakdown = {name: statistics.mean(lats) for name, lats in step_latencies.items()}

    return ToolSummary(
        tool=tool,
        method=method,
        iterations=len(all_results),
        step_count=filtered[0].step_count if filtered else 0,
        success_rate=len(filtered) / len(all_results) if all_results else 0.0,
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
        "# Gmail Workflow Benchmark Results",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Iterations:** {report.iterations}",
        "",
        "## Summary",
        "",
        "| Tool | Method | Total (mean) | Per Step | Success |",
        "|------|--------|--------------|----------|---------|",
    ]

    for summary in report.summaries:
        if summary.mean_total_ms > 0:
            lines.append(
                f"| {summary.tool} | {summary.method} | {summary.mean_total_ms:.0f}ms | "
                f"{summary.mean_per_step_ms:.0f}ms | {summary.success_rate*100:.0f}% |"
            )

    lines.extend([
        "",
        "## Step Breakdown",
        "",
    ])

    for summary in report.summaries:
        if summary.step_breakdown:
            lines.append(f"### {summary.tool} ({summary.method})")
            lines.append("")
            lines.append("| Step | Latency (mean) |")
            lines.append("|------|----------------|")
            for step_name, latency in summary.step_breakdown.items():
                lines.append(f"| {step_name} | {latency:.0f}ms |")
            lines.append("")

    return "\n".join(lines)


def workflow_agent_browser_hn_email_pattern() -> list[StepResult]:
    """
    Email-like workflow using agent-browser CLI.
    2-step workflow: List (snapshot) -> Read detail (click + snapshot)
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
            return False, 30000, 0, "Timeout after 30s"
        except Exception as e:
            return False, 0, 0, str(e)[:200]

    # Step 1: Navigate and get inbox (like listing inbox)
    success, latency, _, error = run_cmd(["open", "https://news.ycombinator.com"])
    steps.append(StepResult("list_inbox_equiv", latency, success, error=error))
    if not success:
        return steps

    # Step 2: Read detail (click + snapshot - like reading email)
    success1, latency1, _, error1 = run_cmd(["click", "td.subtext a[href^='item'] >> nth=0"])
    if not success1:
        steps.append(StepResult("read_email_equiv", latency1, False, error=error1))
        return steps

    time.sleep(0.3)
    success2, latency2, payload, error2 = run_cmd(["snapshot"])
    total_latency = latency1 + latency2
    steps.append(StepResult("read_email_equiv", total_latency, success2, payload_size=payload, error=error2))

    return steps


def main():
    parser = argparse.ArgumentParser(description="Gmail Workflow Benchmark")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per tool")
    args = parser.parse_args()

    print("Gmail Workflow Benchmark")
    print("=" * 60)
    print("Comparing: FGP Gmail API vs FGP Browser vs agent-browser")
    print(f"Iterations: {args.iterations}")
    print()

    # Check tool availability
    gmail_client = FGPClient(FGP_GMAIL_SOCKET)
    browser_client = FGPClient(FGP_BROWSER_SOCKET)
    agent_browser_cli = which("agent-browser")

    print("Pre-flight checks:")
    gmail_ok = gmail_client.is_available()
    browser_ok = browser_client.is_available()
    agent_ok = agent_browser_cli is not None
    print(f"  [{'OK' if gmail_ok else 'SKIP'}] FGP Gmail API daemon")
    print(f"  [{'OK' if browser_ok else 'SKIP'}] FGP Browser daemon")
    print(f"  [{'OK' if agent_ok else 'SKIP'}] agent-browser CLI")
    print()

    results: list[WorkflowResult] = []

    # Run Gmail API benchmark
    if gmail_ok:
        print("[FGP Gmail API]")
        for i in range(args.iterations):
            start = time.perf_counter()
            try:
                steps = workflow_gmail_api(gmail_client)
                total_latency = (time.perf_counter() - start) * 1000
                success = all(s.success for s in steps)
                result = WorkflowResult(
                    tool="fgp_gmail",
                    method="api",
                    iteration=i + 1,
                    steps=steps,
                    total_latency_ms=total_latency,
                    step_count=len(steps),
                    success=success,
                )
            except Exception as e:
                result = WorkflowResult(
                    tool="fgp_gmail",
                    method="api",
                    iteration=i + 1,
                    steps=[],
                    total_latency_ms=0,
                    step_count=0,
                    success=False,
                    error=str(e),
                )
            results.append(result)

            status = "OK" if result.success else "FAIL"
            step_times = " -> ".join(f"{s.latency_ms:.0f}ms" for s in result.steps)
            print(f"  Iter {i+1}: {result.total_latency_ms:.0f}ms [{status}] ({step_times})")
            time.sleep(0.5)
        print()

    # Run Browser benchmark (email-like workflow on HN)
    if browser_ok:
        print("[FGP Browser (HN email-like pattern)]")
        for i in range(args.iterations):
            start = time.perf_counter()
            try:
                steps = workflow_browser_hn_email_pattern(browser_client)
                total_latency = (time.perf_counter() - start) * 1000
                success = all(s.success for s in steps)
                result = WorkflowResult(
                    tool="fgp_browser",
                    method="browser",
                    iteration=i + 1,
                    steps=steps,
                    total_latency_ms=total_latency,
                    step_count=len(steps),
                    success=success,
                )
            except Exception as e:
                result = WorkflowResult(
                    tool="fgp_browser",
                    method="browser",
                    iteration=i + 1,
                    steps=[],
                    total_latency_ms=0,
                    step_count=0,
                    success=False,
                    error=str(e),
                )
            results.append(result)

            status = "OK" if result.success else "FAIL"
            step_times = " -> ".join(f"{s.latency_ms:.0f}ms" for s in result.steps)
            print(f"  Iter {i+1}: {result.total_latency_ms:.0f}ms [{status}] ({step_times})")
            time.sleep(0.5)
        print()

    # Run agent-browser benchmark (email-like workflow on HN)
    if agent_ok:
        print("[agent-browser (HN email-like pattern)]")
        for i in range(args.iterations):
            start = time.perf_counter()
            try:
                steps = workflow_agent_browser_hn_email_pattern()
                total_latency = (time.perf_counter() - start) * 1000
                success = all(s.success for s in steps)
                result = WorkflowResult(
                    tool="agent_browser",
                    method="browser",
                    iteration=i + 1,
                    steps=steps,
                    total_latency_ms=total_latency,
                    step_count=len(steps),
                    success=success,
                )
            except Exception as e:
                result = WorkflowResult(
                    tool="agent_browser",
                    method="browser",
                    iteration=i + 1,
                    steps=[],
                    total_latency_ms=0,
                    step_count=0,
                    success=False,
                    error=str(e),
                )
            results.append(result)

            status = "OK" if result.success else "FAIL"
            step_times = " -> ".join(f"{s.latency_ms:.0f}ms" for s in result.steps)
            print(f"  Iter {i+1}: {result.total_latency_ms:.0f}ms [{status}] ({step_times})")
            time.sleep(0.5)
        print()

    # Compute summaries
    summaries = []
    if gmail_ok:
        summaries.append(compute_summary(results, "fgp_gmail", "api"))
    if browser_ok:
        summaries.append(compute_summary(results, "fgp_browser", "browser"))
    if agent_ok:
        summaries.append(compute_summary(results, "agent_browser", "browser"))

    # Create report
    report = BenchmarkReport(
        generated_at=datetime.now().isoformat(),
        iterations=args.iterations,
        results=results,
        summaries=summaries,
    )

    # Print report
    print("=" * 60)
    print(generate_markdown_report(report))

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"gmail_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_dict = {
        "generated_at": report.generated_at,
        "iterations": report.iterations,
        "results": [
            {
                "tool": r.tool,
                "method": r.method,
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
