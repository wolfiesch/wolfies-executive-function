#!/usr/bin/env python3
"""
Competitor benchmark harness for iMessage tooling.

Goals:
1) Compare startup/read-only operations across tools.
2) Avoid side-effectful commands (send/open) by default.
3) Fail fast when a command is unsupported or hangs.
4) Provide real-time telemetry and support chunked/resumable runs.
"""

from __future__ import annotations

import argparse
import json
import shlex
import os
import shutil
import subprocess
import statistics
import time
import math
import select
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CLI = REPO_ROOT / "gateway" / "imessage_client.py"
MAX_READINESS_BUFFER_SIZE = 65536
BYTES_PER_TOKEN_ESTIMATE = 4.0

def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class CommandSpec:
    label: str
    cmd: str
    timeout_s: int = 20
    requires_contact: bool = False
    requires_imsg_chat_id: bool = False
    read_only: bool = True
    ready_regex: Optional[str] = None


@dataclass
class CommandResult:
    label: str
    cmd: str
    read_only: bool
    iterations: int
    mean_ms: Optional[float]
    median_ms: Optional[float]
    p95_ms: Optional[float]
    min_ms: Optional[float]
    max_ms: Optional[float]
    std_dev_ms: Optional[float]
    success_rate: float
    stdout_bytes_mean: Optional[float] = None
    approx_tokens_mean: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ToolResult:
    name: str
    tool_type: str
    commands: List[CommandResult] = field(default_factory=list)


@dataclass
class SuiteResult:
    suite_name: str
    timestamp: str
    tool_results: List[ToolResult]
    metadata: dict


def _run_command(cmd: List[str], timeout_s: int) -> tuple[float, bool, str]:
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, "TIMEOUT"
    except Exception as exc:  # pragma: no cover - defensive
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, str(exc)

    elapsed = (time.perf_counter() - start) * 1000
    if result.returncode != 0:
        return elapsed, False, (result.stderr or "").strip() or "FAILED"
    return elapsed, True, ""

