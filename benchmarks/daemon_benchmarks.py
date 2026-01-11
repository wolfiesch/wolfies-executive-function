#!/usr/bin/env python3
"""
Comprehensive Daemon Benchmarks for Gmail and Calendar.

This script compares performance across 4 access modes:
1. Direct CLI (cold) - Python spawn + imports + OAuth + API per call
2. Daemon CLI (--use-daemon) - Unix socket to warm daemon
3. MCP Server - Full MCP protocol overhead (reference baseline)
4. Raw daemon call - In-process socket call (best case)

Usage:
    python3 benchmarks/daemon_benchmarks.py --full -o results/daemon_comprehensive.json
    python3 benchmarks/daemon_benchmarks.py --quick -o results/daemon_quick.json
    python3 benchmarks/daemon_benchmarks.py --gmail-only -o results/gmail_daemon.json

CHANGELOG (recent first, max 5 entries):
01/08/2026 - Initial implementation for Twitter release data gathering (Claude)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import select
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# CLI paths
GMAIL_CLI = REPO_ROOT / "src" / "integrations" / "gmail" / "gmail_cli.py"
CALENDAR_CLI = REPO_ROOT / "src" / "integrations" / "google_calendar" / "calendar_cli.py"

# Daemon paths
DAEMON_SERVER = REPO_ROOT / "src" / "integrations" / "google_daemon" / "server.py"
DAEMON_SOCKET = Path.home() / ".wolfies-google" / "daemon.sock"
DAEMON_PID = Path.home() / ".wolfies-google" / "daemon.pid"

# MCP Server paths
GMAIL_MCP = REPO_ROOT / "src" / "integrations" / "gmail" / "server.py"
CALENDAR_MCP = REPO_ROOT / "src" / "integrations" / "google_calendar" / "server.py"

# Bytes per token estimate for output sizing
BYTES_PER_TOKEN = 4.0


def _ts() -> str:
    """Current timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _ensure_parent(path: Path) -> None:
    """Ensure parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single workload."""
    workload_id: str
    mode: str  # "cli_cold", "cli_daemon", "mcp", "daemon_raw"
    iterations: int
    warmup: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    success_rate: float
    mean_stdout_bytes: Optional[float] = None
    approx_tokens: Optional[int] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class WorkloadSpec:
    """Specification for a benchmark workload."""
    workload_id: str
    service: str  # "gmail" or "calendar"
    label: str
    cli_args: List[str]
    daemon_method: str
    daemon_params: Dict[str, Any]
    mcp_tool: str
    mcp_args: Dict[str, Any]


