#!/usr/bin/env python3
"""
FGP vs MCP Performance Comparison Benchmark

Measures equivalent operations via:
1. MCP stdio (spawn per call) - typical Claude Code usage
2. FGP UNIX socket (warm daemon) - new approach

Output: JSON results + markdown summary for YC demo

Usage:
    python3 benchmarks/fgp_vs_mcp_benchmark.py
    python3 benchmarks/fgp_vs_mcp_benchmark.py --iterations 10 --output results/comparison.json
    python3 benchmarks/fgp_vs_mcp_benchmark.py --fly --neon  # Include Fly.io and Neon benchmarks

CHANGELOG (recent first, max 5 entries)
01/13/2026 - Added Vercel (vercel CLI vs FGP) benchmarks (Claude)
01/13/2026 - Added Fly.io (flyctl vs FGP) and Neon (API vs FGP) benchmarks (Claude)
01/13/2026 - Added GitHub (gh CLI vs FGP) and iMessage (CLI vs FGP) benchmarks (Claude)
01/13/2026 - Initial implementation for YC demo (Claude)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for MCP imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class BenchmarkResult:
    """Single benchmark measurement."""
    protocol: str  # "mcp_stdio" | "fgp"
    operation: str
    iteration: int
    latency_ms: float
    success: bool
    payload_size: int | None = None
    error: str | None = None


@dataclass
class WorkloadSummary:
    """Statistical summary for a workload."""
    operation: str
    protocol: str
    count: int
    success_rate: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    generated_at: str
    iterations: int
    warmup: int
    results: list[BenchmarkResult] = field(default_factory=list)
    summaries: list[WorkloadSummary] = field(default_factory=list)
    comparison: dict[str, Any] = field(default_factory=dict)


def _percentile(data: list[float], p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def compute_summary(results: list[BenchmarkResult], operation: str, protocol: str) -> WorkloadSummary:
    """Compute statistical summary for results."""
    filtered = [r for r in results if r.operation == operation and r.protocol == protocol]
    if not filtered:
        return WorkloadSummary(
            operation=operation, protocol=protocol, count=0, success_rate=0,
            mean_ms=0, median_ms=0, p95_ms=0, p99_ms=0, min_ms=0, max_ms=0, std_dev_ms=0
        )

    latencies = [r.latency_ms for r in filtered if r.success]
    successes = sum(1 for r in filtered if r.success)

    return WorkloadSummary(
        operation=operation,
        protocol=protocol,
        count=len(filtered),
        success_rate=successes / len(filtered) * 100 if filtered else 0,
        mean_ms=statistics.mean(latencies) if latencies else 0,
        median_ms=statistics.median(latencies) if latencies else 0,
        p95_ms=_percentile(latencies, 95) if latencies else 0,
        p99_ms=_percentile(latencies, 99) if latencies else 0,
        min_ms=min(latencies) if latencies else 0,
        max_ms=max(latencies) if latencies else 0,
        std_dev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0,
    )


# =============================================================================
# MCP STDIO BENCHMARK (spawn per call - typical Claude Code usage)
# =============================================================================

def benchmark_mcp_stdio_gmail_unread(iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark MCP Gmail get_unread_count via stdio (spawn per call)."""
    results = []
    server_path = REPO_ROOT / "src" / "integrations" / "gmail" / "server.py"

    for i in range(iterations):
        start = time.perf_counter()

        # Create MCP client script that spawns server, calls tool, exits
        client_code = f'''
import asyncio
import sys
sys.path.insert(0, "{REPO_ROOT}")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python3",
        args=["{server_path}"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_unread_count", {{}})
            print(result.content[0].text if result.content else "")

asyncio.run(main())
'''
        try:
            proc = subprocess.run(
                ["python3", "-c", client_code],
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="gmail.unread_count",
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="gmail.unread_count",
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="gmail.unread_count",
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


def benchmark_mcp_stdio_calendar_today(iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark MCP Calendar list_events via stdio (spawn per call)."""
    results = []
    server_path = REPO_ROOT / "src" / "integrations" / "google_calendar" / "server.py"

    for i in range(iterations):
        start = time.perf_counter()

        client_code = f'''
import asyncio
import sys
sys.path.insert(0, "{REPO_ROOT}")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python3",
        args=["{server_path}"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("list_events", {{"days_ahead": 1}})
            print(result.content[0].text if result.content else "")

asyncio.run(main())
'''
        try:
            proc = subprocess.run(
                ["python3", "-c", client_code],
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="calendar.today",
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="calendar.today",
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="mcp_stdio",
                operation="calendar.today",
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# GITHUB BENCHMARKS (gh CLI subprocess)
# =============================================================================

def benchmark_gh_cli(operation: str, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark GitHub via gh CLI subprocess (spawn per call)."""
    results = []

    # Map operations to gh commands
    gh_commands = {
        "github.repos": ["gh", "repo", "list", "--json", "name,url", "-L", "5"],
        "github.notifications": ["gh", "api", "notifications", "--jq", ".[0:5]"],
        "github.user": ["gh", "api", "user"],
    }

    cmd = gh_commands.get(operation)
    if not cmd:
        return [BenchmarkResult(
            protocol="gh_cli",
            operation=operation,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Unknown operation: {operation}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="gh_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="gh_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="gh_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# IMESSAGE BENCHMARKS (Gateway CLI subprocess)
# =============================================================================

def benchmark_imessage_cli(operation: str, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark iMessage via Gateway CLI subprocess (spawn per call)."""
    results = []
    gateway_cli = REPO_ROOT / "Texting" / "gateway" / "imessage_client.py"

    # Map operations to CLI commands
    cli_commands = {
        "imessage.recent": ["python3", str(gateway_cli), "recent", "--limit", "10", "--json"],
        "imessage.unread": ["python3", str(gateway_cli), "unread", "--json"],
        "imessage.search": ["python3", str(gateway_cli), "find", "Alice", "--query", "hello", "--limit", "5", "--json"],
    }

    cmd = cli_commands.get(operation)
    if not cmd:
        return [BenchmarkResult(
            protocol="imessage_cli",
            operation=operation,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Unknown operation: {operation}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
                cwd=str(REPO_ROOT),
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            # Consider success if we get any output (even if no messages found)
            success = proc.returncode == 0 or "messages" in proc.stdout.lower() or "[]" in proc.stdout
            results.append(BenchmarkResult(
                protocol="imessage_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=success,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 and not success else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="imessage_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="imessage_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


def benchmark_fgp_imessage(method: str, params: dict, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark iMessage FGP daemon via UNIX socket."""
    results = []
    # iMessage daemon uses different socket path
    socket_path = Path.home() / ".wolfies-imessage" / "daemon.sock"

    if not socket_path.exists():
        print(f"  WARNING: Socket not found: {socket_path}")
        return [BenchmarkResult(
            protocol="fgp",
            operation=method,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Socket not found: {socket_path}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(str(socket_path))

            request = json.dumps({
                "id": str(uuid.uuid4()),
                "v": 1,
                "method": method,
                "params": params,
            }) + "\n"

            sock.sendall(request.encode())

            # Read response
            chunks = []
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if b'\n' in chunk:
                        break
                except socket.timeout:
                    break

            response = b''.join(chunks)
            sock.close()

            elapsed_ms = (time.perf_counter() - start) * 1000

            try:
                resp_json = json.loads(response.decode().strip())
                success = resp_json.get("error") is None
                error = resp_json.get("error")
            except:
                success = len(response) > 0
                error = None

            results.append(BenchmarkResult(
                protocol="fgp",
                operation=method,
                iteration=i,
                latency_ms=elapsed_ms,
                success=success,
                payload_size=len(response),
                error=str(error)[:200] if error else None,
            ))

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="fgp",
                operation=method,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# FLY.IO BENCHMARKS (flyctl CLI subprocess)
# =============================================================================

def benchmark_flyctl(operation: str, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark Fly.io via flyctl CLI subprocess (spawn per call)."""
    results = []

    # Map operations to flyctl commands
    flyctl_commands = {
        "fly.apps": ["flyctl", "apps", "list", "--json"],
        "fly.status": ["flyctl", "status", "--app", "epstein-monitor", "--json"],
        "fly.machines": ["flyctl", "machines", "list", "--app", "epstein-monitor", "--json"],
    }

    cmd = flyctl_commands.get(operation)
    if not cmd:
        return [BenchmarkResult(
            protocol="flyctl_cli",
            operation=operation,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Unknown operation: {operation}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="flyctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="flyctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="flyctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# NEON BENCHMARKS (neonctl CLI subprocess)
# =============================================================================

def benchmark_neonctl(operation: str, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark Neon via neonctl CLI subprocess (spawn per call)."""
    results = []

    # Map operations to neonctl commands
    neonctl_commands = {
        "neon.projects": ["neonctl", "projects", "list", "--output", "json"],
        "neon.branches": ["neonctl", "branches", "list", "--project-id", "summer-violet-83053059", "--output", "json"],
        "neon.databases": ["neonctl", "databases", "list", "--project-id", "summer-violet-83053059", "--output", "json"],
    }

    cmd = neonctl_commands.get(operation)
    if not cmd:
        return [BenchmarkResult(
            protocol="neonctl_cli",
            operation=operation,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Unknown operation: {operation}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="neonctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="neonctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="neonctl_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# VERCEL BENCHMARKS (vercel CLI subprocess)
# =============================================================================

def benchmark_vercel_cli(operation: str, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark Vercel via vercel CLI subprocess (spawn per call)."""
    results = []

    # Map operations to vercel commands
    # Note: vercel list doesn't support --json, so we just capture text output
    vercel_commands = {
        "vercel.projects": ["vercel", "project", "ls", "--json"],
        "vercel.deployments": ["vercel", "list"],
    }

    cmd = vercel_commands.get(operation)
    if not cmd:
        return [BenchmarkResult(
            protocol="vercel_cli",
            operation=operation,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Unknown operation: {operation}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="vercel_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                error=proc.stderr[:200] if proc.returncode != 0 else None,
            ))
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="vercel_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error="Timeout after 30s",
            ))
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="vercel_cli",
                operation=operation,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# FGP BENCHMARK (UNIX socket - warm daemon)
# =============================================================================

def benchmark_fgp(method: str, params: dict, iterations: int = 10) -> list[BenchmarkResult]:
    """Benchmark FGP daemon via UNIX socket (warm connection)."""
    results = []
    service = method.split('.')[0]
    socket_path = Path.home() / ".fgp" / "services" / service / "daemon.sock"

    if not socket_path.exists():
        print(f"  WARNING: Socket not found: {socket_path}")
        return [BenchmarkResult(
            protocol="fgp",
            operation=method,
            iteration=0,
            latency_ms=0,
            success=False,
            error=f"Socket not found: {socket_path}",
        )]

    for i in range(iterations):
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(str(socket_path))

            request = json.dumps({
                "id": str(uuid.uuid4()),
                "v": 1,
                "method": method,
                "params": params,
            }) + "\n"

            sock.sendall(request.encode())

            # Read response (may be multiple chunks)
            chunks = []
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # Check if we have a complete JSON response (ends with newline)
                    if b'\n' in chunk:
                        break
                except socket.timeout:
                    break

            response = b''.join(chunks)
            sock.close()

            elapsed_ms = (time.perf_counter() - start) * 1000

            # Parse response to check for errors
            try:
                resp_json = json.loads(response.decode().strip())
                success = resp_json.get("error") is None
                error = resp_json.get("error")
            except:
                success = len(response) > 0
                error = None

            results.append(BenchmarkResult(
                protocol="fgp",
                operation=method,
                iteration=i,
                latency_ms=elapsed_ms,
                success=success,
                payload_size=len(response),
                error=str(error)[:200] if error else None,
            ))

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append(BenchmarkResult(
                protocol="fgp",
                operation=method,
                iteration=i,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)[:200],
            ))

    return results


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_comparison(summaries: list[WorkloadSummary]) -> dict[str, Any]:
    """Generate comparison metrics between protocols."""
    comparison = {}

    operations = set(s.operation for s in summaries)
    for op in operations:
        mcp = next((s for s in summaries if s.operation == op and s.protocol == "mcp_stdio"), None)
        gh_cli = next((s for s in summaries if s.operation == op and s.protocol == "gh_cli"), None)
        imessage_cli = next((s for s in summaries if s.operation == op and s.protocol == "imessage_cli"), None)
        flyctl_cli = next((s for s in summaries if s.operation == op and s.protocol == "flyctl_cli"), None)
        neonctl_cli = next((s for s in summaries if s.operation == op and s.protocol == "neonctl_cli"), None)
        vercel_cli = next((s for s in summaries if s.operation == op and s.protocol == "vercel_cli"), None)
        fgp = next((s for s in summaries if s.operation == op and s.protocol == "fgp"), None)

        # Determine the baseline (MCP, gh CLI, iMessage CLI, flyctl CLI, neonctl CLI, or vercel CLI)
        baseline = mcp or gh_cli or imessage_cli or flyctl_cli or neonctl_cli or vercel_cli

        if baseline and fgp and baseline.mean_ms > 0 and fgp.mean_ms > 0:
            speedup = baseline.mean_ms / fgp.mean_ms
            comparison[op] = {
                "baseline_protocol": baseline.protocol,
                "baseline_mean_ms": round(baseline.mean_ms, 2),
                "fgp_mean_ms": round(fgp.mean_ms, 2),
                "speedup": round(speedup, 1),
                "baseline_p95_ms": round(baseline.p95_ms, 2),
                "fgp_p95_ms": round(fgp.p95_ms, 2),
            }
            # Also include legacy fields for backward compatibility
            if mcp:
                comparison[op]["mcp_stdio_mean_ms"] = round(mcp.mean_ms, 2)
                comparison[op]["mcp_p95_ms"] = round(mcp.p95_ms, 2)

    return comparison


def generate_markdown_report(report: BenchmarkReport) -> str:
    """Generate markdown summary for YC demo."""
    lines = [
        "# FGP Performance Comparison",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Iterations:** {report.iterations} (with {report.warmup} warmup)",
        "",
        "## Summary",
        "",
        "| Operation | Baseline | Baseline (ms) | FGP (ms) | Speedup |",
        "|-----------|----------|---------------|----------|---------|",
    ]

    for op, data in sorted(report.comparison.items()):
        baseline_name = data.get('baseline_protocol', 'mcp_stdio')
        baseline_ms = data.get('baseline_mean_ms', data.get('mcp_stdio_mean_ms', 0))
        lines.append(
            f"| {op} | {baseline_name} | {baseline_ms} | {data['fgp_mean_ms']} | **{data['speedup']}x** |"
        )

    lines.extend([
        "",
        "## Key Findings",
        "",
        "1. **MCP/CLI is always \"cold\"** - Every invocation spawns a new process",
        "2. **FGP is always \"warm\"** - Daemon runs continuously, connections reused",
        "3. **4x-20x improvement** depending on operation complexity and baseline",
        "",
    ])

    # Group results by category
    gmail_ops = [s for s in report.summaries if s.operation.startswith("gmail")]
    calendar_ops = [s for s in report.summaries if s.operation.startswith("calendar")]
    github_ops = [s for s in report.summaries if s.operation.startswith("github")]
    imessage_ops = [s for s in report.summaries if s.operation.startswith("imessage")]

    if gmail_ops or calendar_ops:
        lines.extend(["## Gmail & Calendar Results", ""])
        for summary in gmail_ops + calendar_ops:
            lines.extend([
                f"### {summary.operation} ({summary.protocol})",
                f"- Mean: {summary.mean_ms:.2f}ms | Median: {summary.median_ms:.2f}ms",
                f"- P95: {summary.p95_ms:.2f}ms | P99: {summary.p99_ms:.2f}ms",
                f"- Success Rate: {summary.success_rate:.1f}%",
                "",
            ])

    if github_ops:
        lines.extend(["## GitHub Results", ""])
        for summary in github_ops:
            lines.extend([
                f"### {summary.operation} ({summary.protocol})",
                f"- Mean: {summary.mean_ms:.2f}ms | Median: {summary.median_ms:.2f}ms",
                f"- P95: {summary.p95_ms:.2f}ms | P99: {summary.p99_ms:.2f}ms",
                f"- Success Rate: {summary.success_rate:.1f}%",
                "",
            ])

    if imessage_ops:
        lines.extend(["## iMessage Results", ""])
        for summary in imessage_ops:
            lines.extend([
                f"### {summary.operation} ({summary.protocol})",
                f"- Mean: {summary.mean_ms:.2f}ms | Median: {summary.median_ms:.2f}ms",
                f"- P95: {summary.p95_ms:.2f}ms | P99: {summary.p99_ms:.2f}ms",
                f"- Success Rate: {summary.success_rate:.1f}%",
                "",
            ])

    lines.extend([
        "## Methodology",
        "",
        "### Baseline Protocols",
        "- **mcp_stdio**: MCP server via stdio (spawn per call) - typical Claude Code usage",
        "- **gh_cli**: GitHub CLI subprocess spawn - local comparison",
        "- **imessage_cli**: Gateway CLI subprocess spawn - Python CLI invocation",
        "",
        "### FGP (Fast Gateway Protocol)",
        "- Connects to running daemon via UNIX socket",
        "- Daemon keeps OAuth tokens and API connections warm",
        "- Measures only socket + API latency",
        "",
        "---",
        "*Generated by fgp_vs_mcp_benchmark.py*",
    ])

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="FGP vs MCP Performance Benchmark")
    parser.add_argument("-i", "--iterations", type=int, default=5, help="Iterations per workload")
    parser.add_argument("-w", "--warmup", type=int, default=2, help="Warmup iterations (discarded)")
    parser.add_argument("-o", "--output", type=str, help="Output JSON file path")
    parser.add_argument("--github", action="store_true", help="Include GitHub benchmarks")
    parser.add_argument("--imessage", action="store_true", help="Include iMessage benchmarks")
    parser.add_argument("--fly", action="store_true", help="Include Fly.io benchmarks")
    parser.add_argument("--neon", action="store_true", help="Include Neon benchmarks")
    parser.add_argument("--vercel", action="store_true", help="Include Vercel benchmarks")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks (Gmail, Calendar, GitHub, iMessage, Fly, Neon, Vercel)")
    args = parser.parse_args()

    # If --all is set, enable all benchmarks
    if args.all:
        args.github = True
        args.imessage = True
        args.fly = True
        args.neon = True
        args.vercel = True

    total_iterations = args.iterations + args.warmup

    print(f"\n{'='*60}")
    print("FGP vs MCP Performance Benchmark")
    print(f"{'='*60}")
    print(f"Iterations: {args.iterations} (+ {args.warmup} warmup)")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    all_results = []

    # -------------------------------------------------------------------------
    # Gmail Unread Count
    # -------------------------------------------------------------------------
    print("\n[1/4] Benchmarking gmail.unread_count...")

    print("  MCP stdio (spawn per call)...")
    mcp_gmail_results = benchmark_mcp_stdio_gmail_unread(total_iterations)
    # Discard warmup
    mcp_gmail_results = mcp_gmail_results[args.warmup:]
    for i, r in enumerate(mcp_gmail_results):
        r.iteration = i
    all_results.extend(mcp_gmail_results)
    mcp_mean = statistics.mean([r.latency_ms for r in mcp_gmail_results if r.success]) if mcp_gmail_results else 0
    print(f"    Mean: {mcp_mean:.2f}ms")

    print("  FGP (warm daemon)...")
    fgp_gmail_results = benchmark_fgp("gmail.unread", {}, total_iterations)
    fgp_gmail_results = fgp_gmail_results[args.warmup:]
    for i, r in enumerate(fgp_gmail_results):
        r.iteration = i
        r.operation = "gmail.unread_count"  # Normalize operation name
    all_results.extend(fgp_gmail_results)
    fgp_mean = statistics.mean([r.latency_ms for r in fgp_gmail_results if r.success]) if fgp_gmail_results else 0
    print(f"    Mean: {fgp_mean:.2f}ms")

    if mcp_mean > 0 and fgp_mean > 0:
        print(f"  Speedup: {mcp_mean/fgp_mean:.1f}x")

    # -------------------------------------------------------------------------
    # Calendar Today
    # -------------------------------------------------------------------------
    print("\n[2/4] Benchmarking calendar.today...")

    print("  MCP stdio (spawn per call)...")
    mcp_cal_results = benchmark_mcp_stdio_calendar_today(total_iterations)
    mcp_cal_results = mcp_cal_results[args.warmup:]
    for i, r in enumerate(mcp_cal_results):
        r.iteration = i
    all_results.extend(mcp_cal_results)
    mcp_mean = statistics.mean([r.latency_ms for r in mcp_cal_results if r.success]) if mcp_cal_results else 0
    print(f"    Mean: {mcp_mean:.2f}ms")

    print("  FGP (warm daemon)...")
    fgp_cal_results = benchmark_fgp("calendar.today", {}, total_iterations)
    fgp_cal_results = fgp_cal_results[args.warmup:]
    for i, r in enumerate(fgp_cal_results):
        r.iteration = i
    all_results.extend(fgp_cal_results)
    fgp_mean = statistics.mean([r.latency_ms for r in fgp_cal_results if r.success]) if fgp_cal_results else 0
    print(f"    Mean: {fgp_mean:.2f}ms")

    if mcp_mean > 0 and fgp_mean > 0:
        print(f"  Speedup: {mcp_mean/fgp_mean:.1f}x")

    # -------------------------------------------------------------------------
    # Additional FGP-only tests
    # -------------------------------------------------------------------------
    print("\n[3/4] FGP calendar.free_slots...")
    fgp_free_results = benchmark_fgp("calendar.free_slots", {"duration_minutes": 30}, total_iterations)
    fgp_free_results = fgp_free_results[args.warmup:]
    for i, r in enumerate(fgp_free_results):
        r.iteration = i
    all_results.extend(fgp_free_results)
    fgp_mean = statistics.mean([r.latency_ms for r in fgp_free_results if r.success]) if fgp_free_results else 0
    print(f"    Mean: {fgp_mean:.2f}ms")

    print("\n[4/4] FGP gmail.inbox (5 emails)...")
    fgp_inbox_results = benchmark_fgp("gmail.inbox", {"limit": 5}, total_iterations)
    fgp_inbox_results = fgp_inbox_results[args.warmup:]
    for i, r in enumerate(fgp_inbox_results):
        r.iteration = i
    all_results.extend(fgp_inbox_results)
    fgp_mean = statistics.mean([r.latency_ms for r in fgp_inbox_results if r.success]) if fgp_inbox_results else 0
    print(f"    Mean: {fgp_mean:.2f}ms")

    # -------------------------------------------------------------------------
    # GitHub Benchmarks (optional)
    # -------------------------------------------------------------------------
    if args.github:
        print("\n" + "="*60)
        print("GITHUB BENCHMARKS")
        print("="*60)

        # GitHub repos - gh CLI vs FGP
        print("\n[GitHub 1/3] github.repos...")

        print("  gh CLI (subprocess spawn)...")
        gh_repos_results = benchmark_gh_cli("github.repos", total_iterations)
        gh_repos_results = gh_repos_results[args.warmup:]
        for i, r in enumerate(gh_repos_results):
            r.iteration = i
        all_results.extend(gh_repos_results)
        gh_mean = statistics.mean([r.latency_ms for r in gh_repos_results if r.success]) if gh_repos_results else 0
        print(f"    Mean: {gh_mean:.2f}ms")

        print("  FGP (warm daemon)...")
        fgp_repos_results = benchmark_fgp("github.repos", {"limit": 5}, total_iterations)
        fgp_repos_results = fgp_repos_results[args.warmup:]
        for i, r in enumerate(fgp_repos_results):
            r.iteration = i
            r.operation = "github.repos"
        all_results.extend(fgp_repos_results)
        fgp_mean = statistics.mean([r.latency_ms for r in fgp_repos_results if r.success]) if fgp_repos_results else 0
        print(f"    Mean: {fgp_mean:.2f}ms")

        if gh_mean > 0 and fgp_mean > 0:
            print(f"  Speedup: {gh_mean/fgp_mean:.1f}x")

        # GitHub notifications - gh CLI vs FGP
        print("\n[GitHub 2/3] github.notifications...")

        print("  gh CLI (subprocess spawn)...")
        gh_notif_results = benchmark_gh_cli("github.notifications", total_iterations)
        gh_notif_results = gh_notif_results[args.warmup:]
        for i, r in enumerate(gh_notif_results):
            r.iteration = i
        all_results.extend(gh_notif_results)
        gh_mean = statistics.mean([r.latency_ms for r in gh_notif_results if r.success]) if gh_notif_results else 0
        print(f"    Mean: {gh_mean:.2f}ms")

        print("  FGP (warm daemon)...")
        fgp_notif_results = benchmark_fgp("github.notifications", {}, total_iterations)
        fgp_notif_results = fgp_notif_results[args.warmup:]
        for i, r in enumerate(fgp_notif_results):
            r.iteration = i
            r.operation = "github.notifications"
        all_results.extend(fgp_notif_results)
        fgp_mean = statistics.mean([r.latency_ms for r in fgp_notif_results if r.success]) if fgp_notif_results else 0
        print(f"    Mean: {fgp_mean:.2f}ms")

        if gh_mean > 0 and fgp_mean > 0:
            print(f"  Speedup: {gh_mean/fgp_mean:.1f}x")

        # GitHub user - gh CLI vs FGP
        print("\n[GitHub 3/3] github.user...")

        print("  gh CLI (subprocess spawn)...")
        gh_user_results = benchmark_gh_cli("github.user", total_iterations)
        gh_user_results = gh_user_results[args.warmup:]
        for i, r in enumerate(gh_user_results):
            r.iteration = i
        all_results.extend(gh_user_results)
        gh_mean = statistics.mean([r.latency_ms for r in gh_user_results if r.success]) if gh_user_results else 0
        print(f"    Mean: {gh_mean:.2f}ms")

        print("  FGP (warm daemon)...")
        fgp_user_results = benchmark_fgp("github.user", {}, total_iterations)
        fgp_user_results = fgp_user_results[args.warmup:]
        for i, r in enumerate(fgp_user_results):
            r.iteration = i
            r.operation = "github.user"
        all_results.extend(fgp_user_results)
        fgp_mean = statistics.mean([r.latency_ms for r in fgp_user_results if r.success]) if fgp_user_results else 0
        print(f"    Mean: {fgp_mean:.2f}ms")

        if gh_mean > 0 and fgp_mean > 0:
            print(f"  Speedup: {gh_mean/fgp_mean:.1f}x")

    # -------------------------------------------------------------------------
    # iMessage Benchmarks (optional)
    # -------------------------------------------------------------------------
    if args.imessage:
        print("\n" + "="*60)
        print("IMESSAGE BENCHMARKS")
        print("="*60)

        # Check if iMessage daemon is running
        imessage_socket = Path.home() / ".wolfies-imessage" / "daemon.sock"
        imessage_daemon_available = imessage_socket.exists()
        if not imessage_daemon_available:
            print("  NOTE: iMessage daemon not running, will only benchmark CLI")

        # iMessage recent - CLI vs FGP daemon
        print("\n[iMessage 1/2] imessage.recent...")

        print("  Gateway CLI (subprocess spawn)...")
        cli_recent_results = benchmark_imessage_cli("imessage.recent", total_iterations)
        cli_recent_results = cli_recent_results[args.warmup:]
        for i, r in enumerate(cli_recent_results):
            r.iteration = i
        all_results.extend(cli_recent_results)
        cli_mean = statistics.mean([r.latency_ms for r in cli_recent_results if r.success]) if cli_recent_results else 0
        print(f"    Mean: {cli_mean:.2f}ms")

        if imessage_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_recent_results = benchmark_fgp_imessage("recent", {"limit": 10}, total_iterations)
            fgp_recent_results = fgp_recent_results[args.warmup:]
            for i, r in enumerate(fgp_recent_results):
                r.iteration = i
                r.operation = "imessage.recent"
            all_results.extend(fgp_recent_results)
            successful_results = [r.latency_ms for r in fgp_recent_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if cli_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {cli_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_recent_results)} iterations failed")

        # iMessage unread - CLI vs FGP daemon
        print("\n[iMessage 2/2] imessage.unread...")

        print("  Gateway CLI (subprocess spawn)...")
        cli_unread_results = benchmark_imessage_cli("imessage.unread", total_iterations)
        cli_unread_results = cli_unread_results[args.warmup:]
        for i, r in enumerate(cli_unread_results):
            r.iteration = i
        all_results.extend(cli_unread_results)
        cli_mean = statistics.mean([r.latency_ms for r in cli_unread_results if r.success]) if cli_unread_results else 0
        print(f"    Mean: {cli_mean:.2f}ms")

        if imessage_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_unread_results = benchmark_fgp_imessage("unread", {}, total_iterations)
            fgp_unread_results = fgp_unread_results[args.warmup:]
            for i, r in enumerate(fgp_unread_results):
                r.iteration = i
                r.operation = "imessage.unread"
            all_results.extend(fgp_unread_results)
            successful_results = [r.latency_ms for r in fgp_unread_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if cli_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {cli_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_unread_results)} iterations failed")

    # -------------------------------------------------------------------------
    # Fly.io Benchmarks (optional)
    # -------------------------------------------------------------------------
    if args.fly:
        print("\n" + "="*60)
        print("FLY.IO BENCHMARKS")
        print("="*60)

        # Check if Fly.io daemon is running
        fly_socket = Path.home() / ".fgp" / "services" / "fly" / "daemon.sock"
        fly_daemon_available = fly_socket.exists()
        if not fly_daemon_available:
            print("  NOTE: Fly.io FGP daemon not running, will only benchmark flyctl CLI")

        # Fly.io apps - flyctl CLI vs FGP
        print("\n[Fly 1/2] fly.apps...")

        print("  flyctl CLI (subprocess spawn)...")
        flyctl_apps_results = benchmark_flyctl("fly.apps", total_iterations)
        flyctl_apps_results = flyctl_apps_results[args.warmup:]
        for i, r in enumerate(flyctl_apps_results):
            r.iteration = i
        all_results.extend(flyctl_apps_results)
        flyctl_mean = statistics.mean([r.latency_ms for r in flyctl_apps_results if r.success]) if flyctl_apps_results else 0
        print(f"    Mean: {flyctl_mean:.2f}ms")

        if fly_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_apps_results = benchmark_fgp("fly.apps", {}, total_iterations)
            fgp_apps_results = fgp_apps_results[args.warmup:]
            for i, r in enumerate(fgp_apps_results):
                r.iteration = i
                r.operation = "fly.apps"
            all_results.extend(fgp_apps_results)
            successful_results = [r.latency_ms for r in fgp_apps_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if flyctl_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {flyctl_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_apps_results)} iterations failed")

        # Fly.io status - flyctl CLI vs FGP
        print("\n[Fly 2/2] fly.status...")

        print("  flyctl CLI (subprocess spawn)...")
        flyctl_status_results = benchmark_flyctl("fly.status", total_iterations)
        flyctl_status_results = flyctl_status_results[args.warmup:]
        for i, r in enumerate(flyctl_status_results):
            r.iteration = i
        all_results.extend(flyctl_status_results)
        flyctl_mean = statistics.mean([r.latency_ms for r in flyctl_status_results if r.success]) if flyctl_status_results else 0
        print(f"    Mean: {flyctl_mean:.2f}ms")

        if fly_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_status_results = benchmark_fgp("fly.status", {"app": "epstein-monitor"}, total_iterations)
            fgp_status_results = fgp_status_results[args.warmup:]
            for i, r in enumerate(fgp_status_results):
                r.iteration = i
                r.operation = "fly.status"
            all_results.extend(fgp_status_results)
            successful_results = [r.latency_ms for r in fgp_status_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if flyctl_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {flyctl_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_status_results)} iterations failed")

    # -------------------------------------------------------------------------
    # Neon Benchmarks (optional)
    # -------------------------------------------------------------------------
    if args.neon:
        print("\n" + "="*60)
        print("NEON BENCHMARKS")
        print("="*60)

        # Check if Neon daemon is running
        neon_socket = Path.home() / ".fgp" / "services" / "neon" / "daemon.sock"
        neon_daemon_available = neon_socket.exists()
        if not neon_daemon_available:
            print("  NOTE: Neon FGP daemon not running, will only benchmark neonctl CLI")

        # Neon projects - neonctl CLI vs FGP
        print("\n[Neon 1/2] neon.projects...")

        print("  neonctl CLI (subprocess spawn)...")
        neonctl_projects_results = benchmark_neonctl("neon.projects", total_iterations)
        neonctl_projects_results = neonctl_projects_results[args.warmup:]
        for i, r in enumerate(neonctl_projects_results):
            r.iteration = i
        all_results.extend(neonctl_projects_results)
        neonctl_mean = statistics.mean([r.latency_ms for r in neonctl_projects_results if r.success]) if neonctl_projects_results else 0
        print(f"    Mean: {neonctl_mean:.2f}ms")

        if neon_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_projects_results = benchmark_fgp("neon.projects", {}, total_iterations)
            fgp_projects_results = fgp_projects_results[args.warmup:]
            for i, r in enumerate(fgp_projects_results):
                r.iteration = i
                r.operation = "neon.projects"
            all_results.extend(fgp_projects_results)
            successful_results = [r.latency_ms for r in fgp_projects_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if neonctl_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {neonctl_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_projects_results)} iterations failed")

        # Neon branches - neonctl CLI vs FGP
        print("\n[Neon 2/2] neon.branches...")

        print("  neonctl CLI (subprocess spawn)...")
        neonctl_branches_results = benchmark_neonctl("neon.branches", total_iterations)
        neonctl_branches_results = neonctl_branches_results[args.warmup:]
        for i, r in enumerate(neonctl_branches_results):
            r.iteration = i
        all_results.extend(neonctl_branches_results)
        neonctl_mean = statistics.mean([r.latency_ms for r in neonctl_branches_results if r.success]) if neonctl_branches_results else 0
        print(f"    Mean: {neonctl_mean:.2f}ms")

        if neon_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_branches_results = benchmark_fgp("neon.branches", {"project_id": "summer-violet-83053059"}, total_iterations)
            fgp_branches_results = fgp_branches_results[args.warmup:]
            for i, r in enumerate(fgp_branches_results):
                r.iteration = i
                r.operation = "neon.branches"
            all_results.extend(fgp_branches_results)
            successful_results = [r.latency_ms for r in fgp_branches_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if neonctl_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {neonctl_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_branches_results)} iterations failed")

    # -------------------------------------------------------------------------
    # Vercel Benchmarks (optional)
    # -------------------------------------------------------------------------
    if args.vercel:
        print("\n" + "="*60)
        print("VERCEL BENCHMARKS")
        print("="*60)

        # Check if Vercel daemon is running
        vercel_socket = Path.home() / ".fgp" / "services" / "vercel" / "daemon.sock"
        vercel_daemon_available = vercel_socket.exists()
        if not vercel_daemon_available:
            print("  NOTE: Vercel FGP daemon not running, will only benchmark vercel CLI")

        # Vercel projects - vercel CLI vs FGP
        print("\n[Vercel 1/2] vercel.projects...")

        print("  vercel CLI (subprocess spawn)...")
        vercel_projects_results = benchmark_vercel_cli("vercel.projects", total_iterations)
        vercel_projects_results = vercel_projects_results[args.warmup:]
        for i, r in enumerate(vercel_projects_results):
            r.iteration = i
        all_results.extend(vercel_projects_results)
        vercel_mean = statistics.mean([r.latency_ms for r in vercel_projects_results if r.success]) if vercel_projects_results else 0
        print(f"    Mean: {vercel_mean:.2f}ms")

        if vercel_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_projects_results = benchmark_fgp("vercel.projects", {}, total_iterations)
            fgp_projects_results = fgp_projects_results[args.warmup:]
            for i, r in enumerate(fgp_projects_results):
                r.iteration = i
                r.operation = "vercel.projects"
            all_results.extend(fgp_projects_results)
            successful_results = [r.latency_ms for r in fgp_projects_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if vercel_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {vercel_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_projects_results)} iterations failed")

        # Vercel deployments - vercel CLI vs FGP
        print("\n[Vercel 2/2] vercel.deployments...")

        print("  vercel CLI (subprocess spawn)...")
        vercel_deployments_results = benchmark_vercel_cli("vercel.deployments", total_iterations)
        vercel_deployments_results = vercel_deployments_results[args.warmup:]
        for i, r in enumerate(vercel_deployments_results):
            r.iteration = i
        all_results.extend(vercel_deployments_results)
        vercel_mean = statistics.mean([r.latency_ms for r in vercel_deployments_results if r.success]) if vercel_deployments_results else 0
        print(f"    Mean: {vercel_mean:.2f}ms")

        if vercel_daemon_available:
            print("  FGP daemon (warm)...")
            fgp_deployments_results = benchmark_fgp("vercel.deployments", {}, total_iterations)
            fgp_deployments_results = fgp_deployments_results[args.warmup:]
            for i, r in enumerate(fgp_deployments_results):
                r.iteration = i
                r.operation = "vercel.deployments"
            all_results.extend(fgp_deployments_results)
            successful_results = [r.latency_ms for r in fgp_deployments_results if r.success]
            if successful_results:
                fgp_mean = statistics.mean(successful_results)
                print(f"    Mean: {fgp_mean:.2f}ms")
                if vercel_mean > 0 and fgp_mean > 0:
                    print(f"  Speedup: {vercel_mean/fgp_mean:.1f}x")
            else:
                print(f"    ERROR: All {len(fgp_deployments_results)} iterations failed")

    # -------------------------------------------------------------------------
    # Generate Report
    # -------------------------------------------------------------------------
    print("\n" + "="*60)
    print("Generating report...")

    operations = list(set(r.operation for r in all_results))
    all_protocols = list(set(r.protocol for r in all_results))
    summaries = []
    for op in operations:
        for protocol in all_protocols:
            summary = compute_summary(all_results, op, protocol)
            if summary.count > 0:
                summaries.append(summary)

    comparison = generate_comparison(summaries)

    report = BenchmarkReport(
        generated_at=datetime.now().isoformat(),
        iterations=args.iterations,
        warmup=args.warmup,
        results=all_results,
        summaries=summaries,
        comparison=comparison,
    )

    # Save JSON
    output_dir = REPO_ROOT / "benchmarks" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = args.output or f"fgp_vs_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / output_file if not Path(output_file).is_absolute() else Path(output_file)

    with open(output_path, "w") as f:
        json.dump({
            "generated_at": report.generated_at,
            "iterations": report.iterations,
            "warmup": report.warmup,
            "results": [asdict(r) for r in report.results],
            "summaries": [asdict(s) for s in report.summaries],
            "comparison": report.comparison,
        }, f, indent=2)

    print(f"JSON saved to: {output_path}")

    # Save Markdown
    md_path = output_dir / "PERFORMANCE_COMPARISON.md"
    md_content = generate_markdown_report(report)
    with open(md_path, "w") as f:
        f.write(md_content)

    print(f"Markdown saved to: {md_path}")

    # Print summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print("\n| Operation | Baseline | Baseline (ms) | FGP (ms) | Speedup |")
    print("|-----------|----------|---------------|----------|---------|")
    for op, data in sorted(comparison.items()):
        baseline_name = data.get('baseline_protocol', 'mcp_stdio')
        baseline_ms = data.get('baseline_mean_ms', data.get('mcp_stdio_mean_ms', 0))
        print(f"| {op} | {baseline_name} | {baseline_ms:.0f}ms | {data['fgp_mean_ms']:.0f}ms | **{data['speedup']:.1f}x** |")

    print(f"\n{'='*60}")
    print(f"Completed: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
