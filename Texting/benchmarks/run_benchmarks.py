"""
CLI for running benchmarks and comparing results.
"""
import argparse
import sys
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Texting"))

from benchmarks.bench_indexing import run_all_indexing_benchmarks
from benchmarks.bench_search import run_all_search_benchmarks
from benchmarks.benchmark_runner import BenchmarkConfig
from benchmarks.config import RESULTS_DIR


def compare_results(baseline_file: Path, current_file: Path):
    """Compare two benchmark result files and show regression/improvement."""
    try:
        with open(baseline_file) as f:
            baseline = {r["name"]: r for r in json.load(f)}
    except FileNotFoundError:
        print(f"ERROR: Baseline file not found: {baseline_file}")
        return
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in baseline file: {e}")
        return

    try:
        with open(current_file) as f:
            current = {r["name"]: r for r in json.load(f)}
    except FileNotFoundError:
        print(f"ERROR: Current file not found: {current_file}")
        return
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in current file: {e}")
        return

    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON")
    print("="*80)

    for name in sorted(current.keys()):
        if name not in baseline:
            print(f"\n{name}: NEW (no baseline)")
            continue

        base_time = baseline[name]["elapsed_seconds"]
        curr_time = current[name]["elapsed_seconds"]

        if base_time == 0:
            print(f"\n⚪ {name}")
            print(f"  Baseline: {base_time:.3f}s (zero - skipped)")
            continue

        delta = ((curr_time - base_time) / base_time) * 100
        symbol = "🔴" if delta > 10 else "🟢" if delta < -10 else "⚪"

        print(f"\n{symbol} {name}")
        print(f"  Baseline: {base_time:.3f}s")
        print(f"  Current:  {curr_time:.3f}s")
        print(f"  Change:   {delta:+.1f}%")

        # Show metrics if available
        if "metrics" in current[name] and current[name]["metrics"]:
            print(f"  Metrics: {current[name]['metrics']}")

    print("\n" + "="*80)
    print(f"\n🟢 = Improved (>10% faster)")
    print(f"⚪ = Stable (within 10%)")
    print(f"🔴 = Regressed (>10% slower)")
    print()


def print_validation_report(results: dict) -> None:
    """Print validation results in human-readable format."""
    print("\n=== Validation Report ===\n")
    for tool_name, validation in results.items():
        status = "✓" if validation.overall_success else "✗"
        print(f"{status} {tool_name}: {validation.recommended_action}")
        for stage in validation.stages:
            stage_status = "✓" if stage.success else "✗"
            print(f"  {stage_status} {stage.stage}: {stage.elapsed_ms:.1f}ms")
    print("\n" + "=" * 40)


def load_tool_configs() -> dict:
    """Stub for loading tool configs used by validation."""
    return {}


def validate_all_tools(tool_configs: dict) -> dict:
    """Validate all tools in config (stub returns empty if no configs)."""
    if not tool_configs:
        return {}

    from benchmarks.validator import ToolValidator

    results = {}
    for tool_name, config in tool_configs.items():
        cli_path = config.get("cli_path")
        operations = config.get("operations", [])
        if not cli_path:
            continue
        validator = ToolValidator(Path(cli_path), timeout=config.get("timeout", 30))
        results[tool_name] = validator.validate_tool(operations)
    return results


def main():
    """Run benchmark suites from the command line."""
    parser = argparse.ArgumentParser(description="Run RAG performance benchmarks")
    parser.add_argument(
        "--suite",
        choices=["indexing", "search", "all"],
        default="all",
        help="Which benchmark suite to run"
    )
    parser.add_argument(
        "--compare",
        type=Path,
        help="Compare against baseline results file"
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current results as baseline for future comparisons"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation only, skip benchmarks"
    )
    parser.add_argument(
        "--progressive",
        action="store_true",
        help="Validate before benchmarking, skip invalid tools"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per operation"
    )
    parser.add_argument(
        "--save-debug",
        action="store_true",
        help="Save debug logs for failed operations"
    )

    args = parser.parse_args()

    tool_configs = load_tool_configs()

    # Validation-only mode
    if args.validate_only:
        results = validate_all_tools(tool_configs)
        print_validation_report(results)
        sys.exit(0)

    # Progressive mode (validate then benchmark)
    if args.progressive:
        config = BenchmarkConfig(
            validation_mode=True,
            skip_invalid=True,
            iterations=args.iterations,
            save_debug_logs=args.save_debug,
        )
        results = validate_all_tools(tool_configs)
        print_validation_report(results)
        invalid_tools = [
            name for name, validation in results.items()
            if not validation.overall_success
        ]
        if invalid_tools:
            print(f"Skipping invalid tools: {', '.join(invalid_tools)}")

    # Run benchmarks
    print(f"Running benchmark suite: {args.suite}")
    print(f"Results directory: {RESULTS_DIR}")
    print()

    if args.suite in ["indexing", "all"]:
        print("="*80)
        print("INDEXING BENCHMARKS")
        print("="*80)
        run_all_indexing_benchmarks()

    if args.suite in ["search", "all"]:
        print("\n" + "="*80)
        print("SEARCH BENCHMARKS")
        print("="*80)
        run_all_search_benchmarks()

    # Save baseline if requested
    if args.save_baseline:
        if args.suite == "indexing":
            baseline_file = RESULTS_DIR / "indexing_baseline.json"
            current_file = RESULTS_DIR / "indexing_benchmarks.json"
        elif args.suite == "search":
            baseline_file = RESULTS_DIR / "search_baseline.json"
            current_file = RESULTS_DIR / "search_benchmarks.json"
        else:
            print("\n--save-baseline requires --suite to be 'indexing' or 'search'")
            return

        if current_file.exists():
            import shutil
            shutil.copy(current_file, baseline_file)
            print(f"\n✅ Saved baseline to {baseline_file}")

    # Compare if requested
    if args.compare:
        if args.suite == "indexing":
            current = RESULTS_DIR / "indexing_benchmarks.json"
        elif args.suite == "search":
            current = RESULTS_DIR / "search_benchmarks.json"
        else:
            print("\n--compare requires --suite to be 'indexing' or 'search'")
            return

        if current.exists():
            compare_results(args.compare, current)
        else:
            print(f"ERROR: No current results found at {current}")


if __name__ == "__main__":
    main()