def _percentile(values: List[float], p: float) -> float:
    """Calculate percentile (0-100)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int((p / 100) * (len(sorted_vals) - 1))
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def _get_workloads() -> List[WorkloadSpec]:
    """Define benchmark workloads for Gmail and Calendar."""
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")

    return [
        # Gmail workloads
        WorkloadSpec(
            workload_id="GMAIL_UNREAD_COUNT",
            service="gmail",
            label="Gmail unread count",
            cli_args=["unread", "--json"],
            daemon_method="gmail.unread_count",
            daemon_params={},
            mcp_tool="get_unread_count",
            mcp_args={},
        ),
        WorkloadSpec(
            workload_id="GMAIL_LIST_5",
            service="gmail",
            label="Gmail list 5 emails",
            cli_args=["list", "5", "--json"],
            daemon_method="gmail.list",
            daemon_params={"count": 5},
            mcp_tool="list_emails",
            mcp_args={"max_results": 5},
        ),
        WorkloadSpec(
            workload_id="GMAIL_LIST_10",
            service="gmail",
            label="Gmail list 10 emails",
            cli_args=["list", "10", "--json"],
            daemon_method="gmail.list",
            daemon_params={"count": 10},
            mcp_tool="list_emails",
            mcp_args={"max_results": 10},
        ),
        WorkloadSpec(
            workload_id="GMAIL_LIST_25",
            service="gmail",
            label="Gmail list 25 emails",
            cli_args=["list", "25", "--json"],
            daemon_method="gmail.list",
            daemon_params={"count": 25},
            mcp_tool="list_emails",
            mcp_args={"max_results": 25},
        ),
        WorkloadSpec(
            workload_id="GMAIL_SEARCH_SIMPLE",
            service="gmail",
            label="Gmail search (from:me)",
            cli_args=["search", "from:me", "--max-results", "5", "--json"],
            daemon_method="gmail.search",
            daemon_params={"query": "from:me", "max_results": 5},
            mcp_tool="search_emails",
            mcp_args={"query": "from:me", "max_results": 5},
        ),
        # Calendar workloads
        WorkloadSpec(
            workload_id="CALENDAR_TODAY",
            service="calendar",
            label="Calendar today's events",
            cli_args=["today", "--json"],
            daemon_method="calendar.today",
            daemon_params={},
            mcp_tool="list_events",
            mcp_args={"days_ahead": 1, "max_results": 20},
        ),
        WorkloadSpec(
            workload_id="CALENDAR_WEEK",
            service="calendar",
            label="Calendar week's events",
            cli_args=["week", "--json"],
            daemon_method="calendar.week",
            daemon_params={},
            mcp_tool="list_events",
            mcp_args={"days_ahead": 7, "max_results": 50},
        ),
        WorkloadSpec(
            workload_id="CALENDAR_FREE_30MIN",
            service="calendar",
            label="Calendar find 30-min slots",
            cli_args=["free", "30", "--json"],
            daemon_method="calendar.free",
            daemon_params={"duration": 30, "days": 7, "limit": 10},
            mcp_tool="find_free_time",
            mcp_args={"duration_minutes": 30, "days_ahead": 7, "max_slots": 10},
        ),
        WorkloadSpec(
            workload_id="CALENDAR_FREE_60MIN",
            service="calendar",
            label="Calendar find 60-min slots",
            cli_args=["free", "60", "--json"],
            daemon_method="calendar.free",
            daemon_params={"duration": 60, "days": 7, "limit": 5},
            mcp_tool="find_free_time",
            mcp_args={"duration_minutes": 60, "days_ahead": 7, "max_slots": 5},
        ),
    ]


# =============================================================================
# CLI BENCHMARKING (cold and daemon modes)
# =============================================================================

def _run_cli_command(
    cli_path: Path,
    args: List[str],
    timeout: int = 60,
    cwd: Optional[Path] = None,
) -> tuple[float, bool, str, int]:
    """
    Run a CLI command and measure execution time.

    Returns:
        (time_ms, success, output, stdout_bytes)
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", str(cli_path)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or REPO_ROOT),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        stdout_bytes = len(output.encode("utf-8", errors="ignore"))
        return elapsed_ms, success, output, stdout_bytes
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False, "TIMEOUT", 0
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False, str(e), 0


def benchmark_cli_mode(
    workload: WorkloadSpec,
    *,
    use_daemon: bool,
    iterations: int,
    warmup: int,
    timeout: int = 60,
) -> BenchmarkResult:
    """Benchmark a workload using CLI (with or without daemon)."""
    mode = "cli_daemon" if use_daemon else "cli_cold"
    cli_path = GMAIL_CLI if workload.service == "gmail" else CALENDAR_CLI

    args = workload.cli_args.copy()
    if use_daemon:
        args = ["--use-daemon"] + args

    print(f"  [{_ts()}] {workload.workload_id} ({mode}): ", end="", flush=True)

    timings: List[float] = []
    stdout_bytes_list: List[int] = []
    successes = 0

    # Warmup runs
    for _ in range(warmup):
        _run_cli_command(cli_path, args, timeout=timeout)

    # Measured runs
    for _ in range(iterations):
        elapsed_ms, success, output, stdout_bytes = _run_cli_command(cli_path, args, timeout=timeout)
        timings.append(elapsed_ms)
        if success:
            successes += 1
            stdout_bytes_list.append(stdout_bytes)

    success_rate = (successes / iterations) * 100 if iterations > 0 else 0
    mean_ms = statistics.mean(timings) if timings else 0
    std_dev = statistics.stdev(timings) if len(timings) > 1 else 0
    mean_bytes = statistics.mean(stdout_bytes_list) if stdout_bytes_list else None

    print(f"mean={mean_ms:.1f}ms p95={_percentile(timings, 95):.1f}ms ok={successes}/{iterations}")

    return BenchmarkResult(
        workload_id=workload.workload_id,
        mode=mode,
        iterations=iterations,
        warmup=warmup,
        mean_ms=mean_ms,
        median_ms=statistics.median(timings) if timings else 0,
        p95_ms=_percentile(timings, 95),
        p99_ms=_percentile(timings, 99),
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        std_dev_ms=std_dev,
        success_rate=success_rate,
        mean_stdout_bytes=mean_bytes,
        approx_tokens=int(mean_bytes / BYTES_PER_TOKEN) if mean_bytes else None,
    )


