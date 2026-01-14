#!/usr/bin/env python3
"""
FGP API Benchmark - Gmail, Calendar, GitHub Daemons

Tests individual methods and multi-step workflows across all FGP daemons.

Daemons tested:
- Gmail (PyO3 + Google API)
- Calendar (PyO3 + Google API)
- GitHub (Native Rust + gh CLI)

Usage:
    python3 fgp_api_benchmark.py --iterations 3

CHANGELOG (recent first, max 5 entries)
01/14/2026 - Initial implementation (Claude)
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Socket paths
SOCKETS = {
    "gmail": Path.home() / ".fgp" / "services" / "gmail" / "daemon.sock",
    "calendar": Path.home() / ".fgp" / "services" / "calendar" / "daemon.sock",
    "github": Path.home() / ".fgp" / "services" / "github" / "daemon.sock",
}
RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class BenchResult:
    """Result of a single benchmark call."""
    daemon: str
    method: str
    iteration: int
    latency_ms: float
    success: bool
    payload_size: int = 0
    error: str | None = None


@dataclass
class MethodSummary:
    """Statistical summary for a method."""
    daemon: str
    method: str
    iterations: int
    success_rate: float
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    mean_payload: float


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    generated_at: str
    iterations: int
    results: list[BenchResult] = field(default_factory=list)
    summaries: list[MethodSummary] = field(default_factory=list)


class FGPClient:
    """Generic FGP daemon client."""

    def __init__(self, daemon_name: str, socket_path: Path):
        self.daemon = daemon_name
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
            sock.settimeout(30)
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


def bench_method(
    client: FGPClient,
    method: str,
    params: dict | None,
    iterations: int,
    label: str | None = None,
) -> list[BenchResult]:
    """Benchmark a single method."""
    results = []
    display = label or method

    for i in range(iterations):
        try:
            result, latency = client.call(method, params)
            payload = len(json.dumps(result)) if result else 0
            results.append(BenchResult(
                daemon=client.daemon,
                method=display,
                iteration=i + 1,
                latency_ms=latency,
                success=True,
                payload_size=payload,
            ))
        except Exception as e:
            results.append(BenchResult(
                daemon=client.daemon,
                method=display,
                iteration=i + 1,
                latency_ms=0,
                success=False,
                error=str(e)[:200],
            ))
        time.sleep(0.2)  # Small delay between iterations

    return results


def compute_summary(results: list[BenchResult], daemon: str, method: str) -> MethodSummary:
    """Compute statistics for a method."""
    filtered = [r for r in results if r.daemon == daemon and r.method == method and r.success]
    all_results = [r for r in results if r.daemon == daemon and r.method == method]

    if not filtered:
        return MethodSummary(
            daemon=daemon,
            method=method,
            iterations=len(all_results),
            success_rate=0.0,
            mean_ms=0.0,
            median_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            std_dev_ms=0.0,
            mean_payload=0.0,
        )

    latencies = [r.latency_ms for r in filtered]
    payloads = [r.payload_size for r in filtered]

    return MethodSummary(
        daemon=daemon,
        method=method,
        iterations=len(all_results),
        success_rate=len(filtered) / len(all_results) if all_results else 0.0,
        mean_ms=statistics.mean(latencies),
        median_ms=statistics.median(latencies),
        min_ms=min(latencies),
        max_ms=max(latencies),
        std_dev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
        mean_payload=statistics.mean(payloads),
    )


def print_daemon_table(summaries: list[MethodSummary], daemon: str) -> None:
    """Print results table for a daemon."""
    daemon_summaries = [s for s in summaries if s.daemon == daemon]
    if not daemon_summaries:
        return

    print(f"\n{daemon.upper()} Daemon")
    print("-" * 70)
    print(f"{'Method':<20} {'Mean':>10} {'Min':>10} {'Max':>10} {'Payload':>12} {'Success':>8}")
    print("-" * 70)

    for s in daemon_summaries:
        if s.success_rate > 0:
            print(
                f"{s.method:<20} {s.mean_ms:>9.0f}ms {s.min_ms:>9.0f}ms {s.max_ms:>9.0f}ms "
                f"{s.mean_payload:>10.0f}B {s.success_rate*100:>7.0f}%"
            )
        else:
            print(f"{s.method:<20} {'FAILED':>10} {'-':>10} {'-':>10} {'-':>12} {0:>7.0f}%")


def main():
    parser = argparse.ArgumentParser(description="FGP API Benchmark")
    parser.add_argument("--iterations", type=int, default=3, help="Iterations per method")
    args = parser.parse_args()

    print("FGP API Benchmark")
    print("=" * 70)
    print(f"Testing: Gmail, Calendar, GitHub daemons")
    print(f"Iterations: {args.iterations}")
    print()

    # Initialize clients
    clients = {}
    for name, path in SOCKETS.items():
        client = FGPClient(name, path)
        if client.is_available():
            clients[name] = client
            print(f"  [OK] {name} daemon")
        else:
            print(f"  [SKIP] {name} daemon (not running)")

    if not clients:
        print("\nNo daemons available. Exiting.")
        return

    print()
    results: list[BenchResult] = []

    # =========================================================================
    # GMAIL BENCHMARKS
    # =========================================================================
    if "gmail" in clients:
        gmail = clients["gmail"]
        print("[Gmail Daemon]")

        # inbox
        print("  gmail.inbox...")
        results.extend(bench_method(gmail, "gmail.inbox", {"limit": 5}, args.iterations, "inbox"))

        # search
        print("  gmail.search...")
        results.extend(bench_method(gmail, "gmail.search", {"query": "from:*", "limit": 5}, args.iterations, "search"))

        # Get first thread ID for thread test
        print("  gmail.thread...")
        try:
            inbox_result, _ = gmail.call("gmail.inbox", {"limit": 1})
            emails = inbox_result.get("emails", [])
            if emails:
                thread_id = emails[0].get("thread_id")
                results.extend(bench_method(gmail, "gmail.thread", {"thread_id": thread_id}, args.iterations, "thread"))
            else:
                print("    (skipped - no emails)")
        except Exception as e:
            print(f"    (failed: {e})")

        # unread
        print("  gmail.unread...")
        results.extend(bench_method(gmail, "gmail.unread", {"limit": 5}, args.iterations, "unread"))

    # =========================================================================
    # CALENDAR BENCHMARKS
    # =========================================================================
    if "calendar" in clients:
        calendar = clients["calendar"]
        print("\n[Calendar Daemon]")

        # today
        print("  calendar.today...")
        results.extend(bench_method(calendar, "calendar.today", {}, args.iterations, "today"))

        # upcoming
        print("  calendar.upcoming...")
        results.extend(bench_method(calendar, "calendar.upcoming", {"days": 7, "limit": 10}, args.iterations, "upcoming"))

        # search
        print("  calendar.search...")
        results.extend(bench_method(calendar, "calendar.search", {"query": "meeting", "days": 30}, args.iterations, "search"))

        # free_slots
        print("  calendar.free_slots...")
        results.extend(bench_method(calendar, "calendar.free_slots", {"duration_minutes": 30, "days": 7}, args.iterations, "free_slots"))

    # =========================================================================
    # GITHUB BENCHMARKS
    # =========================================================================
    if "github" in clients:
        github = clients["github"]
        print("\n[GitHub Daemon]")

        # user
        print("  github.user...")
        results.extend(bench_method(github, "github.user", {}, args.iterations, "user"))

        # repos
        print("  github.repos...")
        results.extend(bench_method(github, "github.repos", {"limit": 10}, args.iterations, "repos"))

        # notifications
        print("  github.notifications...")
        results.extend(bench_method(github, "github.notifications", {}, args.iterations, "notifications"))

        # issues (on a specific repo)
        print("  github.issues...")
        results.extend(bench_method(github, "github.issues", {"repo": "wolfiesch/fgp-daemon", "limit": 5}, args.iterations, "issues"))

    # =========================================================================
    # COMPUTE SUMMARIES
    # =========================================================================
    summaries = []
    methods_by_daemon = {}
    for r in results:
        key = (r.daemon, r.method)
        if key not in methods_by_daemon:
            methods_by_daemon[key] = True

    for (daemon, method) in methods_by_daemon.keys():
        summaries.append(compute_summary(results, daemon, method))

    # =========================================================================
    # PRINT RESULTS
    # =========================================================================
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    for daemon in ["gmail", "calendar", "github"]:
        print_daemon_table(summaries, daemon)

    # =========================================================================
    # SAVE RESULTS
    # =========================================================================
    report = BenchmarkReport(
        generated_at=datetime.now().isoformat(),
        iterations=args.iterations,
        results=results,
        summaries=summaries,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"fgp_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_dict = {
        "generated_at": report.generated_at,
        "iterations": report.iterations,
        "results": [asdict(r) for r in report.results],
        "summaries": [asdict(s) for s in report.summaries],
    }

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    # Print quick summary
    print("\n" + "=" * 70)
    print("QUICK SUMMARY")
    print("=" * 70)
    for daemon in ["gmail", "calendar", "github"]:
        daemon_summaries = [s for s in summaries if s.daemon == daemon and s.success_rate > 0]
        if daemon_summaries:
            avg = statistics.mean([s.mean_ms for s in daemon_summaries])
            print(f"{daemon:<10}: avg {avg:.0f}ms across {len(daemon_summaries)} methods")


if __name__ == "__main__":
    main()
