#!/usr/bin/env python3
"""
Benchmark suite for iMessage CLI Gateway performance testing.

Tests:
1. Command execution time (cold start)
2. Database query performance across different operations
3. Contact resolution speed
4. JSON output overhead
5. Comparison with MCP server startup

Usage:
    python3 gateway/benchmarks.py                    # Run all benchmarks
    python3 gateway/benchmarks.py --quick           # Run quick benchmarks only
    python3 gateway/benchmarks.py --json            # Output results as JSON
    python3 gateway/benchmarks.py --compare-mcp     # Include MCP server comparison
"""

import sys
import time
import json
import subprocess
import statistics
import sqlite3
import tempfile
import socket
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import argparse
import math

# Project paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

CLI_PATH = SCRIPT_DIR / "imessage_client.py"
DAEMON_PATH = SCRIPT_DIR / "imessage_daemon.py"
DAEMON_CLIENT_PATH = SCRIPT_DIR / "imessage_daemon_client.py"
DAEMON_CLIENT_FAST_PATH = SCRIPT_DIR / "daemon_client_fast.sh"
RUST_DAEMON_CLIENT_PATH = SCRIPT_DIR / "wolfies-daemon-client"
BYTES_PER_TOKEN_ESTIMATE = 4.0


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    description: str
    iterations: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    success_rate: float
    stdout_bytes_mean: Optional[float] = None
    approx_tokens_mean: Optional[float] = None
    server_ms_mean: Optional[float] = None
    server_ms_median: Optional[float] = None
    server_ms_p95: Optional[float] = None
    server_ms_min: Optional[float] = None
    server_ms_max: Optional[float] = None
    server_sqlite_ms_mean: Optional[float] = None
    server_build_ms_mean: Optional[float] = None
    server_resolve_ms_mean: Optional[float] = None
    server_serialize_ms_mean: Optional[float] = None
    inproc_ms_mean: Optional[float] = None
    inproc_ms_median: Optional[float] = None
    inproc_ms_p95: Optional[float] = None
    inproc_ms_min: Optional[float] = None
    inproc_ms_max: Optional[float] = None
    spawn_overhead_ms_mean: Optional[float] = None
    result_count_mean: Optional[float] = None


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    suite_name: str
    timestamp: str
    results: List[BenchmarkResult]
    metadata: Dict[str, Any]


def run_cli_command(cmd: List[str], timeout: int = 30) -> tuple[float, bool, str]:
    """
    Run a CLI command and measure execution time.

    Returns:
        (execution_time_ms, success, output)
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", str(CLI_PATH)] + cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT)
        )
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return elapsed, success, output
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, "TIMEOUT"
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, str(e)


def run_external_command(cmd: List[str], timeout: int = 30) -> tuple[float, bool, str]:
    """
    Run an arbitrary command and measure execution time.

    This is used for daemon benchmarks where the executable is not CLI_PATH.

    Returns:
        (execution_time_ms, success, output)
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
        elapsed = (time.perf_counter() - start) * 1000
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return elapsed, success, output
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, "TIMEOUT"
    except Exception as e:  # pragma: no cover - defensive
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, str(e)