# =============================================================================
# RAW DAEMON BENCHMARKING (in-process socket call)
# =============================================================================

def _daemon_call(
    method: str,
    params: Dict[str, Any],
    socket_path: Path = DAEMON_SOCKET,
    timeout_s: float = 30.0,
) -> tuple[float, bool, Dict[str, Any]]:
    """
    Call daemon directly via socket (in-process).

    Returns:
        (time_ms, success, response_dict)
    """
    request = {
        "id": f"bench_{int(time.time() * 1000)}",
        "method": method,
        "params": params,
        "v": 1,
    }

    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))

            request_line = json.dumps(request, separators=(",", ":")) + "\n"
            s.sendall(request_line.encode("utf-8"))

            response_data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            elapsed_ms = (time.perf_counter() - start) * 1000

            if not response_data:
                return elapsed_ms, False, {}

            response = json.loads(response_data.decode("utf-8").strip())
            success = response.get("ok", False)
            return elapsed_ms, success, response

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False, {"error": str(e)}


def benchmark_daemon_raw(
    workload: WorkloadSpec,
    *,
    iterations: int,
    warmup: int,
) -> BenchmarkResult:
    """Benchmark a workload using raw daemon socket calls (in-process)."""
    print(f"  [{_ts()}] {workload.workload_id} (daemon_raw): ", end="", flush=True)

    timings: List[float] = []
    successes = 0

    # Warmup runs
    for _ in range(warmup):
        _daemon_call(workload.daemon_method, workload.daemon_params)

    # Measured runs
    for _ in range(iterations):
        elapsed_ms, success, response = _daemon_call(workload.daemon_method, workload.daemon_params)
        timings.append(elapsed_ms)
        if success:
            successes += 1

    success_rate = (successes / iterations) * 100 if iterations > 0 else 0
    mean_ms = statistics.mean(timings) if timings else 0
    std_dev = statistics.stdev(timings) if len(timings) > 1 else 0

    print(f"mean={mean_ms:.1f}ms p95={_percentile(timings, 95):.1f}ms ok={successes}/{iterations}")

    return BenchmarkResult(
        workload_id=workload.workload_id,
        mode="daemon_raw",
        iterations=iterations,
        warmup=warmup,
        mean_ms=mean_ms,
        median_ms=statistics.median(timings) if timings else 0,
        p95_ms=_percentile(timings, 95),
        p99_ms=_percentile(timings, 99),
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        std_dev_ms=std_dev,
        success_rate=success_rate,
    )


# =============================================================================
# MCP SERVER BENCHMARKING
# =============================================================================

def _mcp_read_response(
    proc: subprocess.Popen,
    expected_id: int,
    timeout_s: float,
) -> tuple[Optional[Dict], Optional[str], float]:
    """Read a JSON-RPC response from MCP server."""
    if proc.stdout is None:
        return None, "missing stdout", 0

    start = time.perf_counter()
    deadline = time.time() + timeout_s

    while True:
        if time.time() >= deadline:
            return None, "TIMEOUT", (time.perf_counter() - start) * 1000
        if proc.poll() is not None:
            return None, f"EXITED({proc.returncode})", (time.perf_counter() - start) * 1000

        r, _, _ = select.select([proc.stdout], [], [], 0.1)
        if not r:
            continue
        line = proc.stdout.readline()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", errors="ignore"))
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("id") == expected_id:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return obj, None, elapsed_ms


def _mcp_send(proc: subprocess.Popen, msg: Dict) -> None:
    """Send JSON-RPC message to MCP server."""
    if proc.stdin is None:
        raise RuntimeError("missing stdin")
    proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
    proc.stdin.flush()


