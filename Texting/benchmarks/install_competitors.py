#!/usr/bin/env python3
"""
Install competitor tools for maximalist benchmarking.

Why this exists:
- End-to-end tool performance includes installability and runtime reliability.
- Some competitors are Python (pip), some are Node (npm/npx).
- We want to preinstall Node packages so benchmarks can run in **no-download**
  mode (avoids first-run npx timeouts dominating results).

This script is intentionally conservative:
- Installs in small, observable steps
- Uses per-package timeouts
- Records a JSON report of successes/failures (so "homework" is auditable)

Typical usage:
  python3 Texting/benchmarks/install_competitors.py --from-discovery Texting/benchmarks/results/discovery_*.json
  python3 Texting/benchmarks/install_competitors.py --pip --npm --max 5
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISCOVERY_GLOB = REPO_ROOT / "benchmarks" / "results" / "discovery_*.json"


@dataclass
class InstallResult:
    """One package installation attempt."""

    manager: str  # pip|npm
    name: str
    ok: bool
    elapsed_ms: float
    command: list[str]
    error: Optional[str] = None
    stdout_tail: Optional[str] = None
    stderr_tail: Optional[str] = None


def _tail(data: bytes, limit: int = 4000) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", errors="ignore")
    if len(text) <= limit:
        return text
    return text[-limit:]


def _run(cmd: list[str], timeout_s: int) -> InstallResult:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            cwd=str(REPO_ROOT),
            text=False,
        )
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return InstallResult(
            manager="",
            name="",
            ok=False,
            elapsed_ms=elapsed_ms,
            command=cmd,
            error="TIMEOUT",
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    ok = proc.returncode == 0
    err = None if ok else f"exit={proc.returncode}"
    return InstallResult(
        manager="",
        name="",
        ok=ok,
        elapsed_ms=elapsed_ms,
        command=cmd,
        error=err,
        stdout_tail=_tail(proc.stdout),
        stderr_tail=_tail(proc.stderr),
    )


def _latest_discovery(path_or_glob: Optional[str]) -> Optional[Path]:
    if not path_or_glob:
        candidates = sorted(DEFAULT_DISCOVERY_GLOB.parent.glob(DEFAULT_DISCOVERY_GLOB.name))
        return candidates[-1] if candidates else None
    p = Path(path_or_glob)
    if p.exists():
        return p
    # Treat as glob relative to repo root
    matches = sorted((REPO_ROOT / path_or_glob).parent.glob(Path(path_or_glob).name))
    return matches[-1] if matches else None


def _load_discovery(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _select_pypi(discovery: dict[str, Any], *, min_score: int) -> list[str]:
    results = discovery.get("results", {}).get("pypi") or []
    names: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        score = item.get("score") or 0
        if isinstance(name, str) and int(score) >= min_score:
            names.append(name)
    # Stable order: high-score first, then alphabetical.
    def key(n: str) -> tuple[int, str]:
        score = 0
        for item in results:
            if isinstance(item, dict) and item.get("name") == n:
                score = int(item.get("score") or 0)
                break
        return (-score, n.lower())

    return sorted(set(names), key=key)


def _select_npm(discovery: dict[str, Any]) -> list[str]:
    """
    Pick a conservative shortlist from npm discovery results.

    We avoid installing hundreds of unrelated packages. This selects high-signal
    names that look like iMessage/Messages MCP servers or CLIs.
    """
    results = discovery.get("results", {}).get("npm") or []
    out: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("package") or item.get("packageName")
        if not isinstance(name, str):
            continue
        lowered = name.lower()
        if "mcp" in lowered and ("imessage" in lowered or "messages" in lowered or "apple-imessages" in lowered):
            out.add(name)
        if lowered in {
            "@iflow-mcp/imessage-mcp-server",
            "@foxychat-mcp/apple-imessages",
            "@cardmagic/messages",
        }:
            out.add(name)
    return sorted(out, key=lambda s: s.lower())


def _pip_install(python: str, pkg: str, timeout_s: int) -> InstallResult:
    cmd = [
        python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--disable-pip-version-check",
        pkg,
    ]
    r = _run(cmd, timeout_s=timeout_s)
    r.manager = "pip"
    r.name = pkg
    return r


def _npm_install(pkg: str, timeout_s: int) -> InstallResult:
    cmd = ["npm", "install", "-g", pkg]
    r = _run(cmd, timeout_s=timeout_s)
    r.manager = "npm"
    r.name = pkg
    return r


def main() -> int:
    parser = argparse.ArgumentParser(description="Install competitor tools for benchmarks (pip + npm)")
    parser.add_argument("--from-discovery", default=None, help="Path (or glob) to discovery JSON; defaults to latest in benchmarks/results/")
    parser.add_argument("--python", default="python3", help="Python executable to use for pip installs (default: python3)")
    parser.add_argument("--pip", action="store_true", help="Install PyPI packages from discovery")
    parser.add_argument("--npm", action="store_true", help="Install npm packages from discovery shortlist")
    parser.add_argument("--min-score", type=int, default=12, help="Min PyPI discovery score to install (default: 12)")
    parser.add_argument("--timeout", type=int, default=600, help="Per-package install timeout seconds (default: 600)")
    parser.add_argument("--max", type=int, default=None, help="Only install the first N packages (for batching)")
    parser.add_argument("--out", default="Texting/benchmarks/results/install_report.json", help="Write JSON report to this path")
    args = parser.parse_args()

    if not args.pip and not args.npm:
        # Default to maximalist mode when flags are omitted.
        args.pip = True
        args.npm = True

    discovery_path = _latest_discovery(args.from_discovery)
    if not discovery_path:
        raise SystemExit("No discovery JSON found. Run discover_competitors.py first.")
    discovery = _load_discovery(discovery_path)

    pypi_pkgs = _select_pypi(discovery, min_score=args.min_score) if args.pip else []
    npm_pkgs = _select_npm(discovery) if args.npm else []

    install_plan: list[tuple[str, str]] = [("pip", p) for p in pypi_pkgs] + [("npm", n) for n in npm_pkgs]
    if args.max is not None:
        install_plan = install_plan[: max(0, int(args.max))]

    results: list[InstallResult] = []
    print(f"Discovery: {discovery_path}")
    print(f"Plan: {len(install_plan)} installs (pip={len(pypi_pkgs)}, npm={len(npm_pkgs)})")
    if args.max is not None:
        print(f"Batch cap: --max {args.max}")

    for idx, (mgr, name) in enumerate(install_plan, start=1):
        print(f"\n[{idx}/{len(install_plan)}] {mgr} install {name}")
        if mgr == "pip":
            res = _pip_install(args.python, name, timeout_s=args.timeout)
        else:
            res = _npm_install(name, timeout_s=args.timeout)
        results.append(res)
        status = "ok" if res.ok else "FAIL"
        print(f"  {status} ({res.elapsed_ms:.0f}ms)")
        if not res.ok and res.error:
            print(f"  error: {res.error}")

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "discovery": str(discovery_path),
        "min_score": args.min_score,
        "timeout_s": args.timeout,
        "results": [asdict(r) for r in results],
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote report: {out_path}")

    failures = [r for r in results if not r.ok]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