def _percentile(sorted_values: List[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def benchmark_command(
    name: str,
    description: str,
    cmd: List[str],
    iterations: int = 10
) -> BenchmarkResult:
    """
    Benchmark a CLI command over multiple iterations.

    Args:
        name: Benchmark name
        description: What's being tested
        cmd: Command arguments (without python3 gateway/imessage_client.py)
        iterations: Number of times to run the command

    Returns:
        BenchmarkResult with timing statistics
    """
    print(f"Running: {name} ({iterations} iterations)...", end=" ", flush=True)

    timings = []
    successes = 0
    stdout_sizes: List[int] = []

    for _ in range(iterations):
        elapsed, success, output = run_cli_command(cmd)
        timings.append(elapsed)
        if success:
            successes += 1
            # Capture output size in bytes (tool-runner + LLM-facing cost proxy).
            # run_cli_command already captured stdout as text; estimate bytes via utf-8.
            stdout_sizes.append(len((output or "").encode("utf-8", errors="ignore")))

    success_rate = (successes / iterations) * 100

    p95_ms = _percentile(sorted(timings), 95.0) or 0.0
    stdout_bytes_mean = statistics.mean(stdout_sizes) if stdout_sizes else None
    approx_tokens_mean = math.ceil(stdout_bytes_mean / BYTES_PER_TOKEN_ESTIMATE) if stdout_bytes_mean is not None else None

    result = BenchmarkResult(
        name=name,
        description=description,
        iterations=iterations,
        mean_ms=statistics.mean(timings),
        median_ms=statistics.median(timings),
        p95_ms=p95_ms,
        min_ms=min(timings),
        max_ms=max(timings),
        std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
        success_rate=success_rate,
        stdout_bytes_mean=stdout_bytes_mean,
        approx_tokens_mean=approx_tokens_mean,
    )

    print(f"✓ (mean: {result.mean_ms:.2f}ms, success: {success_rate:.0f}%)")
    return result


def _daemon_probe_health(socket_path: Path, timeout_s: float = 0.2) -> bool:
    """
    Lightweight health probe without spawning a client process.

    This measures daemon readiness more directly than shelling out to a client.
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))
            s.sendall(b'{"id":"bench","v":1,"method":"health","params":{}}\n')
            buf = s.recv(4096)
        if not buf:
            return False
        line = buf.split(b"\n", 1)[0]
        resp = json.loads(line.decode("utf-8"))
        return bool(resp.get("ok"))
    except Exception:
        return False


def _daemon_request(socket_path: Path, request: dict[str, Any], timeout_s: float = 0.5) -> dict[str, Any] | None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            s.connect(str(socket_path))
            payload = (json.dumps(request, separators=(",", ":"), default=str) + "\n").encode("utf-8")
            s.sendall(payload)
            buf = bytearray()
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"\n" in chunk:
                    break
        line = bytes(buf).split(b"\n", 1)[0]
        if not line:
            return None
        return json.loads(line.decode("utf-8"))
    except Exception:
        return None


def _extract_daemon_result_count(payload: dict[str, Any], method: str) -> int | None:
    try:
        if "ok" in payload and payload.get("ok") is False:
            return None
        result = payload.get("result", payload)
        if method == "unread_count":
            count = result.get("count")
            return int(count) if isinstance(count, (int, float)) else None
        if method in {"unread_messages", "recent"}:
            messages = result.get("messages")
            return len(messages) if isinstance(messages, list) else None
        if method == "text_search":
            results = result.get("results")
            return len(results) if isinstance(results, list) else None
        if method == "bundle":
            total = 0
            total += len(result.get("unread", {}).get("messages", []))
            total += len(result.get("recent", []))
            total += len(result.get("search", {}).get("results", []))
            total += len(result.get("contact_messages", {}).get("messages", []))
            return total
    except Exception:
        return None
    return None


def _start_daemon_for_bench(*, socket_path: Path, pidfile_path: Path, timeout_s: float = 5.0) -> float:
    """
    Start the daemon and block until it's ready.

    Returns:
        time_to_ready_ms
    """
    start = time.perf_counter()
    proc = subprocess.run(
        [
            "python3",
            str(DAEMON_PATH),
            "--socket",
            str(socket_path),
            "--pidfile",
            str(pidfile_path),
            "start",
        ],
        capture_output=True,
        text=True,
        timeout=max(2.0, timeout_s),
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "failed to start daemon").strip())

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if socket_path.exists() and _daemon_probe_health(socket_path):
            return (time.perf_counter() - start) * 1000
        time.sleep(0.02)
    raise TimeoutError("daemon did not become ready in time")


def _stop_daemon_for_bench(*, socket_path: Path, pidfile_path: Path) -> None:
    subprocess.run(
        [
            "python3",
            str(DAEMON_PATH),
            "--socket",
            str(socket_path),
            "--pidfile",
            str(pidfile_path),
            "stop",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        cwd=str(REPO_ROOT),
    )


def run_cli_command_quiet(cmd: List[str], timeout: int = 30) -> tuple[float, bool]:
    """
    Run a CLI command and measure execution time, discarding stdout/stderr.

    This avoids Python-side overhead of capturing potentially large outputs into memory.
    """
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", str(CLI_PATH)] + cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT)
        )
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, result.returncode == 0
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False


def benchmark_command_quiet(
    name: str,
    description: str,
    cmd: List[str],
    iterations: int = 10,
    timeout: int = 30
) -> BenchmarkResult:
    """Benchmark a CLI command over multiple iterations with output discarded."""
    print(f"Running: {name} ({iterations} iterations)...", end=" ", flush=True)

    timings: List[float] = []
    successes = 0

    for _ in range(iterations):
        elapsed, ok = run_cli_command_quiet(cmd, timeout=timeout)
        timings.append(elapsed)
        if ok:
            successes += 1

    success_rate = (successes / iterations) * 100

    result = BenchmarkResult(
        name=name,
        description=description,
        iterations=iterations,
        mean_ms=statistics.mean(timings),
        median_ms=statistics.median(timings),
        p95_ms=_percentile(sorted(timings), 95.0) or 0.0,
        min_ms=min(timings),
        max_ms=max(timings),
        std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
        success_rate=success_rate
    )

    print(f"✓ (mean: {result.mean_ms:.2f}ms, success: {success_rate:.0f}%)")
    return result


def _get_sample_contact_name() -> str | None:
    """Pick a sample contact name for argumented benchmarks."""
    _, success, output = run_cli_command(["contacts", "--json"])
    if not success:
        return None
    try:
        contacts = json.loads(output)
    except Exception:
        return None
    if not contacts:
        return None
    return contacts[0].get("name")


def _get_sample_group_id() -> str | None:
    """Pick a sample group identifier for group-related benchmarks."""
    _, success, output = run_cli_command(["groups", "--json"])
    if not success:
        return None
    try:
        groups = json.loads(output)
    except Exception:
        return None
    if not groups:
        return None
    first = groups[0]
    return first.get("group_id") or first.get("chat_id") or first.get("id")


def _get_sample_message_guid() -> str | None:
    """Retrieve a message GUID directly from chat.db for thread benchmarking."""
    try:
        db_path = Path("~/Library/Messages/chat.db").expanduser()
        if not db_path.exists():
            return None
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT guid FROM message WHERE guid IS NOT NULL ORDER BY date DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def benchmark_startup_overhead(iterations: int = 20) -> BenchmarkResult:
    """Test CLI startup overhead with minimal command."""
    return benchmark_command(
        name="startup_overhead",
        description="CLI startup time with --help",
        cmd=["--help"],
        iterations=iterations
    )


def benchmark_contacts_list(iterations: int = 10) -> BenchmarkResult:
    """Test listing all contacts."""
    return benchmark_command(
        name="contacts_list",
        description="List all contacts (no JSON)",
        cmd=["contacts"],
        iterations=iterations
    )


def benchmark_contacts_list_json(iterations: int = 10) -> BenchmarkResult:
    """Test listing contacts with JSON output."""
    return benchmark_command(
        name="contacts_list_json",
        description="List all contacts with JSON serialization",
        cmd=["contacts", "--json"],
        iterations=iterations
    )


def benchmark_unread_messages(iterations: int = 10) -> BenchmarkResult:
    """Test fetching unread messages."""
    return benchmark_command(
        name="unread_messages",
        description="Fetch unread messages",
        cmd=["unread"],
        iterations=iterations
    )


def benchmark_recent_conversations(iterations: int = 10, limit: int = 10) -> BenchmarkResult:
    """Test fetching recent conversations."""
    return benchmark_command(
        name=f"recent_conversations_{limit}",
        description=f"Fetch {limit} recent conversations",
        cmd=["recent", "--limit", str(limit)],
        iterations=iterations
    )


def benchmark_search_small(iterations: int = 10) -> BenchmarkResult:
    """Test searching messages with small result set."""
    return benchmark_command(
        name="search_small",
        description="Search recent messages (limit 10, contact-agnostic)",
        cmd=["recent", "--limit", "10"],
        iterations=iterations
    )


def benchmark_search_medium(iterations: int = 10) -> BenchmarkResult:
    """Test searching messages with medium result set."""
    return benchmark_command(
        name="search_medium",
        description="Search recent messages (limit 50, contact-agnostic)",
        cmd=["recent", "--limit", "50"],
        iterations=iterations
    )


def benchmark_search_large(iterations: int = 5) -> BenchmarkResult:
    """Test searching messages with large result set."""
    return benchmark_command(
        name="search_large",
        description="Search recent messages (limit 200, contact-agnostic)",
        cmd=["recent", "--limit", "200"],
        iterations=iterations
    )

def benchmark_bundle(iterations: int = 10) -> BenchmarkResult:
    """Benchmark the canonical bundle workload (single-call LLM read path)."""
    return benchmark_command(
        name="bundle_compact",
        description="Bundle (unread+recent+search) with compact JSON output",
        cmd=[
            "bundle",
            "--json",
            "--compact",
            "--unread-limit", "20",
            "--recent-limit", "10",
            "--query", "http",
            "--search-limit", "20",
            "--max-text-chars", "120",
        ],
        iterations=iterations,
    )


def benchmark_daemon_bundle(
    iterations: int = 10,
    *,
    use_fast_client: bool = False,
    use_rust_client: bool = False,
    include_text_only_search: bool = False,
) -> List[BenchmarkResult]:
    """
    Benchmark canonical read workloads via the daemon.

    This measures:
    - one-time daemon startup (time-to-ready)
    - warm per-call end-to-end cost (python client spawn + socket + daemon + stdout capture)
    """

    def _benchmark_daemon_client_cmd(
        *,
        name: str,
        description: str,
        cmd: List[str],
        request: dict[str, Any] | None,
        method: str | None,
        iterations: int,
        timeout: int = 30,
    ) -> BenchmarkResult:
        print(f"Running: {name} (warm) ({iterations} iterations)...", end=" ", flush=True)
        timings: List[float] = []
        successes = 0
        stdout_sizes: List[int] = []
        server_ms: List[float] = []
        server_sqlite_ms: List[float] = []
        server_build_ms: List[float] = []
        server_resolve_ms: List[float] = []
        server_serialize_ms: List[float] = []
        inproc_ms: List[float] = []
        result_counts: List[int] = []

        for _ in range(iterations):
            elapsed, ok, output = run_external_command(cmd, timeout=timeout)
            timings.append(elapsed)
            if ok:
                successes += 1
                stdout_sizes.append(len((output or "").encode("utf-8", errors="ignore")))
                if method:
                    try:
                        parsed = json.loads(output)
                    except Exception:
                        parsed = None
                    if isinstance(parsed, dict):
                        count = _extract_daemon_result_count(parsed, method)
                        if count is not None:
                            result_counts.append(count)
                if request is not None:
                    inproc_start = time.perf_counter()
                    resp = _daemon_request(socket_path, request, timeout_s=timeout)
                    inproc_ms.append((time.perf_counter() - inproc_start) * 1000)
                    if isinstance(resp, dict):
                        meta = resp.get("meta")
                        if isinstance(meta, dict):
                            if isinstance(meta.get("server_ms"), (float, int)):
                                server_ms.append(float(meta["server_ms"]))
                            if isinstance(meta.get("serialize_ms"), (float, int)):
                                server_serialize_ms.append(float(meta["serialize_ms"]))
                            profile = meta.get("profile")
                            if isinstance(profile, dict):
                                if isinstance(profile.get("sqlite_ms"), (float, int)):
                                    server_sqlite_ms.append(float(profile["sqlite_ms"]))
                                if isinstance(profile.get("build_ms"), (float, int)):
                                    server_build_ms.append(float(profile["build_ms"]))
                                if isinstance(profile.get("resolve_ms"), (float, int)):
                                    server_resolve_ms.append(float(profile["resolve_ms"]))

        success_rate = (successes / iterations) * 100 if iterations > 0 else 0.0
        p95_ms = _percentile(sorted(timings), 95.0) or 0.0
        stdout_bytes_mean = statistics.mean(stdout_sizes) if stdout_sizes else None
        approx_tokens_mean = math.ceil(stdout_bytes_mean / BYTES_PER_TOKEN_ESTIMATE) if stdout_bytes_mean is not None else None

        server_p95_ms = _percentile(sorted(server_ms), 95.0) if server_ms else None
        inproc_p95_ms = _percentile(sorted(inproc_ms), 95.0) if inproc_ms else None
        spawn_overhead = None
        if inproc_ms and timings:
            spawn_overhead = statistics.mean(timings) - statistics.mean(inproc_ms)
        result = BenchmarkResult(
            name=name,
            description=description,
            iterations=iterations,
            mean_ms=statistics.mean(timings) if timings else 0.0,
            median_ms=statistics.median(timings) if timings else 0.0,
            p95_ms=p95_ms,
            min_ms=min(timings) if timings else 0.0,
            max_ms=max(timings) if timings else 0.0,
            std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0.0,
            success_rate=success_rate,
            stdout_bytes_mean=stdout_bytes_mean,
            approx_tokens_mean=approx_tokens_mean,
            server_ms_mean=statistics.mean(server_ms) if server_ms else None,
            server_ms_median=statistics.median(server_ms) if server_ms else None,
            server_ms_p95=server_p95_ms,
            server_ms_min=min(server_ms) if server_ms else None,
            server_ms_max=max(server_ms) if server_ms else None,
            server_sqlite_ms_mean=statistics.mean(server_sqlite_ms) if server_sqlite_ms else None,
            server_build_ms_mean=statistics.mean(server_build_ms) if server_build_ms else None,
            server_resolve_ms_mean=statistics.mean(server_resolve_ms) if server_resolve_ms else None,
            server_serialize_ms_mean=statistics.mean(server_serialize_ms) if server_serialize_ms else None,
            inproc_ms_mean=statistics.mean(inproc_ms) if inproc_ms else None,
            inproc_ms_median=statistics.median(inproc_ms) if inproc_ms else None,
            inproc_ms_p95=inproc_p95_ms,
            inproc_ms_min=min(inproc_ms) if inproc_ms else None,
            inproc_ms_max=max(inproc_ms) if inproc_ms else None,
            spawn_overhead_ms_mean=spawn_overhead,
            result_count_mean=statistics.mean(result_counts) if result_counts else None,
        )
        print(f"✓ (mean: {result.mean_ms:.2f}ms, success: {success_rate:.0f}%)")
        return result

    with tempfile.TemporaryDirectory(prefix="wolfies-imessage-daemon-", dir="/tmp") as d:
        dpath = Path(d)
        socket_path = dpath / "daemon.sock"
        pid_path = dpath / "daemon.pid"

        time_to_ready_ms = _start_daemon_for_bench(socket_path=socket_path, pidfile_path=pid_path, timeout_s=8.0)

        try:
            startup_result = BenchmarkResult(
                name="daemon_startup_ready",
                description="Daemon startup: time-to-ready (health probe)",
                iterations=1,
                mean_ms=time_to_ready_ms,
                median_ms=time_to_ready_ms,
                p95_ms=time_to_ready_ms,
                min_ms=time_to_ready_ms,
                max_ms=time_to_ready_ms,
                std_dev_ms=0.0,
                success_rate=100.0,
            )

            if use_rust_client:
                name_prefix = "daemon_rustclient_"
                client_path = RUST_DAEMON_CLIENT_PATH
                base = [str(client_path), "--socket", str(socket_path), "--minimal"]
            elif use_fast_client:
                name_prefix = "daemon_fastclient_"
                client_path = DAEMON_CLIENT_FAST_PATH
                base = [str(client_path), "--socket", str(socket_path), "--minimal"]
            else:
                name_prefix = "daemon_"
                client_path = DAEMON_CLIENT_PATH
                base = ["python3", str(client_path), "--socket", str(socket_path), "--minimal"]

            warm_results: List[BenchmarkResult] = []
            warm_results.append(
                _benchmark_daemon_client_cmd(
                    name=f"{name_prefix}unread_count",
                    description="Unread count via daemon (thin client, warm daemon)",
                    cmd=base + ["unread-count"],
                    request={"id": "bench", "v": 1, "method": "unread_count", "params": {}},
                    method="unread_count",
                    iterations=iterations,
                )
            )
            warm_results.append(
                _benchmark_daemon_client_cmd(
                    name=f"{name_prefix}unread_messages_20",
                    description="Unread messages via daemon (limit 20, thin client, warm daemon)",
                    cmd=base + ["unread", "--limit", "20"],
                    request={
                        "id": "bench",
                        "v": 1,
                        "method": "unread_messages",
                        "params": {"limit": 20, "minimal": True},
                    },
                    method="unread_messages",
                    iterations=iterations,
                )
            )
            warm_results.append(
                _benchmark_daemon_client_cmd(
                    name=f"{name_prefix}recent_10",
                    description="Recent messages via daemon (limit 10, thin client, warm daemon)",
                    cmd=base + ["recent", "--limit", "10"],
                    request={
                        "id": "bench",
                        "v": 1,
                        "method": "recent",
                        "params": {"limit": 10, "minimal": True},
                    },
                    method="recent",
                    iterations=iterations,
                )
            )
            warm_results.append(
                _benchmark_daemon_client_cmd(
                    name=f"{name_prefix}text_search_http_20",
                    description="Text search via daemon (query=http, limit 20, thin client, warm daemon)",
                    cmd=base + ["text-search", "http", "--limit", "20"],
                    request={
                        "id": "bench",
                        "v": 1,
                        "method": "text_search",
                        "params": {"query": "http", "limit": 20, "minimal": True},
                    },
                    method="text_search",
                    iterations=iterations,
                )
            )
            if include_text_only_search:
                warm_results.append(
                    _benchmark_daemon_client_cmd(
                        name=f"{name_prefix}text_search_http_20_text_only",
                        description="Text search via daemon (text-only, query=http, limit 20, warm daemon)",
                        cmd=base + ["--text-only-search", "text-search", "http", "--limit", "20"],
                        request={
                            "id": "bench",
                            "v": 1,
                            "method": "text_search",
                            "params": {"query": "http", "limit": 20, "minimal": True, "text_only": True},
                        },
                        method="text_search",
                        iterations=iterations,
                    )
                )
            warm_results.append(
                _benchmark_daemon_client_cmd(
                    name=f"{name_prefix}bundle",
                    description="Bundle via daemon (thin client, warm daemon)",
                    cmd=base
                    + [
                        "bundle",
                        "--unread-limit",
                        "20",
                        "--recent-limit",
                        "10",
                        "--query",
                        "http",
                        "--search-limit",
                        "20",
                    ],
                    request={
                        "id": "bench",
                        "v": 1,
                        "method": "bundle",
                        "params": {
                            "unread_limit": 20,
                            "recent_limit": 10,
                            "query": "http",
                            "search_limit": 20,
                            "minimal": True,
                        },
                    },
                    method="bundle",
                    iterations=iterations,
                )
            )
            if include_text_only_search:
                warm_results.append(
                    _benchmark_daemon_client_cmd(
                        name=f"{name_prefix}bundle_text_only_search",
                        description="Bundle via daemon (text-only search, warm daemon)",
                        cmd=base
                        + [
                            "--text-only-search",
                            "bundle",
                            "--unread-limit",
                            "20",
                            "--recent-limit",
                            "10",
                            "--query",
                            "http",
                            "--search-limit",
                            "20",
                        ],
                        request={
                            "id": "bench",
                            "v": 1,
                            "method": "bundle",
                            "params": {
                                "unread_limit": 20,
                                "recent_limit": 10,
                                "query": "http",
                                "search_limit": 20,
                                "minimal": True,
                                "text_only": True,
                            },
                        },
                        method="bundle",
                        iterations=iterations,
                    )
                )

            return [startup_result, *warm_results]
        finally:
            _stop_daemon_for_bench(socket_path=socket_path, pidfile_path=pid_path)


def benchmark_analytics(iterations: int = 5) -> BenchmarkResult:
    """Test conversation analytics (computationally intensive)."""
    return benchmark_command(
        name="analytics_30days",
        description="Conversation analytics for 30 days",
        cmd=["analytics", "--days", "30"],
        iterations=iterations
    )


def benchmark_followup_detection(iterations: int = 5) -> BenchmarkResult:
    """Test follow-up detection (complex query)."""
    return benchmark_command(
        name="followup_detection",
        description="Detect follow-ups needed (7 days)",
        cmd=["followup", "--days", "7"],
        iterations=iterations
    )


# =============================================================================
# NEW COMMAND BENCHMARKS (T0, T1, T2)
# =============================================================================


def benchmark_groups_list(iterations: int = 10) -> BenchmarkResult:
    """Test listing group chats."""
    return benchmark_command(
        name="groups_list",
        description="List group chats",
        cmd=["groups", "--json"],
        iterations=iterations
    )


def benchmark_attachments(iterations: int = 10) -> BenchmarkResult:
    """Test getting attachments."""
    return benchmark_command(
        name="attachments",
        description="Get attachments (photos/videos/files)",
        cmd=["attachments", "--limit", "20", "--json"],
        iterations=iterations
    )


def benchmark_reactions(iterations: int = 10) -> BenchmarkResult:
    """Test getting reactions/tapbacks."""
    return benchmark_command(
        name="reactions",
        description="Get reactions (tapbacks)",
        cmd=["reactions", "--limit", "20", "--json"],
        iterations=iterations
    )


def benchmark_links(iterations: int = 10) -> BenchmarkResult:
    """Test extracting links from messages."""
    return benchmark_command(
        name="links",
        description="Extract shared URLs",
        cmd=["links", "--limit", "20", "--json"],
        iterations=iterations
    )


def benchmark_voice_messages(iterations: int = 10) -> BenchmarkResult:
    """Test getting voice messages."""
    return benchmark_command(
        name="voice_messages",
        description="Get voice messages",
        cmd=["voice", "--limit", "10", "--json"],
        iterations=iterations
    )


def benchmark_handles(iterations: int = 10) -> BenchmarkResult:
    """Test listing recent handles."""
    return benchmark_command(
        name="handles_list",
        description="List recent phone/email handles",
        cmd=["handles", "--days", "7", "--json"],
        iterations=iterations
    )


def benchmark_unknown_senders(iterations: int = 5) -> BenchmarkResult:
    """Test finding unknown senders (computationally intensive)."""
    return benchmark_command(
        name="unknown_senders",
        description="Find messages from non-contacts",
        cmd=["unknown", "--days", "7", "--json"],
        iterations=iterations
    )


def benchmark_scheduled(iterations: int = 10) -> BenchmarkResult:
    """Test getting scheduled messages."""
    return benchmark_command(
        name="scheduled_messages",
        description="Get scheduled messages",
        cmd=["scheduled", "--json"],
        iterations=iterations
    )


def benchmark_summary(iterations: int = 5) -> BenchmarkResult:
    """Test getting conversation summary (complex)."""
    return benchmark_command(
        name="conversation_summary",
        description="Get conversation analytics (contact-agnostic, complex operation)",
        cmd=["analytics", "--days", "30", "--json"],
        iterations=iterations
    )


def benchmark_mcp_server_startup(iterations: int = 10) -> BenchmarkResult:
    """
    Benchmark MCP server startup overhead.

    This simulates the cost of starting the MCP server for each Claude Code session.
    We measure the time to import and initialize the server.
    """
    print(f"Running: MCP server startup simulation ({iterations} iterations)...", end=" ", flush=True)

    timings = []
    successes = 0

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            # Simulate MCP server import and initialization
            result = subprocess.run(
                [
                    "python3", "-c",
                    "import sys; "
                    f"sys.path.insert(0, '{REPO_ROOT}'); "
                    "from mcp_server.server import app; "
                    "print('initialized')"
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(REPO_ROOT)
            )
            elapsed = (time.perf_counter() - start) * 1000
            success = "initialized" in result.stdout
            timings.append(elapsed)
            if success:
                successes += 1
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)

    success_rate = (successes / iterations) * 100 if iterations > 0 else 0

    result = BenchmarkResult(
        name="mcp_server_startup",
        description="MCP server import + initialization overhead",
        iterations=iterations,
        mean_ms=statistics.mean(timings) if timings else 0,
        median_ms=statistics.median(timings) if timings else 0,
        p95_ms=_percentile(sorted(timings), 95.0) or 0.0,
        min_ms=min(timings) if timings else 0,
        max_ms=max(timings) if timings else 0,
        std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
        success_rate=success_rate
    )

    print(f"✓ (mean: {result.mean_ms:.2f}ms, success: {success_rate:.0f}%)")
    return result


def run_quick_benchmarks(*, iterations: int = 5) -> List[BenchmarkResult]:
    """Run a quick subset of benchmarks (fast execution)."""
    print("\n=== Quick Benchmark Suite ===\n")
    return [
        benchmark_startup_overhead(iterations=iterations),
        benchmark_contacts_list(iterations=iterations),
        benchmark_unread_messages(iterations=iterations),
        benchmark_recent_conversations(iterations=iterations, limit=10),
        benchmark_search_small(iterations=iterations),
        benchmark_bundle(iterations=iterations),
    ]


def run_llm_canonical_benchmarks(*, iterations: int = 5, include_daemon: bool = True) -> List[BenchmarkResult]:
    """
    Canonical LLM-facing workload suite (JSON + minimal output).

    This is closer to how an LLM tool runner uses the gateway: JSON in/out, bounded limits,
    and token-conscious output shaping.
    """
    print("\n=== LLM Canonical Benchmark Suite (JSON minimal) ===\n")

    results: List[BenchmarkResult] = []

    # CLI cold path (spawn per call).
    results.append(
        benchmark_command(
            name="llm_cli_unread_20_minimal_json",
            description="Unread messages (20) via CLI (JSON minimal)",
            cmd=["unread", "--limit", "20", "--json", "--minimal"],
            iterations=iterations,
        )
    )
    results.append(
        benchmark_command(
            name="llm_cli_recent_10_minimal_json",
            description="Recent conversations (10) via CLI (JSON minimal)",
            cmd=["recent", "--limit", "10", "--json", "--minimal"],
            iterations=iterations,
        )
    )
    results.append(
        benchmark_command(
            name="llm_cli_text_search_http_20_minimal_json",
            description="Text search (http, 20) via CLI (JSON minimal)",
            cmd=["text-search", "http", "--limit", "20", "--json", "--minimal"],
            iterations=iterations,
        )
    )
    results.append(
        benchmark_command(
            name="llm_cli_bundle_minimal_json",
            description="Bundle via CLI (JSON minimal)",
            cmd=[
                "bundle",
                "--json",
                "--minimal",
                "--unread-limit",
                "20",
                "--recent-limit",
                "10",
                "--query",
                "http",
                "--search-limit",
                "20",
            ],
            iterations=iterations,
        )
    )

    if include_daemon:
        results.extend(benchmark_daemon_bundle(iterations=iterations))

    return results

def run_full_benchmarks() -> List[BenchmarkResult]:
    """Run the full benchmark suite."""
    print("\n=== Full Benchmark Suite ===\n")
    return [
        # Core operations
        benchmark_startup_overhead(iterations=20),
        benchmark_contacts_list(iterations=10),
        benchmark_contacts_list_json(iterations=10),

        # Message operations
        benchmark_unread_messages(iterations=10),
        benchmark_recent_conversations(iterations=10, limit=10),
        benchmark_recent_conversations(iterations=10, limit=50),

        # Search operations (varying complexity)
        benchmark_search_small(iterations=10),
        benchmark_search_medium(iterations=10),
        benchmark_search_large(iterations=5),
        benchmark_bundle(iterations=10),

        # Complex operations
        benchmark_analytics(iterations=5),
        benchmark_followup_detection(iterations=5),

        # T0 Features - Core
        benchmark_groups_list(iterations=10),
        benchmark_attachments(iterations=10),

        # T1 Features - Advanced
        benchmark_reactions(iterations=10),
        benchmark_links(iterations=10),
        benchmark_voice_messages(iterations=10),

        # T2 Features - Discovery
        benchmark_handles(iterations=10),
        benchmark_unknown_senders(iterations=5),
        benchmark_scheduled(iterations=10),
        benchmark_summary(iterations=5),
    ]


def run_comparison_benchmarks() -> List[BenchmarkResult]:
    """Run benchmarks comparing Gateway CLI vs MCP server."""
    print("\n=== Gateway CLI vs MCP Server Comparison ===\n")

    cli_results = [
        benchmark_startup_overhead(iterations=20),
        benchmark_contacts_list(iterations=10),
        benchmark_search_small(iterations=10),
    ]

    mcp_result = benchmark_mcp_server_startup(iterations=20)

    return cli_results + [mcp_result]


def run_comprehensive_benchmarks(
    iterations: int = 5,
    timeout: int = 30,
    include_rag: bool = False
) -> List[BenchmarkResult]:
    """
    Comprehensive, safe benchmark matrix across read-only commands.

    Excludes side-effectful commands: send*, add-contact, index, clear, migrate.
    """
    print("\n=== Comprehensive Benchmark Suite ===\n")

    results: List[BenchmarkResult] = []
    sample_contact = _get_sample_contact_name()
    sample_group_id = _get_sample_group_id()
    sample_guid = _get_sample_message_guid()

    results.append(benchmark_command_quiet(
        name="startup_overhead_quiet",
        description="CLI startup time with --help (quiet)",
        cmd=["--help"],
        iterations=iterations,
        timeout=timeout
    ))

    # Core operations
    results.append(benchmark_command_quiet(
        name="contacts_json",
        description="List all contacts (JSON)",
        cmd=["contacts", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="recent_10_json",
        description="Recent conversations (10, JSON)",
        cmd=["recent", "--limit", "10", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="recent_50_json",
        description="Recent conversations (50, JSON)",
        cmd=["recent", "--limit", "50", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="unread_json",
        description="Unread messages (JSON)",
        cmd=["unread", "--json"],
        iterations=iterations,
        timeout=timeout
    ))

    # Discovery
    results.append(benchmark_command_quiet(
        name="handles_30d_json",
        description="Recent handles (30d, JSON)",
        cmd=["handles", "--days", "30", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="unknown_7d_json",
        description="Unknown senders (7d, JSON)",
        cmd=["unknown", "--days", "7", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="scheduled_json",
        description="Scheduled messages (JSON)",
        cmd=["scheduled", "--json"],
        iterations=iterations,
        timeout=timeout
    ))

    # Links
    results.append(benchmark_command_quiet(
        name="links_default_json",
        description="Links (default lookback, JSON)",
        cmd=["links", "--limit", "100", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="links_all_time_json",
        description="Links (all-time, JSON)",
        cmd=["links", "--all-time", "--limit", "100", "--json"],
        iterations=iterations,
        timeout=timeout
    ))

    # Groups
    results.append(benchmark_command_quiet(
        name="groups_json",
        description="List group chats (JSON)",
        cmd=["groups", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    if sample_group_id:
        results.append(benchmark_command_quiet(
            name="group_messages_50_json",
            description="Group messages (50, JSON)",
            cmd=["group-messages", "--group-id", sample_group_id, "--limit", "50", "--json"],
            iterations=iterations,
            timeout=timeout
        ))

    # Media & reactions
    results.append(benchmark_command_quiet(
        name="attachments_50_json",
        description="Attachments (50, JSON)",
        cmd=["attachments", "--limit", "50", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="voice_50_json",
        description="Voice messages (50, JSON)",
        cmd=["voice", "--limit", "50", "--json"],
        iterations=iterations,
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="reactions_100_json",
        description="Reactions (100, JSON)",
        cmd=["reactions", "--limit", "100", "--json"],
        iterations=iterations,
        timeout=timeout
    ))

    # Contact-specific
    if sample_contact:
        results.append(benchmark_command_quiet(
            name="messages_contact_20_json",
            description="Messages with sample contact (20, JSON)",
            cmd=["messages", sample_contact, "--limit", "20", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="find_contact_noquery_json",
            description="Find with sample contact (no query, JSON)",
            cmd=["find", sample_contact, "--limit", "50", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="find_contact_query_json",
            description="Find with sample contact + query (JSON)",
            cmd=["find", sample_contact, "--query", "http", "--limit", "50", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="summary_contact_7d_json",
            description="Summary with sample contact (7d, JSON)",
            cmd=["summary", sample_contact, "--days", "7", "--limit", "200", "--json"],
            iterations=max(3, iterations),
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="analytics_contact_30d_json",
            description="Analytics for sample contact (30d, JSON)",
            cmd=["analytics", sample_contact, "--days", "30", "--json"],
            iterations=max(3, iterations),
            timeout=timeout
        ))

    # Whole-db analytics/followup
    results.append(benchmark_command_quiet(
        name="analytics_7d_json",
        description="Analytics (7d, JSON)",
        cmd=["analytics", "--days", "7", "--json"],
        iterations=max(3, iterations),
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="analytics_30d_json",
        description="Analytics (30d, JSON)",
        cmd=["analytics", "--days", "30", "--json"],
        iterations=max(3, iterations),
        timeout=timeout
    ))
    results.append(benchmark_command_quiet(
        name="followup_7d_json",
        description="Follow-up detection (7d, JSON)",
        cmd=["followup", "--days", "7", "--json"],
        iterations=max(3, iterations),
        timeout=timeout
    ))

    # Thread by GUID
    if sample_guid:
        results.append(benchmark_command_quiet(
            name="thread_50_json",
            description="Thread lookup by GUID (50, JSON)",
            cmd=["thread", "--guid", sample_guid, "--limit", "50", "--json"],
            iterations=iterations,
            timeout=timeout
        ))

    # RAG (read-only; may call out to embeddings/LLM depending on config)
    if include_rag:
        results.append(benchmark_command_quiet(
            name="sources_json",
            description="RAG sources (JSON)",
            cmd=["sources", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="stats_json",
            description="RAG stats (JSON)",
            cmd=["stats", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="search_json",
            description="RAG search (JSON)",
            cmd=["search", "dinner plans", "--json"],
            iterations=iterations,
            timeout=timeout
        ))
        results.append(benchmark_command_quiet(
            name="ask_json",
            description="RAG ask (JSON)",
            cmd=["ask", "What did I talk about this week?", "--json"],
            iterations=iterations,
            timeout=timeout
        ))

    return results


def print_daemon_overhead_summary(results: List[BenchmarkResult]) -> None:
    """Print end-to-end vs in-process daemon timing + spawn overhead."""
    rows = []
    for r in results:
        if not r.name.startswith("daemon_"):
            continue
        if r.inproc_ms_mean is None and r.server_ms_mean is None:
            continue
        rows.append(r)

    if not rows:
        return

    print("\n=== Daemon Overhead Summary (end-to-end vs in-proc) ===")
    print("name\tmean_ms\tinproc_ms\tspawn_overhead_ms\tserver_ms")
    for r in rows:
        mean_ms = f"{r.mean_ms:.2f}" if r.mean_ms is not None else "-"
        inproc_ms = f"{r.inproc_ms_mean:.2f}" if r.inproc_ms_mean is not None else "-"
        overhead = f"{r.spawn_overhead_ms_mean:.2f}" if r.spawn_overhead_ms_mean is not None else "-"
        server_ms = f"{r.server_ms_mean:.2f}" if r.server_ms_mean is not None else "-"
        print(f"{r.name}\t{mean_ms}\t{inproc_ms}\t{overhead}\t{server_ms}")


def print_summary(results: List[BenchmarkResult]):
    """Print a human-readable summary of benchmark results."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)

    # Group by performance tier
    fast = [r for r in results if r.mean_ms < 100]
    medium = [r for r in results if 100 <= r.mean_ms < 500]
    slow = [r for r in results if r.mean_ms >= 500]

    print("\n⚡ FAST (<100ms):")
    for r in fast:
        print(f"  {r.name:30s} {r.mean_ms:7.2f}ms ± {r.std_dev_ms:6.2f}ms")

    print("\n⚙️  MEDIUM (100-500ms):")
    for r in medium:
        print(f"  {r.name:30s} {r.mean_ms:7.2f}ms ± {r.std_dev_ms:6.2f}ms")

    print("\n🐌 SLOW (>500ms):")
    for r in slow:
        print(f"  {r.name:30s} {r.mean_ms:7.2f}ms ± {r.std_dev_ms:6.2f}ms")

    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS:")
    all_means = [r.mean_ms for r in results]
    print(f"  Average execution time: {statistics.mean(all_means):.2f}ms")
    print(f"  Median execution time:  {statistics.median(all_means):.2f}ms")
    print(f"  Fastest operation:      {min(all_means):.2f}ms ({min(results, key=lambda r: r.mean_ms).name})")
    print(f"  Slowest operation:      {max(all_means):.2f}ms ({max(results, key=lambda r: r.mean_ms).name})")

    # Success rates
    failed = [r for r in results if r.success_rate < 100]
    if failed:
        print("\n⚠️  OPERATIONS WITH FAILURES:")
        for r in failed:
            print(f"  {r.name}: {r.success_rate:.0f}% success rate")
    else:
        print("\n✓ All operations completed successfully (100% success rate)")

    print("=" * 80)


def main():
    """Run the benchmark suite CLI."""
    parser = argparse.ArgumentParser(
        description="Benchmark suite for iMessage CLI Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmarks only (faster)"
    )
    parser.add_argument(
        "--compare-mcp",
        action="store_true",
        help="Include MCP server comparison benchmarks"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive benchmarks across all safe read-only commands"
    )
    parser.add_argument(
        "--include-rag",
        action="store_true",
        help="Include RAG read-only benchmarks (stats/sources/search/ask)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override default iterations per benchmark"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-command timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--include-daemon",
        action="store_true",
        help="Include daemon warm-path benchmarks (requires daemon to access chat.db)",
    )
    parser.add_argument(
        "--daemon-fast-client",
        action="store_true",
        help="Also benchmark daemon with fast client wrapper (python3 -S)",
    )
    parser.add_argument(
        "--daemon-text-only-search",
        action="store_true",
        help="Also benchmark daemon with text-only search (explicit flag)",
    )
    parser.add_argument(
        "--daemon-rust-client",
        action="store_true",
        help="Also benchmark daemon with Rust client (requires pre-built binary)",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Run canonical LLM-facing benchmarks (JSON minimal), optionally including daemon warm-path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Save results to file (JSON format)"
    )

    args = parser.parse_args()

    # Run benchmarks
    results: list[BenchmarkResult] = []

    if args.llm:
        # --llm mode handles daemon internally via include_daemon parameter
        results = run_llm_canonical_benchmarks(iterations=args.iterations or 5, include_daemon=bool(args.include_daemon))
    elif args.comprehensive:
        results = run_comprehensive_benchmarks(
            iterations=args.iterations or 5,
            timeout=args.timeout,
            include_rag=args.include_rag
        )
    elif args.quick:
        results = run_quick_benchmarks(iterations=args.iterations or 5)
    elif args.compare_mcp:
        results = run_comparison_benchmarks()
    elif args.include_daemon:
        # Standalone daemon-only mode (no other suite selected)
        pass  # Results will be added below
    else:
        results = run_full_benchmarks()

    # Add daemon benchmarks for non-llm modes (llm mode handles it internally)
    if args.include_daemon and not args.llm:
        results.extend(
            benchmark_daemon_bundle(
                iterations=args.iterations or 5,
                include_text_only_search=bool(args.daemon_text_only_search),
            )
        )
        if args.daemon_fast_client:
            results.extend(
                benchmark_daemon_bundle(
                    iterations=args.iterations or 5,
                    use_fast_client=True,
                    include_text_only_search=bool(args.daemon_text_only_search),
                )
            )
        if args.daemon_rust_client:
            if not RUST_DAEMON_CLIENT_PATH.exists():
                print(f"Warning: Rust client not found at {RUST_DAEMON_CLIENT_PATH}")
                print("  Build with: ./Texting/gateway/build_rust_client.sh")
            else:
                results.extend(
                    benchmark_daemon_bundle(
                        iterations=args.iterations or 5,
                        use_rust_client=True,
                        include_text_only_search=bool(args.daemon_text_only_search),
                    )
                )

    # Create suite
    suite = BenchmarkSuite(
        suite_name="comprehensive" if args.comprehensive else ("quick" if args.quick else "full"),
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        results=results,
        metadata={
            "cli_path": str(CLI_PATH),
            "total_benchmarks": len(results),
            "python_version": sys.version.split()[0],
            "timeout_s": args.timeout,
            "include_rag": bool(args.include_rag) if args.comprehensive else False,
            "iterations_override": args.iterations
        }
    )

    print_daemon_overhead_summary(results)

    # Output results
    if args.json or args.output:
        output_data = {
            "suite_name": suite.suite_name,
            "timestamp": suite.timestamp,
            "metadata": suite.metadata,
            "results": [asdict(r) for r in suite.results]
        }

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to {args.output}")
        else:
            print(json.dumps(output_data, indent=2))
    else:
        print_summary(results)

    return 0


if __name__ == '__main__':
    sys.exit(main())