def benchmark_mcp_mode(
    workload: WorkloadSpec,
    *,
    iterations: int,
    warmup: int,
    timeout: int = 60,
) -> BenchmarkResult:
    """Benchmark a workload using MCP server."""
    print(f"  [{_ts()}] {workload.workload_id} (mcp): ", end="", flush=True)

    mcp_path = GMAIL_MCP if workload.service == "gmail" else CALENDAR_MCP

    timings: List[float] = []
    successes = 0
    total_init_ms = 0

    total_calls = warmup + iterations

    # For MCP, we need to spawn a server, initialize it, then run calls
    try:
        proc = subprocess.Popen(
            ["python3", str(mcp_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(REPO_ROOT),
        )

        # Initialize MCP session
        init_start = time.perf_counter()
        _mcp_send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bench", "version": "0.1"},
            },
        })

        resp, err, _ = _mcp_read_response(proc, 1, timeout)
        if err or not resp:
            print(f"INIT FAILED: {err}")
            proc.terminate()
            return BenchmarkResult(
                workload_id=workload.workload_id,
                mode="mcp",
                iterations=iterations,
                warmup=warmup,
                mean_ms=0,
                median_ms=0,
                p95_ms=0,
                p99_ms=0,
                min_ms=0,
                max_ms=0,
                std_dev_ms=0,
                success_rate=0,
                notes=["MCP init failed"],
            )

        total_init_ms = (time.perf_counter() - init_start) * 1000

        # Send initialized notification
        _mcp_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # List tools
        _mcp_send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        _mcp_read_response(proc, 2, timeout)

        # Run warmup + measured calls
        next_id = 100
        for i in range(total_calls):
            next_id += 1
            call_start = time.perf_counter()

            _mcp_send(proc, {
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": workload.mcp_tool,
                    "arguments": workload.mcp_args,
                },
            })

            resp, err, _ = _mcp_read_response(proc, next_id, timeout)
            call_ms = (time.perf_counter() - call_start) * 1000

            if i >= warmup:  # Skip warmup in measurements
                timings.append(call_ms)
                if err is None and resp and "error" not in resp:
                    successes += 1

        proc.terminate()
        proc.wait(timeout=2)

    except Exception as e:
        print(f"ERROR: {e}")
        return BenchmarkResult(
            workload_id=workload.workload_id,
            mode="mcp",
            iterations=iterations,
            warmup=warmup,
            mean_ms=0,
            median_ms=0,
            p95_ms=0,
            p99_ms=0,
            min_ms=0,
            max_ms=0,
            std_dev_ms=0,
            success_rate=0,
            notes=[f"Error: {e}"],
        )

    success_rate = (successes / iterations) * 100 if iterations > 0 else 0
    mean_ms = statistics.mean(timings) if timings else 0
    std_dev = statistics.stdev(timings) if len(timings) > 1 else 0

    print(f"mean={mean_ms:.1f}ms p95={_percentile(timings, 95):.1f}ms ok={successes}/{iterations} init={total_init_ms:.0f}ms")

    return BenchmarkResult(
        workload_id=workload.workload_id,
        mode="mcp",
        iterations=iterations,
        warmup=warmup,
        mean_ms=mean_ms,
        median_ms=statistics.median(timings) if timings else 0,
        p95_ms=_percentile(timings, 95),
        p99_ms=_percentile(timings, 99),
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        std_dev_ms=std_dev,
        success_rate=success_rate,
        notes=[f"Init overhead: {total_init_ms:.0f}ms"],
    )


# =============================================================================
# DAEMON MANAGEMENT
# =============================================================================

def is_daemon_running() -> bool:
    """Check if Google daemon is running."""
    if not DAEMON_SOCKET.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            s.connect(str(DAEMON_SOCKET))
        return True
    except Exception:
        return False


def start_daemon_for_bench() -> float:
    """Start daemon and return time-to-ready in ms."""
    if is_daemon_running():
        return 0  # Already running

    start = time.perf_counter()
    subprocess.run(
        ["python3", str(DAEMON_SERVER), "start"],
        capture_output=True,
        timeout=15,
        cwd=str(REPO_ROOT),
    )

    # Wait for daemon to be ready
    deadline = time.time() + 10
    while time.time() < deadline:
        if is_daemon_running():
            return (time.perf_counter() - start) * 1000
        time.sleep(0.1)

    raise TimeoutError("Daemon did not start in time")


def stop_daemon_for_bench() -> None:
    """Stop the daemon if running."""
    subprocess.run(
        ["python3", str(DAEMON_SERVER), "stop"],
        capture_output=True,
        timeout=5,
        cwd=str(REPO_ROOT),
    )


# =============================================================================
# SUMMARY AND OUTPUT
# =============================================================================

