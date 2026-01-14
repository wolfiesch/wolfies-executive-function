#!/usr/bin/env python3
"""
Browser Automation Benchmark Suite

Compares browser automation tools:
1. Playwright MCP (npx @playwright/mcp@latest) - Headless browser via MCP stdio
2. browser-gateway - Warm daemon CLI (when available)
3. claude-in-chrome - Manual testing within Claude Code session

Usage:
    python3 benchmarks/browser_benchmark.py
    python3 benchmarks/browser_benchmark.py --iterations 5
    python3 benchmarks/browser_benchmark.py --tool playwright_mcp

CHANGELOG (recent first, max 5 entries)
01/13/2026 - Initial implementation for browser automation benchmarks (Claude)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.browser_tools import (
    BrowserTool,
    BrowserBenchmarkResult,
    PlaywrightMCPTool,
    BrowserGatewayTool,
    AgentBrowserTool,
)
from benchmarks.browser_tools.base import BrowserBenchmarkSummary


# Test URLs
TEST_URLS = {
    "simple": "https://example.com",
    "quotes": "https://quotes.toscrape.com/",
    "form": "https://the-internet.herokuapp.com/login",
}


@dataclass
class BrowserBenchmarkReport:
    """Complete browser benchmark report."""
    generated_at: str
    iterations: int
    warmup: int
    tools_tested: list[str]
    test_urls: dict[str, str]
    results: list[dict] = field(default_factory=list)
    summaries: list[dict] = field(default_factory=list)
    comparison: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _percentile(data: list[float], p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def compute_summary(results: list[BrowserBenchmarkResult], tool: str, operation: str, test_case: str) -> BrowserBenchmarkSummary:
    """Compute statistical summary."""
    filtered = [r for r in results if r.tool == tool and r.operation == operation and r.test_case == test_case]
    if not filtered:
        return BrowserBenchmarkSummary(
            tool=tool, operation=operation, test_case=test_case,
            count=0, success_rate=0, cold_start_mean_ms=0, warm_mean_ms=0,
            mean_ms=0, median_ms=0, p95_ms=0, p99_ms=0,
            min_ms=0, max_ms=0, std_dev_ms=0, avg_tokens=0, avg_response_size=0,
        )

    successful = [r for r in filtered if r.success]
    latencies = [r.latency_ms for r in successful]
    cold_latencies = [r.latency_ms for r in successful if r.is_cold_start]
    warm_latencies = [r.latency_ms for r in successful if not r.is_cold_start]
    tokens = [r.token_estimate for r in successful if r.token_estimate]
    sizes = [r.payload_size for r in successful if r.payload_size]

    return BrowserBenchmarkSummary(
        tool=tool,
        operation=operation,
        test_case=test_case,
        count=len(filtered),
        success_rate=len(successful) / len(filtered) if filtered else 0,
        cold_start_mean_ms=statistics.mean(cold_latencies) if cold_latencies else 0,
        warm_mean_ms=statistics.mean(warm_latencies) if warm_latencies else 0,
        mean_ms=statistics.mean(latencies) if latencies else 0,
        median_ms=statistics.median(latencies) if latencies else 0,
        p95_ms=_percentile(latencies, 95),
        p99_ms=_percentile(latencies, 99),
        min_ms=min(latencies) if latencies else 0,
        max_ms=max(latencies) if latencies else 0,
        std_dev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0,
        avg_tokens=statistics.mean(tokens) if tokens else 0,
        avg_response_size=int(statistics.mean(sizes)) if sizes else 0,
    )


def benchmark_navigation(tool: BrowserTool, iterations: int = 5) -> list[BrowserBenchmarkResult]:
    """Benchmark page navigation."""
    results = []
    url = TEST_URLS["simple"]
    test_case = "navigation_simple"

    print(f"  Navigation ({url})...")

    for i in range(iterations):
        result = tool.navigate(url, test_case=test_case, iteration=i)
        results.append(result)
        status = "✓" if result.success else "✗"
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.0f}ms")

    return results


def benchmark_extraction(tool: BrowserTool, iterations: int = 5) -> list[BrowserBenchmarkResult]:
    """Benchmark content extraction."""
    results = []
    url = TEST_URLS["quotes"]
    test_case = "extraction_quotes"

    print(f"  Extraction ({url})...")

    # First navigate
    nav_result = tool.navigate(url, test_case=test_case, iteration=0)
    if not nav_result.success:
        print(f"    Failed to navigate: {nav_result.error}")
        return results

    for i in range(iterations):
        result = tool.extract({}, test_case=test_case, iteration=i)
        results.append(result)
        status = "✓" if result.success else "✗"
        tokens = result.token_estimate or 0
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.0f}ms (~{tokens} tokens)")

    return results


def benchmark_screenshot(tool: BrowserTool, iterations: int = 5) -> list[BrowserBenchmarkResult]:
    """Benchmark screenshot capture."""
    results = []
    url = TEST_URLS["simple"]
    test_case = "screenshot_simple"
    output_dir = REPO_ROOT / "benchmarks" / "results" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Screenshot ({url})...")

    # First navigate
    nav_result = tool.navigate(url, test_case=test_case, iteration=0)
    if not nav_result.success:
        print(f"    Failed to navigate: {nav_result.error}")
        return results

    for i in range(iterations):
        output_path = str(output_dir / f"{tool.name}_{i}.png")
        result = tool.screenshot(output_path, test_case=test_case, iteration=i)
        results.append(result)
        status = "✓" if result.success else "✗"
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.0f}ms")

    return results


def run_benchmarks(
    iterations: int = 5,
    warmup: int = 1,
    tools: list[str] | None = None,
) -> BrowserBenchmarkReport:
    """Run browser automation benchmarks."""

    # Initialize tools
    available_tools: dict[str, BrowserTool] = {}

    playwright = PlaywrightMCPTool()
    if playwright.is_available():
        available_tools["playwright_mcp"] = playwright
    else:
        print("⚠️  Playwright MCP not available (npx not found)")

    agent_browser = AgentBrowserTool()
    if agent_browser.is_available():
        available_tools["agent_browser"] = agent_browser
    else:
        print("⚠️  agent-browser not available (not installed)")

    gateway = BrowserGatewayTool()
    if gateway.is_available():
        available_tools["browser_gateway"] = gateway
    else:
        print("⚠️  browser-gateway not available (not installed)")

    # Filter to requested tools
    if tools:
        available_tools = {k: v for k, v in available_tools.items() if k in tools}

    if not available_tools:
        print("❌ No browser tools available for benchmarking")
        return BrowserBenchmarkReport(
            generated_at=datetime.now().isoformat(),
            iterations=iterations,
            warmup=warmup,
            tools_tested=[],
            test_urls=TEST_URLS,
            notes=["No browser tools available"],
        )

    print(f"\n🌐 Browser Automation Benchmark")
    print(f"   Tools: {list(available_tools.keys())}")
    print(f"   Iterations: {iterations}")
    print()

    all_results: list[BrowserBenchmarkResult] = []

    for tool_name, tool in available_tools.items():
        print(f"\n📊 {tool_name}")
        print("-" * 40)

        # Warmup
        if warmup > 0:
            print(f"  Warmup ({warmup} iterations)...")
            for _ in range(warmup):
                tool.navigate(TEST_URLS["simple"], test_case="warmup", iteration=0)

        # Benchmark navigation
        results = benchmark_navigation(tool, iterations)
        all_results.extend(results)

        # Benchmark extraction
        results = benchmark_extraction(tool, iterations)
        all_results.extend(results)

        # Benchmark screenshot
        results = benchmark_screenshot(tool, iterations)
        all_results.extend(results)

        # Cleanup
        tool.close()

    # Compute summaries
    summaries = []
    for tool_name in available_tools:
        for operation in ["navigate", "extract", "screenshot"]:
            for test_case in ["navigation_simple", "extraction_quotes", "screenshot_simple"]:
                summary = compute_summary(all_results, tool_name, operation, test_case)
                if summary.count > 0:
                    summaries.append(summary)

    # Create comparison
    comparison = {}
    for summary in summaries:
        key = f"{summary.operation}_{summary.test_case}"
        if key not in comparison:
            comparison[key] = {}
        comparison[key][summary.tool] = {
            "mean_ms": round(summary.mean_ms, 1),
            "warm_ms": round(summary.warm_mean_ms, 1),
            "tokens": round(summary.avg_tokens),
            "success_rate": round(summary.success_rate * 100, 1),
        }

    # Create report
    report = BrowserBenchmarkReport(
        generated_at=datetime.now().isoformat(),
        iterations=iterations,
        warmup=warmup,
        tools_tested=list(available_tools.keys()),
        test_urls=TEST_URLS,
        results=[asdict(r) for r in all_results],
        summaries=[asdict(s) for s in summaries],
        comparison=comparison,
        notes=[
            "claude-in-chrome MCP can only be tested within Claude Code session",
            "browser-gateway requires installation of the skill daemon",
        ],
    )

    return report


def print_summary(report: BrowserBenchmarkReport) -> None:
    """Print human-readable summary."""
    print("\n" + "=" * 60)
    print("BROWSER BENCHMARK SUMMARY")
    print("=" * 60)

    print(f"\nTools tested: {report.tools_tested}")
    print(f"Iterations: {report.iterations}")
    print()

    # Print comparison table
    print("Performance Comparison:")
    print("-" * 60)
    print(f"{'Operation':<25} {'Tool':<20} {'Mean (ms)':<12} {'Tokens':<10}")
    print("-" * 60)

    for summary in report.summaries:
        s = BrowserBenchmarkSummary(**summary)
        if s.count > 0:
            print(f"{s.operation:<25} {s.tool:<20} {s.mean_ms:>8.0f}ms   ~{s.avg_tokens:>6.0f}")

    print("-" * 60)

    # Notes
    if report.notes:
        print("\nNotes:")
        for note in report.notes:
            print(f"  • {note}")


def main():
    parser = argparse.ArgumentParser(description="Browser Automation Benchmark")
    parser.add_argument("-i", "--iterations", type=int, default=3, help="Iterations per test")
    parser.add_argument("-w", "--warmup", type=int, default=1, help="Warmup iterations")
    parser.add_argument("-t", "--tool", choices=["playwright_mcp", "agent_browser", "browser_gateway"], help="Specific tool to test")
    parser.add_argument("-o", "--output", type=str, help="Output JSON file path")
    args = parser.parse_args()

    tools = [args.tool] if args.tool else None

    report = run_benchmarks(
        iterations=args.iterations,
        warmup=args.warmup,
        tools=tools,
    )

    print_summary(report)

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = REPO_ROOT / "benchmarks" / "results"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"browser_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    print(f"\n📁 Results saved to: {output_path}")


if __name__ == "__main__":
    main()
