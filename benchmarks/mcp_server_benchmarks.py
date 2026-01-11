#!/usr/bin/env python3
"""
MCP Server Benchmarks for Gmail, Calendar, and Reminders.

This script measures performance of Life Planner MCP servers to:
1. Create baseline measurements before optimization
2. Profile where time is spent (spawn vs OAuth vs API)
3. Compare before/after optimization results

Usage:
    python3 benchmarks/mcp_server_benchmarks.py -o results/mcp_baseline.json
    python3 benchmarks/mcp_server_benchmarks.py --server gmail -o results/gmail_baseline.json
    python3 benchmarks/mcp_server_benchmarks.py --iterations 10 --warmup 2 -o results/baseline.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import select
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp import types

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, default=str))


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass
class WorkloadSpec:
    workload_id: str
    label: str
    tool: ToolCall
    read_only: bool = True


@dataclass
class McpServerSpec:
    name: str
    command: str
    args: list[str]
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    workloads: list[WorkloadSpec] = field(default_factory=list)


@dataclass
class PhaseResult:
    ok: bool
    ms: float
    error: str | None = None
    stdout_bytes: int | None = None


@dataclass
class CallResult:
    iteration: int
    ok: bool
    ms: float
    error: str | None = None
    payload_bytes: int | None = None
    server_timing: dict[str, float] = field(default_factory=dict)  # [TIMING] markers from stderr


@dataclass
class WorkloadResult:
    workload_id: str
    tool_name: str
    read_only: bool = True
    results: list[CallResult] = field(default_factory=list)
    warmup_results: list[CallResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerRunResult:
    name: str
    command: str
    args: list[str]
    session_initialize: PhaseResult | None = None
    session_list_tools: PhaseResult | None = None
    workloads: list[WorkloadResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _read_jsonrpc_response(
    proc: subprocess.Popen[bytes],
    expected_id: int,
    timeout_s: int,
) -> tuple[dict | None, str | None, int]:
    """Read a JSON-RPC response from the process stdout."""
    if proc.stdout is None:
        return None, "missing stdout", 0

    deadline = time.time() + timeout_s
    bytes_read = 0

    while True:
        if time.time() >= deadline:
            return None, "TIMEOUT", bytes_read
        if proc.poll() is not None:
            return None, f"EXITED({proc.returncode})", bytes_read

        r, _, _ = select.select([proc.stdout], [], [], 0.1)
        if not r:
            continue
        line = proc.stdout.readline()
        if not line:
            continue
        bytes_read += len(line)
        try:
            obj = json.loads(line.decode("utf-8", errors="ignore"))
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("id") == expected_id:
            return obj, None, bytes_read


def _jsonrpc_send(proc: subprocess.Popen[bytes], msg: dict) -> None:
    """Send a JSON-RPC message to the process."""
    if proc.stdin is None:
        raise RuntimeError("missing stdin")
    proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    """Terminate the process gracefully."""
    try:
        if proc.stdin:
            proc.stdin.close()
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _drain_stderr(proc: subprocess.Popen[bytes], max_seconds: float = 0.5) -> dict[str, float]:
    """
    Drain stderr to prevent blocking and extract timing markers.

    Timing markers are in format: [TIMING] phase_name=XX.XXms

    Returns:
        Dictionary of timing markers {phase_name: ms_value}
    """
    timing_markers: dict[str, float] = {}
    timing_pattern = re.compile(r'\[TIMING\]\s+(\w+)=([\d.]+)ms')

    if proc.stderr is None:
        return timing_markers

    start = time.time()
    while time.time() - start < max_seconds:
        r, _, _ = select.select([proc.stderr], [], [], 0.05)
        if not r:
            continue
        line = proc.stderr.readline()
        if not line:
            break

        # Try to parse timing marker
        try:
            decoded = line.decode("utf-8", errors="ignore")
            match = timing_pattern.search(decoded)
            if match:
                phase_name = match.group(1)
                ms_value = float(match.group(2))
                timing_markers[phase_name] = ms_value
        except Exception:
            pass

    return timing_markers


def _call_tool(
    proc: subprocess.Popen[bytes],
    *,
    request_id: int,
    tool_name: str,
    tool_args: dict[str, Any],
    timeout_s: int,
) -> tuple[dict | None, CallResult]:
    """Call an MCP tool and measure timing."""
    t0 = time.perf_counter()
    _jsonrpc_send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": tool_args or {}},
        },
    )
    resp, err, bytes_read = _read_jsonrpc_response(proc, expected_id=request_id, timeout_s=timeout_s)
    call_ms = (time.perf_counter() - t0) * 1000

    # Drain stderr and capture timing markers
    server_timing = _drain_stderr(proc, max_seconds=0.1)

    call_ok = err is None and resp is not None and "error" not in resp

    # Estimate payload size
    payload_bytes = None
    if resp:
        result = resp.get("result")
        if result:
            payload_bytes = len(json.dumps(result).encode("utf-8"))

    return (
        resp,
        CallResult(
            iteration=request_id,
            ok=call_ok,
            ms=call_ms,
            error=err or ((resp or {}).get("error") or {}).get("message"),
            payload_bytes=payload_bytes,
            server_timing=server_timing,
        ),
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _std_dev(values: list[float]) -> float | None:
    """Calculate standard deviation."""
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _cv(values: list[float]) -> float | None:
    """Calculate coefficient of variation (std_dev / mean * 100)."""
    if not values:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    std = _std_dev(values)
    if std is None:
        return None
    return (std / mean) * 100


def _percentile(values: list[float], p: float) -> float | None:
    """Calculate percentile (0-100)."""
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = int((p / 100) * (len(sorted_vals) - 1))
    return sorted_vals[idx]


def _p50(values: list[float]) -> float | None:
    return _percentile(values, 50)


def _p90(values: list[float]) -> float | None:
    return _percentile(values, 90)


def _p95(values: list[float]) -> float | None:
    return _percentile(values, 95)


def _p99(values: list[float]) -> float | None:
    return _percentile(values, 99)


def _summarize_calls(calls: list[CallResult]) -> dict:
    """Calculate summary statistics for a list of calls."""
    ok_calls = [c for c in calls if c.ok]
    ms_vals = [c.ms for c in ok_calls]
    payload_vals = [c.payload_bytes for c in ok_calls if c.payload_bytes]

    # Aggregate server timing markers
    timing_aggregates: dict[str, list[float]] = {}
    for call in ok_calls:
        for phase, ms in call.server_timing.items():
            if phase not in timing_aggregates:
                timing_aggregates[phase] = []
            timing_aggregates[phase].append(ms)

    server_timing_summary: dict[str, dict[str, float | None]] = {}
    for phase, values in timing_aggregates.items():
        server_timing_summary[phase] = {
            "mean_ms": _mean(values),
            "p50_ms": _p50(values),
            "min_ms": min(values) if values else None,
            "max_ms": max(values) if values else None,
        }

    result = {
        "total": len(calls),
        "ok": len(ok_calls),
        "failed": len(calls) - len(ok_calls),
        "mean_ms": _mean(ms_vals),
        "p50_ms": _p50(ms_vals),
        "p90_ms": _p90(ms_vals),
        "p95_ms": _p95(ms_vals),
        "p99_ms": _p99(ms_vals),
        "min_ms": min(ms_vals) if ms_vals else None,
        "max_ms": max(ms_vals) if ms_vals else None,
        "std_dev_ms": _std_dev(ms_vals),
        "cv_percent": _cv(ms_vals),
        "mean_payload_bytes": _mean([float(v) for v in payload_vals]) if payload_vals else None,
    }

    if server_timing_summary:
        result["server_timing"] = server_timing_summary

    return result


def _run_server_benchmark(
    spec: McpServerSpec,
    *,
    iterations: int,
    warmup: int,
    phase_timeout_s: int,
    call_timeout_s: int,
    protocol_versions: list[str],
) -> ServerRunResult:
    """Run benchmarks for a single MCP server."""

    print(f"\n{'='*60}")
    print(f"Server: {spec.name}")
    print(f"Command: {spec.command} {' '.join(spec.args)}")
    print(f"{'='*60}")

    # Spawn the server process
    spawn_t0 = time.perf_counter()
    proc = subprocess.Popen(
        [spec.command, *spec.args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=spec.cwd or str(REPO_ROOT),
        env={**os.environ, **(spec.env or {})},
    )

    server_result = ServerRunResult(
        name=spec.name,
        command=spec.command,
        args=spec.args,
    )

    try:
        _ = _drain_stderr(proc, max_seconds=1.0)  # Discard timing during warmup

        # Initialize MCP session
        init_ok = False
        init_err: str | None = None
        init_stdout_bytes: int | None = None

        for pv in protocol_versions:
            _jsonrpc_send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": pv,
                        "capabilities": {},
                        "clientInfo": {"name": "bench", "version": "0.1"},
                    },
                },
            )
            resp, err, bytes_read = _read_jsonrpc_response(proc, expected_id=1, timeout_s=phase_timeout_s)
            init_stdout_bytes = bytes_read
            if err:
                init_err = err
                continue
            if resp and "error" in resp:
                init_err = (resp.get("error") or {}).get("message") or "initialize error"
                continue
            init_ok = True
            init_err = None
            break

        init_ms = (time.perf_counter() - spawn_t0) * 1000
        server_result.session_initialize = PhaseResult(
            ok=init_ok,
            ms=init_ms,
            error=init_err,
            stdout_bytes=init_stdout_bytes,
        )

        print(f"[{_ts()}] Initialize: {'OK' if init_ok else 'FAIL'} {init_ms:.1f}ms")

        if not init_ok:
            server_result.notes.append(f"Initialize failed: {init_err}")
            return server_result

        # Send initialized notification
        _jsonrpc_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # List tools
        t1 = time.perf_counter()
        _jsonrpc_send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp, tools_err, tools_bytes = _read_jsonrpc_response(proc, expected_id=2, timeout_s=phase_timeout_s)
        tools_ms = (time.perf_counter() - t1) * 1000
        tools_ok = tools_err is None and tools_resp is not None and "error" not in tools_resp

        server_result.session_list_tools = PhaseResult(
            ok=tools_ok,
            ms=tools_ms,
            error=tools_err or ((tools_resp or {}).get("error") or {}).get("message"),
            stdout_bytes=tools_bytes,
        )

        print(f"[{_ts()}] List tools: {'OK' if tools_ok else 'FAIL'} {tools_ms:.1f}ms")

        if not tools_ok or tools_resp is None:
            server_result.notes.append(f"List tools failed: {tools_err}")
            return server_result

        # Get available tool names
        tool_list = (tools_resp.get("result") or {}).get("tools") or []
        available_tools = {str(t.get("name") or "") for t in tool_list if isinstance(t, dict)}
        print(f"[{_ts()}] Available tools: {', '.join(sorted(available_tools))}")

        # Run workloads
        next_id = 1000
        for workload in spec.workloads:
            w_result = WorkloadResult(
                workload_id=workload.workload_id,
                tool_name=workload.tool.name,
                read_only=workload.read_only,
            )

            if workload.tool.name not in available_tools:
                print(f"[{_ts()}] {workload.workload_id}: SKIPPED (tool not found: {workload.tool.name})")
                server_result.workloads.append(w_result)
                continue

            print(f"\n[{_ts()}] Running {workload.workload_id}: {workload.label}")

            # Warmup calls
            for i in range(warmup):
                next_id += 1
                _, call = _call_tool(
                    proc,
                    request_id=next_id,
                    tool_name=workload.tool.name,
                    tool_args=workload.tool.args,
                    timeout_s=call_timeout_s,
                )
                w_result.warmup_results.append(call)
                print(f"[{_ts()}]   warmup {i+1}/{warmup}: {'OK' if call.ok else 'FAIL'} {call.ms:.1f}ms")

            # Measured calls
            for i in range(iterations):
                next_id += 1
                _, call = _call_tool(
                    proc,
                    request_id=next_id,
                    tool_name=workload.tool.name,
                    tool_args=workload.tool.args,
                    timeout_s=call_timeout_s,
                )
                call.iteration = i + 1
                w_result.results.append(call)

                # Format timing marker output
                timing_str = ""
                if call.server_timing:
                    timing_parts = [f"{k}={v:.1f}" for k, v in call.server_timing.items()]
                    timing_str = f" [{', '.join(timing_parts)}]"

                print(
                    f"[{_ts()}]   iter {i+1}/{iterations}: {'OK' if call.ok else 'FAIL'} {call.ms:.1f}ms"
                    f"{f' payload={call.payload_bytes}b' if call.payload_bytes else ''}"
                    f"{timing_str}"
                )

            w_result.summary = _summarize_calls(w_result.results)
            server_result.workloads.append(w_result)

            print(f"[{_ts()}] {workload.workload_id} summary: mean={w_result.summary['mean_ms']:.1f}ms p95={w_result.summary['p95_ms']:.1f}ms")

        return server_result

    finally:
        _terminate(proc)


def _get_server_specs() -> list[McpServerSpec]:
    """Define MCP server specs and their workloads (expanded for Phase 2 profiling)."""

    # Get date strings for calendar queries
    today = datetime.now()
    week_ago = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    month_ago = (today - timedelta(days=30)).strftime("%Y/%m/%d")

    return [
        # Gmail MCP Server - 8 workloads
        McpServerSpec(
            name="Gmail MCP",
            command="python3",
            args=[str(REPO_ROOT / "src" / "integrations" / "gmail" / "server.py")],
            cwd=str(REPO_ROOT),
            workloads=[
                # Baseline API call
                WorkloadSpec(
                    workload_id="GMAIL_UNREAD_COUNT",
                    label="Get unread email count",
                    tool=ToolCall("get_unread_count", {}),
                ),
                # N+1 scaling tests (5, 10, 25 emails)
                WorkloadSpec(
                    workload_id="GMAIL_LIST_5",
                    label="List 5 recent emails",
                    tool=ToolCall("list_emails", {"max_results": 5}),
                ),
                WorkloadSpec(
                    workload_id="GMAIL_LIST_10",
                    label="List 10 recent emails",
                    tool=ToolCall("list_emails", {"max_results": 10}),
                ),
                WorkloadSpec(
                    workload_id="GMAIL_LIST_25",
                    label="List 25 recent emails",
                    tool=ToolCall("list_emails", {"max_results": 25}),
                ),
                # Search tests
                WorkloadSpec(
                    workload_id="GMAIL_SEARCH_SIMPLE",
                    label="Search emails (simple)",
                    tool=ToolCall("search_emails", {"query": "from:me", "max_results": 5}),
                ),
                WorkloadSpec(
                    workload_id="GMAIL_SEARCH_COMPLEX",
                    label="Search emails (with date)",
                    tool=ToolCall("search_emails", {"query": f"after:{week_ago}", "max_results": 5}),
                ),
                # Single fetch - requires a message ID, skip if not available
                # WorkloadSpec(
                #     workload_id="GMAIL_GET_SINGLE",
                #     label="Get single email by ID",
                #     tool=ToolCall("get_email", {"message_id": "PLACEHOLDER"}),
                # ),
                # Filtered list
                WorkloadSpec(
                    workload_id="GMAIL_LIST_UNREAD",
                    label="List unread emails (5)",
                    tool=ToolCall("list_emails", {"max_results": 5, "unread_only": True}),
                ),
            ],
        ),
        # Google Calendar MCP Server - 6 workloads
        McpServerSpec(
            name="Calendar MCP",
            command="python3",
            args=[str(REPO_ROOT / "src" / "integrations" / "google_calendar" / "server.py")],
            cwd=str(REPO_ROOT),
            workloads=[
                # Time range tests
                WorkloadSpec(
                    workload_id="CALENDAR_LIST_TODAY",
                    label="List today's events",
                    tool=ToolCall("list_events", {"days_ahead": 1, "max_results": 20}),
                ),
                WorkloadSpec(
                    workload_id="CALENDAR_LIST_WEEK",
                    label="List week's events",
                    tool=ToolCall("list_events", {"days_ahead": 7, "max_results": 50}),
                ),
                WorkloadSpec(
                    workload_id="CALENDAR_LIST_MONTH",
                    label="List month's events",
                    tool=ToolCall("list_events", {"days_ahead": 30, "max_results": 100}),
                ),
                # Free time tests
                WorkloadSpec(
                    workload_id="CALENDAR_FREE_30MIN",
                    label="Find 30-min free slots",
                    tool=ToolCall("find_free_time", {"duration_minutes": 30, "days_ahead": 7, "max_slots": 10}),
                ),
                WorkloadSpec(
                    workload_id="CALENDAR_FREE_60MIN",
                    label="Find 60-min free slots",
                    tool=ToolCall("find_free_time", {"duration_minutes": 60, "days_ahead": 7, "max_slots": 5}),
                ),
                WorkloadSpec(
                    workload_id="CALENDAR_FREE_2HOUR",
                    label="Find 2-hour free slots",
                    tool=ToolCall("find_free_time", {"duration_minutes": 120, "days_ahead": 14, "max_slots": 3}),
                ),
            ],
        ),
        # Reminders MCP Server - 5 workloads
        McpServerSpec(
            name="Reminders MCP",
            command="python3",
            args=[str(REPO_ROOT / "Reminders" / "mcp_server" / "server.py")],
            cwd=str(REPO_ROOT / "Reminders"),
            workloads=[
                # Cached/fast operation
                WorkloadSpec(
                    workload_id="REMINDERS_LIST_LISTS",
                    label="List reminder lists",
                    tool=ToolCall("list_reminder_lists", {}),
                ),
                # Default list - various limits
                WorkloadSpec(
                    workload_id="REMINDERS_LIST_10",
                    label="List reminders (10)",
                    tool=ToolCall("list_reminders", {"limit": 10}),
                ),
                WorkloadSpec(
                    workload_id="REMINDERS_LIST_50",
                    label="List reminders (50)",
                    tool=ToolCall("list_reminders", {"limit": 50}),
                ),
                # Completed reminders
                WorkloadSpec(
                    workload_id="REMINDERS_LIST_COMPLETED",
                    label="List completed reminders",
                    tool=ToolCall("list_reminders", {"limit": 20, "completed": True}),
                ),
                # With tag filter (if available)
                WorkloadSpec(
                    workload_id="REMINDERS_LIST_TAGGED",
                    label="List reminders with tag",
                    tool=ToolCall("list_reminders", {"limit": 20, "tag_filter": "work"}),
                ),
            ],
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark MCP servers for Gmail, Calendar, and Reminders")
    parser.add_argument("--iterations", "-n", type=int, default=10, help="Number of measured iterations per workload (default: 10)")
    parser.add_argument("--warmup", "-w", type=int, default=2, help="Number of warmup iterations (default: 2)")
    parser.add_argument("--phase-timeout", type=int, default=30, help="Timeout for init/list phases (seconds)")
    parser.add_argument("--call-timeout", type=int, default=60, help="Timeout for tool calls (seconds)")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file path")
    parser.add_argument("--server", "-s", choices=["gmail", "calendar", "reminders"], help="Run only specified server")
    args = parser.parse_args()

    protocol_versions = ["2024-11-05", types.LATEST_PROTOCOL_VERSION]

    # Get server specs
    all_servers = _get_server_specs()

    # Filter if --server specified
    if args.server:
        name_map = {"gmail": "Gmail MCP", "calendar": "Calendar MCP", "reminders": "Reminders MCP"}
        target_name = name_map[args.server]
        all_servers = [s for s in all_servers if s.name == target_name]

    out_path = Path(args.output)

    # Prepare payload
    payload: dict = {
        "generated_at": _ts(),
        "metadata": {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "phase_timeout_s": args.phase_timeout,
            "call_timeout_s": args.call_timeout,
        },
        "servers": [],
    }

    print(f"\n{'#'*60}")
    print("MCP Server Benchmarks")
    print(f"Iterations: {args.iterations}, Warmup: {args.warmup}")
    print(f"Output: {out_path}")
    print(f"{'#'*60}")

    # Run benchmarks
    for spec in all_servers:
        try:
            result = _run_server_benchmark(
                spec,
                iterations=args.iterations,
                warmup=args.warmup,
                phase_timeout_s=args.phase_timeout,
                call_timeout_s=args.call_timeout,
                protocol_versions=protocol_versions,
            )
            payload["servers"].append(asdict(result))
        except Exception as e:
            print(f"[{_ts()}] ERROR: {spec.name} failed with exception: {e}")
            payload["servers"].append({
                "name": spec.name,
                "error": str(e),
            })

        # Save checkpoint after each server
        _write_json(out_path, payload)

    # Print summary
    print(f"\n{'='*80}")
    print("                        MCP SERVER BENCHMARK SUMMARY")
    print(f"{'='*80}")

    for server in payload["servers"]:
        name = server.get("name", "Unknown")
        init = server.get("session_initialize") or {}
        error = server.get("error")

        print(f"\n┌{'─'*78}┐")
        print(f"│ {name:<76} │")
        print(f"├{'─'*78}┤")

        if error:
            print(f"│ {'ERROR: ' + error[:70]:<76} │")
            print(f"└{'─'*78}┘")
            continue

        init_status = "OK" if init.get("ok") else "FAIL"
        init_ms = init.get("ms", 0)
        print(f"│ Initialize: {init_status} {init_ms:>8.1f}ms{' '*51}│")
        print(f"├{'─'*78}┤")
        print(f"│ {'Workload':<28} │ {'Mean':>8} │ {'P50':>8} │ {'P95':>8} │ {'StdDev':>8} │ {'OK':>4} │")
        print(f"├{'─'*78}┤")

        for workload in server.get("workloads") or []:
            summary = workload.get("summary") or {}
            wid = workload.get("workload_id", "")
            mean = summary.get("mean_ms") or 0
            p50 = summary.get("p50_ms") or 0
            p95 = summary.get("p95_ms") or 0
            std = summary.get("std_dev_ms") or 0
            ok = summary.get("ok", 0)
            total = summary.get("total", 0)

            # Truncate workload ID if too long
            wid_display = wid[:28] if len(wid) <= 28 else wid[:25] + "..."

            print(f"│ {wid_display:<28} │ {mean:>7.1f}ms │ {p50:>7.1f}ms │ {p95:>7.1f}ms │ {std:>7.1f}ms │ {ok:>2}/{total:<1} │")

            # Print server timing breakdown if available
            server_timing = summary.get("server_timing")
            if server_timing:
                for phase, phase_data in server_timing.items():
                    phase_mean = phase_data.get("mean_ms") or 0
                    phase_display = f"  └─ {phase}"[:28]
                    print(f"│ {phase_display:<28} │ {phase_mean:>7.1f}ms │ {' '*8} │ {' '*8} │ {' '*8} │ {' '*4} │")

        print(f"└{'─'*78}┘")

    # Print analysis/findings
    print(f"\n{'='*80}")
    print("                              KEY OBSERVATIONS")
    print(f"{'='*80}")

    for server in payload["servers"]:
        name = server.get("name", "Unknown")
        init = server.get("session_initialize") or {}
        workloads = server.get("workloads") or []

        if server.get("error"):
            continue

        print(f"\n{name}:")
        init_ms = init.get("ms", 0)
        if init_ms > 1000:
            print(f"  ⚠️  Init time {init_ms:.0f}ms - daemon pattern would eliminate this")

        # Find slowest and fastest workload
        if workloads:
            sorted_workloads = sorted(
                [w for w in workloads if w.get("summary", {}).get("mean_ms")],
                key=lambda w: w.get("summary", {}).get("mean_ms", 0),
            )
            if len(sorted_workloads) >= 2:
                fastest = sorted_workloads[0]
                slowest = sorted_workloads[-1]
                print(f"  🚀 Fastest: {fastest['workload_id']} ({fastest['summary']['mean_ms']:.1f}ms)")
                print(f"  🐢 Slowest: {slowest['workload_id']} ({slowest['summary']['mean_ms']:.1f}ms)")

                # Check for N+1 scaling pattern (Gmail)
                if "GMAIL_LIST" in slowest["workload_id"]:
                    print(f"  ⚠️  Slow list operation - likely N+1 API pattern")

    print(f"\n{'='*80}")
    print(f"Results saved to: {out_path}")
    print(f"{'='*80}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