def generate_summary_tables(results: List[BenchmarkResult]) -> str:
    """Generate markdown summary tables."""
    lines = []
    lines.append("# Google Daemon Benchmark Results\n")
    lines.append(f"Generated: {_ts()}\n")

    # Group by workload
    workloads = sorted(set(r.workload_id for r in results))
    modes = ["cli_cold", "cli_daemon", "daemon_raw", "mcp"]

    # Main comparison table
    lines.append("## Performance Comparison\n")
    lines.append("| Workload | CLI Cold | CLI+Daemon | Raw Daemon | MCP | Speedup (CLI→Daemon) |")
    lines.append("|----------|----------|------------|------------|-----|---------------------|")

    for wid in workloads:
        w_results = {r.mode: r for r in results if r.workload_id == wid}

        cold = w_results.get("cli_cold")
        daemon = w_results.get("cli_daemon")
        raw = w_results.get("daemon_raw")
        mcp = w_results.get("mcp")

        cold_ms = f"{cold.mean_ms:.0f}ms" if cold else "-"
        daemon_ms = f"{daemon.mean_ms:.0f}ms" if daemon else "-"
        raw_ms = f"{raw.mean_ms:.0f}ms" if raw else "-"
        mcp_ms = f"{mcp.mean_ms:.0f}ms" if mcp else "-"

        speedup = ""
        if cold and daemon and cold.mean_ms > 0:
            speedup_val = cold.mean_ms / daemon.mean_ms
            speedup = f"**{speedup_val:.1f}x**"

        lines.append(f"| {wid} | {cold_ms} | {daemon_ms} | {raw_ms} | {mcp_ms} | {speedup} |")

    lines.append("\n")

    # Detailed stats table
    lines.append("## Detailed Statistics\n")
    lines.append("| Workload | Mode | Mean | P50 | P95 | P99 | StdDev | OK% |")
    lines.append("|----------|------|------|-----|-----|-----|--------|-----|")

    for r in sorted(results, key=lambda x: (x.workload_id, x.mode)):
        lines.append(
            f"| {r.workload_id} | {r.mode} | {r.mean_ms:.1f}ms | {r.median_ms:.1f}ms | "
            f"{r.p95_ms:.1f}ms | {r.p99_ms:.1f}ms | {r.std_dev_ms:.1f}ms | {r.success_rate:.0f}% |"
        )

    lines.append("\n")

    # Summary stats
    lines.append("## Summary\n")

    cli_cold_results = [r for r in results if r.mode == "cli_cold"]
    cli_daemon_results = [r for r in results if r.mode == "cli_daemon"]

    if cli_cold_results and cli_daemon_results:
        avg_cold = statistics.mean(r.mean_ms for r in cli_cold_results)
        avg_daemon = statistics.mean(r.mean_ms for r in cli_daemon_results)
        avg_speedup = avg_cold / avg_daemon if avg_daemon > 0 else 0

        lines.append(f"- Average CLI Cold: {avg_cold:.0f}ms")
        lines.append(f"- Average CLI Daemon: {avg_daemon:.0f}ms")
        lines.append(f"- **Average Speedup: {avg_speedup:.1f}x**")

    return "\n".join(lines)