def _run_command_capture(cmd: List[str], timeout_s: int) -> tuple[float, bool, str, int]:
    """Run a command capturing stdout so we can estimate LLM-facing output cost."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            timeout=timeout_s,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, "TIMEOUT", 0
    except Exception as exc:  # pragma: no cover - defensive
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, False, str(exc), 0

    elapsed = (time.perf_counter() - start) * 1000
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="ignore").strip() or "FAILED"
        return elapsed, False, err, len(result.stdout or b"")
    return elapsed, True, "", len(result.stdout or b"")

def _run_command_until_ready(
    cmd: List[str],
    timeout_s: int,
    ready_regex: str,
) -> tuple[float, bool, str, int]:
    """
    Run a long-lived command (e.g., MCP stdio server) until it prints a readiness marker.

    We then terminate it and return the time-to-ready. This avoids benchmark runs hanging
    forever for servers that never exit on --help/--version.
    """
    start = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        cwd=str(REPO_ROOT),
    )
    stdout_fd = proc.stdout.fileno() if proc.stdout is not None else None
    stderr_fd = proc.stderr.fileno() if proc.stderr is not None else None
    fds = [fd for fd in (stdout_fd, stderr_fd) if fd is not None]

    captured: bytearray = bytearray()
    total_bytes = 0
    ready_re = re.compile(ready_regex, flags=re.IGNORECASE | re.DOTALL)
    deadline = time.time() + timeout_s

    def _cleanup() -> None:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    try:
        while True:
            if time.time() >= deadline:
                _cleanup()
                elapsed = (time.perf_counter() - start) * 1000
                return elapsed, False, "TIMEOUT", total_bytes

            rc = proc.poll()
            if rc is not None:
                # Process exited before readiness marker; return any stderr as clue.
                try:
                    out = (proc.stdout.read() if proc.stdout else b"") + (proc.stderr.read() if proc.stderr else b"")
                except Exception:
                    out = b""
                total_bytes += len(out)
                captured.extend(out[:4096])
                elapsed = (time.perf_counter() - start) * 1000
                err_preview = captured.decode("utf-8", errors="ignore").strip()
                return elapsed, False, err_preview or f"EXITED({rc})", total_bytes

            if not fds:
                time.sleep(0.05)
                continue

            r, _, _ = select.select(fds, [], [], 0.1)
            for fd in r:
                try:
                    chunk = os.read(fd, 4096)
                except Exception:
                    chunk = b""
                if not chunk:
                    continue
                total_bytes += len(chunk)
                captured.extend(chunk)
                # Keep buffer bounded; we only need to detect readiness.
                if len(captured) > MAX_READINESS_BUFFER_SIZE:
                    captured = captured[-MAX_READINESS_BUFFER_SIZE:]
                # Strip ANSI escape sequences before matching.
                text = captured.decode("utf-8", errors="ignore")
                # ANSI CSI sequences: ESC [ ... <final>
                text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
                if ready_re.search(text):
                    elapsed = (time.perf_counter() - start) * 1000
                    _cleanup()
                    return elapsed, True, "", total_bytes
    finally:
        _cleanup()


def _percentile(sorted_values: List[float], p: float) -> Optional[float]:
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


def _benchmark_command(spec: CommandSpec, iterations: int) -> CommandResult:
    return _benchmark_command_with_display(spec, iterations, cmd_display=None)


def _benchmark_command_with_display(
    spec: CommandSpec,
    iterations: int,
    *,
    cmd_display: Optional[str],
) -> CommandResult:
    cmd = shlex.split(spec.cmd)
    timings: List[float] = []
    successes = 0
    error: Optional[str] = None
    stdout_sizes: List[int] = []
    display = cmd_display if cmd_display is not None else spec.cmd

    # First run is a validation; if it fails, skip to avoid wasted time.
    print(f"[{_ts()}]    iter 1/{iterations} ...", end=" ", flush=True)
    if spec.ready_regex:
        elapsed, ok, err, stdout_len = _run_command_until_ready(cmd, spec.timeout_s, spec.ready_regex)
    else:
        elapsed, ok, err, stdout_len = _run_command_capture(cmd, spec.timeout_s)
    timings.append(elapsed)
    if ok:
        successes += 1
        stdout_sizes.append(stdout_len)
        print(f"ok ({elapsed:.2f}ms)")
    else:
        error = err
        print(f"FAIL ({elapsed:.2f}ms) {err}")
        return CommandResult(
            label=spec.label,
            cmd=display,
            read_only=spec.read_only,
            iterations=1,
            mean_ms=elapsed,
            median_ms=elapsed,
            p95_ms=elapsed,
            min_ms=elapsed,
            max_ms=elapsed,
            std_dev_ms=0.0,
            success_rate=0.0,
            error=error,
        )

    for _ in range(iterations - 1):
        print(f"[{_ts()}]    iter {len(timings)+1}/{iterations} ...", end=" ", flush=True)
        if spec.ready_regex:
            elapsed, ok, err, stdout_len = _run_command_until_ready(cmd, spec.timeout_s, spec.ready_regex)
        else:
            elapsed, ok, err, stdout_len = _run_command_capture(cmd, spec.timeout_s)
        timings.append(elapsed)
        if ok:
            successes += 1
            stdout_sizes.append(stdout_len)
            print(f"ok ({elapsed:.2f}ms)")
        else:
            error = err
            print(f"FAIL ({elapsed:.2f}ms) {err}")
            break

    success_rate = (successes / len(timings)) * 100 if timings else 0.0
    mean_ms = statistics.mean(timings) if timings else None
    median_ms = statistics.median(timings) if timings else None
    p95_ms = _percentile(sorted(timings), 95.0) if timings else None
    min_ms = min(timings) if timings else None
    max_ms = max(timings) if timings else None
    std_dev_ms = statistics.stdev(timings) if len(timings) > 1 else 0.0
    stdout_bytes_mean = statistics.mean(stdout_sizes) if stdout_sizes else None
    approx_tokens_mean = math.ceil(stdout_bytes_mean / BYTES_PER_TOKEN_ESTIMATE) if stdout_bytes_mean is not None else None

    return CommandResult(
        label=spec.label,
        cmd=display,
        read_only=spec.read_only,
        iterations=len(timings),
        mean_ms=mean_ms,
        median_ms=median_ms,
        p95_ms=p95_ms,
        min_ms=min_ms,
        max_ms=max_ms,
        std_dev_ms=std_dev_ms,
        success_rate=success_rate,
        stdout_bytes_mean=stdout_bytes_mean,
        approx_tokens_mean=approx_tokens_mean,
        error=error,
    )


def _tool_specs_tier_a(include_rw: bool, send_to: Optional[str]) -> List[tuple[str, str, List[CommandSpec]]]:
    send_specs: List[CommandSpec] = []
    if include_rw:
        if not send_to:
            raise ValueError("include_rw requires send_to")
        send_specs = [
            CommandSpec(
                "send_message",
                f"python3 {GATEWAY_CLI} send-by-phone {{send_to}} 'benchmark ping (ignore)'",
                25,
                read_only=False,
            )
        ]

    return [
        (
            "Wolfies iMessage Gateway (CLI)",
            "cli",
            [
                CommandSpec("startup_help", f"python3 {GATEWAY_CLI} --help", 10),
                CommandSpec("recent_10", f"python3 {GATEWAY_CLI} recent --limit 10 --json", 20),
                CommandSpec("recent_10_minimal", f"python3 {GATEWAY_CLI} recent --limit 10 --json --minimal", 20),
                CommandSpec("unread", f"python3 {GATEWAY_CLI} unread --json", 20),
                CommandSpec("unread_minimal", f"python3 {GATEWAY_CLI} unread --json --minimal", 20),
                CommandSpec("search_http_global", f"python3 {GATEWAY_CLI} text-search http --limit 20 --json", 25),
                CommandSpec(
                    "search_http_global_minimal",
                    f"python3 {GATEWAY_CLI} text-search http --limit 20 --json --minimal",
                    25,
                ),
                CommandSpec(
                    "search_http_contact",
                    f"python3 {GATEWAY_CLI} find {{contact}} --query http --limit 20 --json",
                    25,
                    requires_contact=True,
                ),
                CommandSpec(
                    "bundle_compact",
                    f"python3 {GATEWAY_CLI} bundle --json --compact --unread-limit 20 --recent-limit 10 --query http --search-limit 20 --max-text-chars 120",
                    30,
                ),
                CommandSpec(
                    "bundle_minimal",
                    f"python3 {GATEWAY_CLI} bundle --json --minimal --unread-limit 20 --recent-limit 10 --query http --search-limit 20",
                    30,
                ),
            ]
            + send_specs,
        ),
        (
            "jean-claude (iMessage)",
            "cli",
            [
                CommandSpec("startup_help", "jean-claude imessage --help", 10),
                CommandSpec("chats", "jean-claude imessage chats", 20),
                CommandSpec("unread", "jean-claude imessage unread", 20),
                CommandSpec("search_http", "jean-claude imessage search http", 25),
                CommandSpec(
                    "history_contact_10",
                    "jean-claude imessage history --name {contact} -n 10",
                    25,
                    requires_contact=True,
                ),
            ],
        ),
        (
            "imessage-exporter",
            "cli",
            [
                CommandSpec("startup_help", "imessage-exporter --help", 10),
                CommandSpec("list_chats", "imessage-exporter --list-chats", 20),
                CommandSpec("search_http", "imessage-exporter --search http", 25),
            ],
        ),
        (
            "imsg (Messages.app CLI) [steipete/imsg]",
            "cli",
            [
                CommandSpec("startup_help", "benchmarks/vendor/imsg/bin/imsg --help", 10),
                CommandSpec("chats_10_json", "benchmarks/vendor/imsg/bin/imsg chats --limit 10 --json", 15),
                CommandSpec(
                    "history_10_json",
                    "benchmarks/vendor/imsg/bin/imsg history --chat-id {imsg_chat_id} --limit 10 --json",
                    20,
                    requires_imsg_chat_id=True,
                ),
            ],
        ),
        (
            "messages (CLI/MCP) [cardmagic/messages]",
            "cli",
            [
                CommandSpec("startup_help", "messages --help", 10),
                CommandSpec("recent_10", "messages recent --limit 10", 20),
                CommandSpec("search_http", "messages search http --limit 10 --context 0", 25),
            ],
        ),
        (
            "mcp-server-imessage (import)",
            "import",
            [
                CommandSpec("import_module", "python3 -c \"import mcp_server_imessage; print('ok')\"", 10),
            ],
        ),
    ]

def _tool_specs_extended() -> List[tuple[str, str, List[CommandSpec]]]:
    """
    Additional candidates discovered via GitHub/PyPI/Homebrew/npm.

    Many are not installed by default. The runner will skip missing binaries quickly,
    recording a SKIPPED reason so the run stays visible and bounded.
    """
    return [
        (
            "imsg (Messages.app CLI) [steipete/imsg]",
            "cli",
            [
                CommandSpec("startup_help", "benchmarks/vendor/imsg/bin/imsg --help", 10),
                CommandSpec("chats_10_json", "benchmarks/vendor/imsg/bin/imsg chats --limit 10 --json", 15),
                CommandSpec(
                    "history_10_json",
                    "benchmarks/vendor/imsg/bin/imsg history --chat-id {imsg_chat_id} --limit 10 --json",
                    20,
                    requires_imsg_chat_id=True,
                ),
            ],
        ),
        (
            "messages (CLI/MCP) [cardmagic/messages]",
            "cli",
            [
                CommandSpec("startup_help", "messages --help", 10),
            ],
        ),
        (
            "OSX-Messages-Exporter [cfinke/OSX-Messages-Exporter]",
            "cli",
            [
                CommandSpec(
                    "startup_help",
                    "php benchmarks/vendor/osx-messages-exporter/messages-exporter.php --help",
                    10,
                ),
            ],
        ),
        (
            "imessage-ruby (send) [Homebrew: imessage-ruby]",
            "cli",
            [
                CommandSpec("startup_help", "imessage --help", 10, read_only=False),
            ],
        ),
        (
            "npx MCP: @iflow-mcp/imessage-mcp-server",
            "cli",
            [
                CommandSpec(
                    "startup_ready",
                    "npx {npx_flags} @iflow-mcp/imessage-mcp-server --help",
                    60,
                    ready_regex=r"imessage.*mcp.*server.*started",
                ),
            ],
        ),
        (
            "npx MCP: @foxychat-mcp/apple-imessages",
            "cli",
            [
                CommandSpec(
                    "startup_ready",
                    "npx {npx_flags} @foxychat-mcp/apple-imessages --help",
                    60,
                    ready_regex=r"imessage.*mcp.*server.*running.*stdio",
                ),
            ],
        ),
        (
            "npx (CLI/MCP): @cardmagic/messages",
            "cli",
            [
                CommandSpec("startup_help", "npx {npx_flags} @cardmagic/messages --help", 15),
            ],
        ),
    ]


def _tool_specs_tier_b() -> List[tuple[str, str, List[CommandSpec]]]:
    return [
        (
            "imessagedb",
            "import",
            [
                CommandSpec("import_module", "python3 -c \"import imessagedb; print('ok')\"", 10),
            ],
        ),
        (
            "imessage-reader",
            "import",
            [
                CommandSpec("import_module", "python3 -c \"import imessage_reader; print('ok')\"", 10),
            ],
        ),
        (
            "imessage-monitor",
            "import",
            [
                CommandSpec("import_module", "python3 -c \"import imessage_monitor; print('ok')\"", 10),
            ],
        ),
        (
            "imessage-conversation-analyzer",
            "cli",
            [
                CommandSpec("startup_help", "ica --help", 10),
            ],
        ),
        (
            "imessage-wrapped",
            "cli",
            [
                CommandSpec("startup_help", "imexport --help", 10),
            ],
        ),
        (
            "imessage-year-wrapped",
            "cli",
            [
                CommandSpec("startup_help", "imessage-wrapped --help", 10),
            ],
        ),
    ]


def _get_gateway_sample_contact() -> Optional[str]:
    try:
        proc = subprocess.run(
            ["python3", str(GATEWAY_CLI), "contacts", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        contacts = json.loads(proc.stdout)
    except Exception:
        return None
    if not contacts:
        return None
    return contacts[0].get("name")

def _get_imsg_sample_chat_id(imsg_bin: str) -> Optional[str]:
    """
    Pick a chat id for steipete/imsg benchmarks.

    imsg emits one JSON object per line; we take the first line from:
      imsg chats --limit 1 --json
    """
    try:
        proc = subprocess.run(
            [imsg_bin, "chats", "--limit", "1", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return None
    try:
        obj = json.loads(line[0])
    except Exception:
        return None
    chat_id = obj.get("id")
    if chat_id is None:
        return None
    return str(chat_id)


def _load_completed(output_path: Optional[str]) -> set[tuple[str, str]]:
    if not output_path:
        return set()
    try:
        data = json.loads(Path(output_path).read_text())
    except Exception:
        return set()
    completed: set[tuple[str, str]] = set()
    for tool in data.get("tool_results") or []:
        tool_name = tool.get("name") or ""
        for cmd in tool.get("commands") or []:
            label = cmd.get("label") or ""
            iterations = cmd.get("iterations") or 0
            success_rate = cmd.get("success_rate") or 0.0
            error = (cmd.get("error") or "")
            # Only treat a command as completed if it succeeded (100%) or was intentionally skipped.
            # Failures (e.g. TIMEOUT) should remain eligible for retry on resume.
            if error.startswith("SKIPPED"):
                completed.add((tool_name, label))
                continue
            if iterations > 0 and success_rate == 100.0 and not error:
                completed.add((tool_name, label))
    return completed


def _write_checkpoint(output_path: Optional[str], payload: dict) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def run_suite(
    suite_name: str,
    iterations: int,
    tier: str,
    *,
    include_rw: bool,
    send_to: Optional[str],
    allow_npx: bool,
    npx_download: bool,
    npx_timeout_s: int,
    output_path: Optional[str],
    resume: bool,
    tool_filter: Optional[str],
    max_tools: Optional[int],
) -> SuiteResult:
    if tier == "a":
        specs = _tool_specs_tier_a(include_rw=include_rw, send_to=send_to)
    elif tier == "b":
        specs = _tool_specs_tier_b()
    elif tier == "extended":
        specs = _tool_specs_extended()
    else:
        specs = _tool_specs_tier_a(include_rw=include_rw, send_to=send_to) + _tool_specs_tier_b() + _tool_specs_extended()

    tool_results: List[ToolResult] = []
    sample_contact = _get_gateway_sample_contact()
    imsg_chat_id = _get_imsg_sample_chat_id(str(REPO_ROOT / "benchmarks/vendor/imsg/bin/imsg"))
    completed = _load_completed(output_path) if resume else set()

    if tool_filter:
        specs = [(n, t, c) for (n, t, c) in specs if tool_filter.lower() in n.lower()]
    if max_tools is not None:
        specs = specs[: max(0, max_tools)]

    # Stream checkpoints as we go so long runs remain observable.
    suite = SuiteResult(
        suite_name=suite_name,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        tool_results=tool_results,
        metadata={
            "iterations": iterations,
            "python_version": f"{time.strftime('%Y-%m-%d')} (py {subprocess.check_output(['python3', '-V']).decode().strip()})",
            "tier": tier,
            "include_rw": include_rw,
            "allow_npx": allow_npx,
            "npx_download": npx_download,
            "npx_timeout_s": npx_timeout_s,
            "resume": resume,
            "tool_filter": tool_filter,
        },
    )
    payload = {
        "suite_name": suite.suite_name,
        "timestamp": suite.timestamp,
        "metadata": suite.metadata,
        "tool_results": [asdict(r) for r in suite.tool_results],
    }
    _write_checkpoint(output_path, payload)

    for name, tool_type, commands in specs:
        print(f"\n== {name} ==")
        tool_result = ToolResult(name=name, tool_type=tool_type)

        # Skip missing non-Python binaries up front to keep runs bounded.
        if commands:
            first_argv = shlex.split(commands[0].cmd)
            if first_argv and first_argv[0] == "npx" and not suite.metadata.get("allow_npx"):
                for command in commands:
                    tool_result.commands.append(
                        CommandResult(
                            label=command.label,
                            cmd=command.cmd,
                            read_only=command.read_only,
                            iterations=0,
                            mean_ms=None,
                            median_ms=None,
                            p95_ms=None,
                            min_ms=None,
                            max_ms=None,
                            std_dev_ms=None,
                            success_rate=0.0,
                            stdout_bytes_mean=None,
                            approx_tokens_mean=None,
                            error="SKIPPED (npx disabled; enable with --allow-npx)",
                        )
                    )
                print("  -> skipped (npx disabled)")
                tool_results.append(tool_result)
                payload["tool_results"] = [asdict(r) for r in suite.tool_results]
                _write_checkpoint(output_path, payload)
                continue

            if first_argv and first_argv[0] not in ("python3", "python", "npx"):
                binary = first_argv[0]
                resolved_ok = False
                if shutil.which(binary) is not None:
                    resolved_ok = True
                else:
                    # If the command is a relative path, resolve it relative to REPO_ROOT,
                    # since we run all commands with cwd=REPO_ROOT.
                    try:
                        p = Path(binary)
                        if not p.is_absolute():
                            p = (REPO_ROOT / p).resolve()
                        resolved_ok = p.exists() and os.access(str(p), os.X_OK)
                    except Exception:
                        resolved_ok = False

                if not resolved_ok:
                    for command in commands:
                        tool_result.commands.append(
                            CommandResult(
                                label=command.label,
                                cmd=command.cmd,
                                read_only=command.read_only,
                                iterations=0,
                                mean_ms=None,
                                median_ms=None,
                                p95_ms=None,
                                min_ms=None,
                                max_ms=None,
                                std_dev_ms=None,
                                success_rate=0.0,
                                stdout_bytes_mean=None,
                                approx_tokens_mean=None,
                                error=f"SKIPPED (not installed: {binary})",
                            )
                        )
                    print(f"  -> skipped (not installed: {binary})")
                    tool_results.append(tool_result)
                    payload["tool_results"] = [asdict(r) for r in suite.tool_results]
                    _write_checkpoint(output_path, payload)
                    continue

        for command in commands:
            if not include_rw and not command.read_only:
                result = CommandResult(
                    label=command.label,
                    cmd=command.cmd,
                    read_only=command.read_only,
                    iterations=0,
                    mean_ms=None,
                    median_ms=None,
                    p95_ms=None,
                    min_ms=None,
                    max_ms=None,
                    std_dev_ms=None,
                    success_rate=0.0,
                    stdout_bytes_mean=None,
                    approx_tokens_mean=None,
                    error="SKIPPED (rw disabled)",
                )
                tool_result.commands.append(result)
                print(f"  -> {command.label} (skipped: rw disabled)")
                continue

            cmd = command.cmd
            if command.requires_contact:
                if not sample_contact:
                    result = CommandResult(
                        label=command.label,
                        cmd=cmd,
                        read_only=command.read_only,
                        iterations=0,
                        mean_ms=None,
                        median_ms=None,
                        p95_ms=None,
                        min_ms=None,
                        max_ms=None,
                        std_dev_ms=None,
                        success_rate=0.0,
                        stdout_bytes_mean=None,
                        approx_tokens_mean=None,
                        error="SKIPPED (no sample contact)",
                    )
                    tool_result.commands.append(result)
                    print(f"  -> {command.label} (skipped: no sample contact)")
                    continue
                cmd = cmd.replace("{contact}", shlex.quote(sample_contact))

            if command.requires_imsg_chat_id:
                if not imsg_chat_id:
                    result = CommandResult(
                        label=command.label,
                        cmd=cmd,
                        read_only=command.read_only,
                        iterations=0,
                        mean_ms=None,
                        median_ms=None,
                        p95_ms=None,
                        min_ms=None,
                        max_ms=None,
                        std_dev_ms=None,
                        success_rate=0.0,
                        stdout_bytes_mean=None,
                        approx_tokens_mean=None,
                        error="SKIPPED (no imsg chat id)",
                    )
                    tool_result.commands.append(result)
                    print(f"  -> {command.label} (skipped: no imsg chat id)")
                    continue
                cmd = cmd.replace("{imsg_chat_id}", shlex.quote(imsg_chat_id))

            if "{npx_flags}" in cmd:
                if not allow_npx:
                    # Kept for robustness; npx-disabled tools are already skipped earlier.
                    cmd = cmd.replace("{npx_flags}", "--no-install")
                else:
                    cmd = cmd.replace("{npx_flags}", "--yes" if npx_download else "--no-install")

            cmd_run = cmd
            cmd_display = cmd
            if "{send_to}" in cmd:
                if not send_to:
                    result = CommandResult(
                        label=command.label,
                        cmd=command.cmd,
                        read_only=command.read_only,
                        iterations=0,
                        mean_ms=None,
                        median_ms=None,
                        p95_ms=None,
                        min_ms=None,
                        max_ms=None,
                        std_dev_ms=None,
                        success_rate=0.0,
                        stdout_bytes_mean=None,
                        approx_tokens_mean=None,
                        error="SKIPPED (missing send target)",
                    )
                    tool_result.commands.append(result)
                    print(f"  -> {command.label} (skipped: missing send target)")
                    continue
                cmd_run = cmd.replace("{send_to}", shlex.quote(send_to))
                cmd_display = cmd  # keep placeholder to avoid leaking phone numbers into output artifacts

            print(f"  -> {command.label} ({cmd})")
            if resume and (name, command.label) in completed:
                result = CommandResult(
                    label=command.label,
                    cmd=cmd,
                    read_only=command.read_only,
                    iterations=0,
                    mean_ms=None,
                    median_ms=None,
                    p95_ms=None,
                    min_ms=None,
                    max_ms=None,
                    std_dev_ms=None,
                    success_rate=0.0,
                    stdout_bytes_mean=None,
                    approx_tokens_mean=None,
                    error="SKIPPED (already completed)",
                )
                tool_result.commands.append(result)
                print(f"     skipped | already completed")
                continue

            spec = CommandSpec(
                label=command.label,
                cmd=cmd_run,
                timeout_s=npx_timeout_s if shlex.split(cmd_run)[:1] == ["npx"] else command.timeout_s,
                requires_contact=command.requires_contact,
                read_only=command.read_only,
                ready_regex=command.ready_regex,
            )
            result = _benchmark_command_with_display(spec, iterations=iterations, cmd_display=cmd_display)
            tool_result.commands.append(result)
            status = "ok" if result.success_rate == 100 else "fail"
            mean_display = f"{result.mean_ms:.2f}ms" if result.mean_ms is not None else "n/a"
            rw = "RO" if result.read_only else "R/W"
            print(f"     {status} | {mean_display} | {result.success_rate:.0f}% | {rw}")
            if result.error:
                print(f"     error: {result.error}")

            # Checkpoint after every command for maximum visibility/resume-ability.
            payload["tool_results"] = [asdict(r) for r in suite.tool_results] + [asdict(tool_result)]
            _write_checkpoint(output_path, payload)
        tool_results.append(tool_result)

        payload["tool_results"] = [asdict(r) for r in suite.tool_results]
        _write_checkpoint(output_path, payload)

    return suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Competitor benchmark harness")
    parser.add_argument("--tier", choices=["a", "b", "extended", "all"], default="a")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", "-o", default=None, help="Write/stream JSON results to file")
    parser.add_argument("--resume", action="store_true", help="Resume a previous run from --output")
    parser.add_argument("--tool-filter", default=None, help="Only run tools whose name contains this substring")
    parser.add_argument("--max-tools", type=int, default=None, help="Only run the first N matched tools")
    parser.add_argument(
        "--allow-npx",
        action="store_true",
        help="Allow npx-based competitors (downloads on first run; can be slow).",
    )
    parser.add_argument(
        "--npx-download",
        action="store_true",
        help="If set, allow npx to download packages (uses 'npx --yes'). Default is no-download mode ('npx --no-install').",
    )
    parser.add_argument(
        "--npx-timeout",
        type=int,
        default=15,
        help="Timeout in seconds for npx commands (per iteration).",
    )
    parser.add_argument(
        "--include-rw",
        action="store_true",
        help="Include R/W benchmarks (send). Requires IMESSAGE_BENCH_SEND_TO env var.",
    )
    args = parser.parse_args()

    # Preflight: ensure our own gateway can read chat.db so we fail fast (no hours-long silent run).
    preflight = subprocess.run(
        ["python3", str(GATEWAY_CLI), "recent", "--limit", "1", "--json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        cwd=str(REPO_ROOT),
    )
    if preflight.returncode != 0:
        msg = (preflight.stderr or "").strip()
        print(f"[{_ts()}] Preflight failed: gateway cannot read chat.db.")
        if msg:
            print(msg)
        print("Fix: grant Full Disk Access to your terminal and retry.")
        return 2

    send_to = None
    if args.include_rw:
        send_to = os.environ.get("IMESSAGE_BENCH_SEND_TO")
        if not send_to:
            print("Refusing to run R/W benchmarks: set IMESSAGE_BENCH_SEND_TO to a test number.")
            return 2

    suite = run_suite(
        suite_name=f"competitor_tier_{args.tier}",
        iterations=args.iterations,
        tier=args.tier,
        include_rw=args.include_rw,
        send_to=send_to,
        allow_npx=args.allow_npx,
        npx_download=args.npx_download,
        npx_timeout_s=args.npx_timeout,
        output_path=args.output,
        resume=args.resume,
        tool_filter=args.tool_filter,
        max_tools=args.max_tools,
    )
    payload = {
        "suite_name": suite.suite_name,
        "timestamp": suite.timestamp,
        "metadata": suite.metadata,
        "tool_results": [asdict(r) for r in suite.tool_results],
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"\nSaved results to {args.output}")
    else:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