def print_results_summary(results: List[BenchmarkResult]) -> None:
    """Print summary to console."""
    print("\n" + "=" * 80)
    print("                     DAEMON BENCHMARK SUMMARY")
    print("=" * 80)

    # Group by workload
    workloads = sorted(set(r.workload_id for r in results))

    print(f"\n{'Workload':<25} | {'CLI Cold':>10} | {'CLI+Daemon':>12} | {'Speedup':>8}")
    print("-" * 65)

    speedups = []
    for wid in workloads:
        cold = next((r for r in results if r.workload_id == wid and r.mode == "cli_cold"), None)
        daemon = next((r for r in results if r.workload_id == wid and r.mode == "cli_daemon"), None)

        cold_str = f"{cold.mean_ms:.0f}ms" if cold else "-"
        daemon_str = f"{daemon.mean_ms:.0f}ms" if daemon else "-"

        speedup_str = ""
        if cold and daemon and daemon.mean_ms > 0:
            speedup = cold.mean_ms / daemon.mean_ms
            speedups.append(speedup)
            speedup_str = f"{speedup:.1f}x"

        print(f"{wid:<25} | {cold_str:>10} | {daemon_str:>12} | {speedup_str:>8}")

    if speedups:
        avg_speedup = statistics.mean(speedups)
        print("-" * 65)
        print(f"{'AVERAGE'::<25} | {'':<10} | {'':<12} | {avg_speedup:.1f}x ⭐")

    print("=" * 80)


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comprehensive daemon benchmarks for Gmail and Calendar"
    )
    parser.add_argument("--full", action="store_true", help="Run full benchmark suite (all modes)")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark (fewer iterations)")
    parser.add_argument("--iterations", "-n", type=int, default=5, help="Iterations per workload (default: 5)")
    parser.add_argument("--warmup", "-w", type=int, default=2, help="Warmup iterations (default: 2)")
    parser.add_argument("--gmail-only", action="store_true", help="Only benchmark Gmail")
    parser.add_argument("--calendar-only", action="store_true", help="Only benchmark Calendar")
    parser.add_argument("--skip-mcp", action="store_true", help="Skip MCP server benchmarks")
    parser.add_argument("--skip-daemon", action="store_true", help="Skip daemon benchmarks")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file")
    parser.add_argument("--tables", "-t", type=str, help="Output markdown tables file")
    args = parser.parse_args()

    iterations = args.iterations
    warmup = args.warmup

    if args.quick:
        iterations = 3
        warmup = 1

    # Get workloads
    workloads = _get_workloads()

    if args.gmail_only:
        workloads = [w for w in workloads if w.service == "gmail"]
    elif args.calendar_only:
        workloads = [w for w in workloads if w.service == "calendar"]

    print(f"\n{'#' * 60}")
    print("Google Daemon Benchmarks")
    print(f"Iterations: {iterations}, Warmup: {warmup}")
    print(f"Workloads: {len(workloads)}")
    print(f"{'#' * 60}\n")

    results: List[BenchmarkResult] = []

    # Check/start daemon
    daemon_available = False
    daemon_startup_ms = 0
    if not args.skip_daemon:
        print(f"[{_ts()}] Checking daemon status...")
        if not is_daemon_running():
            print(f"[{_ts()}] Starting daemon...")
            try:
                daemon_startup_ms = start_daemon_for_bench()
                print(f"[{_ts()}] Daemon started in {daemon_startup_ms:.0f}ms")
                daemon_available = True
            except Exception as e:
                print(f"[{_ts()}] Failed to start daemon: {e}")
        else:
            print(f"[{_ts()}] Daemon already running")
            daemon_available = True

    # Run benchmarks
    for workload in workloads:
        print(f"\n[{_ts()}] === {workload.label} ===")

        # Mode 1: CLI Cold (direct, no daemon)
        results.append(benchmark_cli_mode(
            workload,
            use_daemon=False,
            iterations=iterations,
            warmup=warmup,
        ))

        # Mode 2: CLI with Daemon
        if daemon_available:
            results.append(benchmark_cli_mode(
                workload,
                use_daemon=True,
                iterations=iterations,
                warmup=warmup,
            ))

            # Mode 3: Raw daemon (in-process socket)
            results.append(benchmark_daemon_raw(
                workload,
                iterations=iterations,
                warmup=warmup,
            ))

        # Mode 4: MCP Server
        if not args.skip_mcp and args.full:
            results.append(benchmark_mcp_mode(
                workload,
                iterations=iterations,
                warmup=warmup,
            ))

    # Print summary
    print_results_summary(results)

    # Generate output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_data = {
        "generated_at": _ts(),
        "metadata": {
            "iterations": iterations,
            "warmup": warmup,
            "daemon_startup_ms": daemon_startup_ms,
            "workload_count": len(workloads),
        },
        "results": [asdict(r) for r in results],
    }

    # Save JSON
    if args.output:
        out_path = Path(args.output)
        _ensure_parent(out_path)
        out_path.write_text(json.dumps(output_data, indent=2))
        print(f"\nResults saved to: {out_path}")
    else:
        default_out = REPO_ROOT / "benchmarks" / "results" / f"daemon_comprehensive_{timestamp}.json"
        _ensure_parent(default_out)
        default_out.write_text(json.dumps(output_data, indent=2))
        print(f"\nResults saved to: {default_out}")

    # Save markdown tables
    tables_content = generate_summary_tables(results)
    if args.tables:
        tables_path = Path(args.tables)
        _ensure_parent(tables_path)
        tables_path.write_text(tables_content)
        print(f"Tables saved to: {tables_path}")
    else:
        default_tables = REPO_ROOT / "benchmarks" / "results" / f"daemon_summary_tables_{timestamp}.md"
        _ensure_parent(default_tables)
        default_tables.write_text(tables_content)
        print(f"Tables saved to: {default_tables}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
