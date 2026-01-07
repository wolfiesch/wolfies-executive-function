#!/usr/bin/env python3
"""
Measure MCP stdio tool-call latency for external servers (including npx-based ones).

We intentionally do NOT persist tool outputs (which may contain personal data).
We only store:
- timing metrics (initialize, list_tools, call_tool)
- success/error markers
- output byte and token estimates

This script is built for visibility and safety:
- preflight check for local chat.db readability (Full Disk Access)
- bounded timeouts for every phase
- streaming checkpoints to an output JSON file
- resume support (skip completed successful iterations)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import select
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple

from mcp import types


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CLI = REPO_ROOT / "gateway" / "imessage_client.py"
COMPETITOR_VENV_BIN = REPO_ROOT / "benchmarks" / ".venv_competitors" / "bin"
SAFE_PLACEHOLDER_PHONE = "+10000000000"
BYTES_PER_TOKEN_ESTIMATE = 4.0


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _approx_tokens_from_bytes(byte_count: int | None) -> int | None:
    if byte_count is None:
        return None
    return int(math.ceil(byte_count / BYTES_PER_TOKEN_ESTIMATE))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _preflight_chat_db() -> Tuple[bool, str]:
    """
    Fail fast if Full Disk Access is missing (common root cause of 'silent failure').
    """
    proc = subprocess.run(
        ["python3", str(GATEWAY_CLI), "recent", "--limit", "1", "--json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode == 0:
        return True, ""
    return False, (proc.stderr or "").strip() or "gateway preflight failed"


@dataclass
class McpServerSpec:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    # Optional: guidance when the server cannot be executed.
    install_hint: str = ""
    preferred_tool_names: List[str] = field(default_factory=list)
    preferred_tool_args: Dict[str, dict] = field(default_factory=dict)


@dataclass
class PhaseResult:
    ok: bool
    ms: float
    error: Optional[str] = None
    stdout_bytes: Optional[int] = None
    approx_tokens: Optional[int] = None


@dataclass
class IterationResult:
    iteration: int
    initialize: PhaseResult
    list_tools: PhaseResult
    call_tool: PhaseResult
    chosen_tool: Optional[str] = None
    chosen_args: Optional[dict] = None


@dataclass
class ServerRunResult:
    name: str
    command: str
    args: List[str]
    iterations: int
    results: List[IterationResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    mode: str = "cold"
    session_initialize: Optional[PhaseResult] = None
    session_list_tools: Optional[PhaseResult] = None


def _pick_readonly_tool(
    tools_list_result: dict,
    *,
    preferred_names: List[str],
    preferred_args: Dict[str, dict],
) -> Tuple[Optional[str], Optional[dict]]:
    """
    Choose a deterministic read-only tool and minimal arguments.

    Heuristics:
    - prefer tools whose names imply read access (unread/recent/search/contacts/list)
    - avoid anything that looks side-effectful (send/create/delete/update/write)
    - if the schema has required fields, supply minimal placeholders
    """
    tool_list = (tools_list_result.get("result") or {}).get("tools") or []

    # Safety: aggressively exclude anything that might have side effects.
    # We prefer skipping a server over accidentally triggering a send/create/etc.
    side_effect_re = re.compile(
        r"(?:^|[^a-z])("
        r"send|sent|create|delete|update|write|edit|add|post|reply|dispatch|deliver"
        r"|rebuild"
        r")(?:[^a-z]|$)",
        flags=re.IGNORECASE,
    )

    # 1) Try preferred tools first (if present and not obviously R/W).
    by_name = {str(t.get("name") or ""): t for t in tool_list if isinstance(t, dict)}
    for name in preferred_names:
        t = by_name.get(name)
        if not t:
            continue
        text = f"{name} {(t.get('description') or '')}"
        if side_effect_re.search(text):
            continue
        args = preferred_args.get(name)
        if args is None:
            args = {}
        return name, args

    candidates = []
    for t in tool_list:
        name = (t.get("name") or "").strip()
        desc = (t.get("description") or "").strip()
        schema = t.get("inputSchema")
        text = f"{name} {desc}"
        if side_effect_re.search(text):
            continue
        lowered = text.lower()
        score = 0
        if any(k in lowered for k in ["unread", "recent", "history", "thread", "messages", "conversation"]):
            score += 5
        if any(k in lowered for k in ["search", "find"]):
            score += 4
        if any(k in lowered for k in ["contacts", "contact"]):
            score += 4
        if any(k in lowered for k in ["list", "get", "fetch", "read"]):
            score += 2

        required: List[str] = []
        properties: Dict[str, Any] = {}
        if isinstance(schema, dict):
            required = schema.get("required") or []
            properties = schema.get("properties") or {}

        args: Dict[str, Any] = {}
        # Fill required args with safe placeholders.
        for key in required:
            prop = properties.get(key) or {}
            tpe = prop.get("type")
            if isinstance(tpe, list):
                tpe = next((x for x in tpe if x != "null"), None)
            if tpe == "string":
                # Prefer a safe, non-PII placeholder for phone-like fields.
                lk = str(key).lower()
                if "phone" in lk or "recipient" in lk:
                    args[key] = SAFE_PLACEHOLDER_PHONE
                else:
                    args[key] = "a"
            elif tpe == "integer" or tpe == "number":
                args[key] = 1
            elif tpe == "boolean":
                args[key] = False
            else:
                # generic placeholder
                args[key] = "a"

        # Special-case common patterns
        if "query" in properties and "query" not in args:
            args["query"] = "a"
        if "limit" in properties and "limit" not in args:
            args["limit"] = 1

        candidates.append((score, name, args))

    candidates.sort(key=lambda x: (x[0], x[1].lower()), reverse=True)
    if not candidates:
        return None, None

    # Extra safety: require at least a weak signal that the tool is read-ish.
    # This avoids picking random tool names that lack semantics (common in buggy servers).
    score, name, args = candidates[0]
    if score <= 0:
        return None, None
    return name or None, args


def _redact_stderr_text(text: str) -> str:
    """
    Best-effort redaction for stderr logs from external MCP servers.

    We print stderr to provide real-time visibility during long runs, but never
    want to leak PII into the terminal scrollback or logs.
    """
    if not text:
        return text

    # Email addresses
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)
    # Local hostnames (often include user/device names)
    text = re.sub(r"\b[A-Za-z0-9._-]+\.local\b", "[REDACTED_HOST]", text)

    # Phone numbers (prefer precision to avoid mangling timestamps/log prefixes).
    # - E.164: +14155552671
    # - Plain digits: 4083480244
    # - Common US formatting: (408) 348-0244 / 408-348-0244 / 408 348 0244
    text = re.sub(r"\+\d{8,15}", "[REDACTED_NUMBER]", text)
    text = re.sub(r"(?<!\d)\d{10,16}(?!\d)", "[REDACTED_NUMBER]", text)
    text = re.sub(
        r"(?<!\d)(?:\(\d{3}\)|\d{3})[-. ]?\d{3}[-. ]?\d{4}(?!\d)",
        "[REDACTED_NUMBER]",
        text,
    )

    return text


def _drain_stderr(proc: subprocess.Popen[bytes], max_seconds: float = 0.5) -> None:
    if proc.stderr is None:
        return
    start = time.time()
    while time.time() - start < max_seconds:
        r, _, _ = select.select([proc.stderr], [], [], 0.05)
        if not r:
            continue
        line = proc.stderr.readline()
        if not line:
            break
        try:
            text = line.decode("utf-8", errors="ignore").rstrip()
        except Exception:
            text = ""
        if text:
            print(_redact_stderr_text(text))


def _read_jsonrpc_response(
    proc: subprocess.Popen[bytes],
    expected_id: int,
    timeout_s: int,
) -> Tuple[Optional[dict], Optional[str], int]:
    """
    Read JSON-RPC messages until we find a response with the expected id.

    Returns: (response_obj, error_str, bytes_read)
    """
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
    if proc.stdin is None:
        raise RuntimeError("missing stdin")
    proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _terminate(proc: subprocess.Popen[bytes]) -> None:
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


def _run_one_iteration(
    spec: McpServerSpec,
    iteration: int,
    phase_timeout_s: int,
    call_timeout_s: int,
    protocol_versions: List[str],
) -> IterationResult:
    # Spawn
    spawn_t0 = time.perf_counter()
    proc = subprocess.Popen(
        [spec.command, *spec.args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=spec.cwd or str(REPO_ROOT),
        env={**os.environ, **(spec.env or {})},
    )

    try:
        _drain_stderr(proc, max_seconds=1.0)

        # 1) initialize (try protocol versions; restart per attempt)
        init_ok = False
        init_err: Optional[str] = None
        init_ms = 0.0
        init_stdout_bytes: Optional[int] = None

        for pv in protocol_versions:
            t0 = time.perf_counter()
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
            init_ms = (time.perf_counter() - t0) * 1000
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

        # Include process startup in the initialize phase for end-to-end comparison.
        init_ms = (time.perf_counter() - spawn_t0) * 1000

        init_phase = PhaseResult(
            ok=init_ok,
            ms=init_ms,
            error=init_err,
            stdout_bytes=init_stdout_bytes,
            approx_tokens=_approx_tokens_from_bytes(init_stdout_bytes),
        )

        if not init_ok:
            return IterationResult(
                iteration=iteration,
                initialize=init_phase,
                list_tools=PhaseResult(ok=False, ms=0.0, error="skipped (init failed)"),
                call_tool=PhaseResult(ok=False, ms=0.0, error="skipped (init failed)"),
            )

        # initialized notification
        _jsonrpc_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 2) list_tools
        t1 = time.perf_counter()
        _jsonrpc_send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp, tools_err, tools_bytes = _read_jsonrpc_response(proc, expected_id=2, timeout_s=phase_timeout_s)
        tools_ms = (time.perf_counter() - t1) * 1000

        tools_ok = tools_err is None and tools_resp is not None and "error" not in tools_resp
        tools_phase = PhaseResult(
            ok=tools_ok,
            ms=tools_ms,
            error=tools_err or ((tools_resp or {}).get("error") or {}).get("message"),
            stdout_bytes=tools_bytes,
            approx_tokens=_approx_tokens_from_bytes(tools_bytes),
        )

        if not tools_ok or tools_resp is None:
            return IterationResult(
                iteration=iteration,
                initialize=init_phase,
                list_tools=tools_phase,
                call_tool=PhaseResult(ok=False, ms=0.0, error="skipped (list_tools failed)"),
            )

        tool_name, tool_args = _pick_readonly_tool(
            tools_resp,
            preferred_names=spec.preferred_tool_names,
            preferred_args=spec.preferred_tool_args,
        )
        if not tool_name:
            return IterationResult(
                iteration=iteration,
                initialize=init_phase,
                list_tools=tools_phase,
                call_tool=PhaseResult(ok=False, ms=0.0, error="no suitable read-only tool found"),
            )

        # 3) call_tool
        t2 = time.perf_counter()
        _jsonrpc_send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": tool_args or {}},
            },
        )
        call_resp, call_err, call_bytes = _read_jsonrpc_response(proc, expected_id=3, timeout_s=call_timeout_s)
        call_ms = (time.perf_counter() - t2) * 1000
        call_ok = call_err is None and call_resp is not None and "error" not in call_resp
        call_phase = PhaseResult(
            ok=call_ok,
            ms=call_ms,
            error=call_err or ((call_resp or {}).get("error") or {}).get("message"),
            stdout_bytes=call_bytes,
            approx_tokens=_approx_tokens_from_bytes(call_bytes),
        )

        return IterationResult(
            iteration=iteration,
            initialize=init_phase,
            list_tools=tools_phase,
            call_tool=call_phase,
            chosen_tool=tool_name,
            chosen_args=None,
        )
    finally:
        _terminate(proc)


def _run_persistent_session(
    spec: McpServerSpec,
    *,
    iterations: int,
    phase_timeout_s: int,
    call_timeout_s: int,
    protocol_versions: List[str],
) -> tuple[PhaseResult, PhaseResult, List[IterationResult]]:
    """
    Run a single MCP server process, initialize once, then call one tool repeatedly.

    This models a tool runner that keeps an MCP stdio server alive across calls.
    """
    spawn_t0 = time.perf_counter()
    proc = subprocess.Popen(
        [spec.command, *spec.args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=spec.cwd or str(REPO_ROOT),
        env={**os.environ, **(spec.env or {})},
    )

    try:
        _drain_stderr(proc, max_seconds=1.0)

        # initialize (try protocol versions without restarting; record last error)
        init_ok = False
        init_err: Optional[str] = None
        init_stdout_bytes: Optional[int] = None
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
        init_phase = PhaseResult(
            ok=init_ok,
            ms=init_ms,
            error=init_err,
            stdout_bytes=init_stdout_bytes,
            approx_tokens=_approx_tokens_from_bytes(init_stdout_bytes),
        )

        if not init_ok:
            return init_phase, PhaseResult(ok=False, ms=0.0, error="skipped (init failed)"), []

        _jsonrpc_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # list_tools
        t1 = time.perf_counter()
        _jsonrpc_send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp, tools_err, tools_bytes = _read_jsonrpc_response(proc, expected_id=2, timeout_s=phase_timeout_s)
        tools_ms = (time.perf_counter() - t1) * 1000
        tools_ok = tools_err is None and tools_resp is not None and "error" not in tools_resp
        list_phase = PhaseResult(
            ok=tools_ok,
            ms=tools_ms,
            error=tools_err or ((tools_resp or {}).get("error") or {}).get("message"),
            stdout_bytes=tools_bytes,
            approx_tokens=_approx_tokens_from_bytes(tools_bytes),
        )
        if not tools_ok or tools_resp is None:
            return init_phase, list_phase, []

        tool_name, tool_args = _pick_readonly_tool(
            tools_resp,
            preferred_names=spec.preferred_tool_names,
            preferred_args=spec.preferred_tool_args,
        )
        if not tool_name:
            return init_phase, list_phase, []

        call_results: List[IterationResult] = []
        for i in range(1, iterations + 1):
            t2 = time.perf_counter()
            _jsonrpc_send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1000 + i,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": tool_args or {}},
                },
            )
            call_resp, call_err, call_bytes = _read_jsonrpc_response(
                proc, expected_id=1000 + i, timeout_s=call_timeout_s
            )
            call_ms = (time.perf_counter() - t2) * 1000
            call_ok = call_err is None and call_resp is not None and "error" not in call_resp
            call_phase = PhaseResult(
                ok=call_ok,
                ms=call_ms,
                error=call_err or ((call_resp or {}).get("error") or {}).get("message"),
                stdout_bytes=call_bytes,
                approx_tokens=_approx_tokens_from_bytes(call_bytes),
            )
            call_results.append(
                IterationResult(
                    iteration=i,
                    initialize=PhaseResult(ok=True, ms=0.0, error="(session mode)"),
                    list_tools=PhaseResult(ok=True, ms=0.0, error="(session mode)"),
                    call_tool=call_phase,
                    chosen_tool=tool_name,
                    chosen_args=None,
                )
            )

        return init_phase, list_phase, call_results
    finally:
        _terminate(proc)


def _summarize_phase(results: List[IterationResult], phase_key: str) -> dict:
    vals = []
    ok = 0
    for it in results:
        phase = getattr(it, phase_key)
        if phase.ok:
            ok += 1
            vals.append(phase.ms)
    vals_sorted = sorted(vals)
    p95 = _percentile(vals_sorted, 95.0)
    mean = sum(vals) / len(vals) if vals else None
    return {
        "ok": ok,
        "total": len(results),
        "mean_ms": mean,
        "p95_ms": p95,
    }


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


def _load_completed_iterations(output_path: Path, server_name: str) -> set[int]:
    try:
        data = _load_json(output_path)
    except Exception:
        return set()
    completed: set[int] = set()
    for srv in data.get("servers") or []:
        if (srv.get("name") or "") != server_name:
            continue
        for it in srv.get("results") or []:
            idx = it.get("iteration")
            if idx is None:
                continue
            # Only mark complete if all phases succeeded.
            if (
                (it.get("initialize") or {}).get("ok")
                and (it.get("list_tools") or {}).get("ok")
                and (it.get("call_tool") or {}).get("ok")
            ):
                completed.add(int(idx))
    return completed


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark MCP stdio tool-call latency")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--phase-timeout", type=int, default=20, help="Timeout per phase (initialize/list/call) in seconds")
    parser.add_argument("--call-timeout", type=int, default=10, help="Timeout for tools/call in seconds")
    parser.add_argument(
        "--mode",
        choices=["cold", "session"],
        default="cold",
        help="cold: start a new server per iteration; session: start once and call repeatedly",
    )
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--npx-download", action="store_true", help="Allow npx to download packages (uses --yes). Default: --no-install")
    parser.add_argument("--server-filter", default=None, help="Only run servers whose name contains this substring")
    parser.add_argument(
        "--protocol-version",
        action="append",
        dest="protocol_versions",
        default=[],
        help="Protocol version to try for MCP initialize (repeatable). Default tries 2024-11-05 then 2025-11-25.",
    )
    args = parser.parse_args()

    ok, err = _preflight_chat_db()
    if not ok:
        print(f"[{_ts()}] Preflight failed: {err}")
        print("Fix: grant Full Disk Access to your terminal and retry.")
        return 2

    out_path = Path(args.output)
    npx_flags = "--yes" if args.npx_download else "--no-install"
    protocol_versions = args.protocol_versions or ["2024-11-05", types.LATEST_PROTOCOL_VERSION]

    servers: List[McpServerSpec] = [
        McpServerSpec(
            name="npx MCP: @iflow-mcp/imessage-mcp-server (stdio)",
            command="npx",
            args=[npx_flags, "--package", "@iflow-mcp/imessage-mcp-server", "iMessage MCP Server"],
        ),
        McpServerSpec(
            name="npx MCP: @foxychat-mcp/apple-imessages (stdio)",
            command="npx",
            args=[npx_flags, "--package", "@foxychat-mcp/apple-imessages", "apple-imessages-mcp"],
        ),
        McpServerSpec(
            name="brew MCP: cardmagic/messages (messages --mcp)",
            command="messages",
            args=["--mcp"],
            preferred_tool_names=[
                "recent_messages",
                "list_conversations",
                "get_message_stats",
                "search_messages",
            ],
            preferred_tool_args={
                "recent_messages": {"limit": 1},
                "list_conversations": {"limit": 1},
                "get_message_stats": {},
                "search_messages": {"query": "http", "limit": 1},
            },
        ),
        McpServerSpec(
            name="python MCP: imessage-life-planner (archived stdio)",
            command="python3",
            args=["-u", "mcp_server_archive/server.py"],
            # Prefer minimal, read-only tools with small outputs.
            preferred_tool_names=[
                "get_unread_messages",
                "get_recent_messages",
                "get_all_recent_conversations",
                "search_messages",
            ],
            preferred_tool_args={
                "get_unread_messages": {"limit": 1},
                "get_recent_messages": {"limit": 1},
                "get_all_recent_conversations": {"limit": 1},
                "search_messages": {"query": "http", "limit": 1},
            },
        ),
        McpServerSpec(
            name="python MCP: mac-messages-mcp (pip, stdio)",
            command=str(COMPETITOR_VENV_BIN / "mac-messages-mcp"),
            args=[],
            install_hint="Install into Texting/benchmarks/.venv_competitors via pip: mac-messages-mcp",
            preferred_tool_names=[
                # mac-messages-mcp tool naming convention
                "tool_get_recent_messages",
                "tool_get_chats",
                "tool_fuzzy_search_messages",
            ],
            preferred_tool_args={
                # Constrain output: this tool has no explicit limit, so we scope by time window.
                "tool_get_recent_messages": {"hours": 1},
                "tool_get_chats": {},
                "tool_fuzzy_search_messages": {"search_term": "http", "hours": 1, "threshold": 95},
            },
        ),
        McpServerSpec(
            name="python MCP: mcp-server-imessage (pip, stdio?)",
            command=str(COMPETITOR_VENV_BIN / "mcp-server-imessage"),
            args=[],
            install_hint="Install into Texting/benchmarks/.venv_competitors via pip: mcp-server-imessage",
            preferred_tool_names=[
                "inbox",
            ],
            preferred_tool_args={
                "inbox": {"limit": 1},
            },
        ),
        # GitHub-only MCP servers (vendored under benchmarks/vendor/github_mcp/)
        McpServerSpec(
            name="github MCP: Causality-C/imessage-mcp-improved (node stdio)",
            command="node",
            args=["server/index.js"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "imessage-mcp-improved"),
            preferred_tool_names=["get_unread_imessages", "get_groups"],
            preferred_tool_args={"get_unread_imessages": {"limit": 1}},
        ),
        McpServerSpec(
            name="github MCP: wyattjoh/imessage-mcp (deno stdio)",
            command="deno",
            args=[
                "run",
                "--allow-read",
                "--allow-env",
                "--allow-sys",
                "--allow-run",
                "--allow-ffi",
                "packages/imessage-mcp/mod.ts",
            ],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "imessage-mcp"),
            preferred_tool_names=["get_recent_messages", "search_messages", "get_chats"],
            preferred_tool_args={"get_recent_messages": {"limit": 1}, "search_messages": {"query": "http", "limit": 1}},
        ),
        McpServerSpec(
            name="github MCP: hannesrudolph/imessage-query-fastmcp-mcp-server (python stdio)",
            command=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "imessage-query-fastmcp-mcp-server"
                / ".venv"
                / "bin"
                / "python"
            ),
            args=["-u", "imessage-query-server.py"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "imessage-query-fastmcp-mcp-server"),
            preferred_tool_names=["get_chat_transcript"],
            preferred_tool_args={"get_chat_transcript": {"phone_number": SAFE_PLACEHOLDER_PHONE}},
        ),
        McpServerSpec(
            name="github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)",
            command=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "jons-mcp-imessage"
                / ".venv"
                / "bin"
                / "jons-mcp-imessage"
            ),
            args=[],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "jons-mcp-imessage"),
            preferred_tool_names=["get_recent_messages", "list_conversations", "search_index_status"],
            preferred_tool_args={"get_recent_messages": {"limit": 1}},
        ),
        McpServerSpec(
            name="github MCP: TextFly/photon-imsg-mcp (node stdio)",
            command="node",
            args=["dist/index.js", "--stdio"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "photon-imsg-mcp"),
            preferred_tool_names=["photon_get_conversations", "photon_read_messages"],
            preferred_tool_args={"photon_get_conversations": {"limit": 1}, "photon_read_messages": {"limit": 1}},
        ),
        McpServerSpec(
            name="github MCP: marissamarym/imessage-mcp-server (node stdio)",
            command="node",
            args=["build/index.js"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "imessage-mcp-server"),
            preferred_tool_names=["search_contacts"],
            preferred_tool_args={"search_contacts": {"query": "a"}},
        ),
        McpServerSpec(
            name="github MCP: rallyventurepartners/iMessage_MCPServer_AdvancedInsights (python fastmcp stdio)",
            command=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "iMessage_MCPServer_AdvancedInsights"
                / ".venv"
                / "bin"
                / "python"
            ),
            args=["-u", "-m", "imessage_mcp_server.main"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "iMessage_MCPServer_AdvancedInsights"),
            env={
                "PYTHONPATH": str(
                    REPO_ROOT
                    / "benchmarks"
                    / "vendor"
                    / "github_mcp"
                    / "iMessage_MCPServer_AdvancedInsights"
                    / "src"
                )
            },
            preferred_tool_names=["imsg_health_check"],
            preferred_tool_args={"imsg_health_check": {"db_path": "~/Library/Messages/chat.db"}},
        ),
        McpServerSpec(
            name="github MCP: mattt/iMCP (swift stdio proxy)",
            command=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "iMCP"
                / ".derived"
                / "Build"
                / "Products"
                / "Release"
                / "iMCP.app"
                / "Contents"
                / "MacOS"
                / "imcp-server"
            ),
            args=[],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "iMCP"),
            install_hint="Build iMCP.app (Xcode) and ensure the iMCP app is running and Messages service activated.",
            preferred_tool_names=["messages_fetch"],
            preferred_tool_args={"messages_fetch": {"participants": [SAFE_PLACEHOLDER_PHONE], "limit": 1}},
        ),
    ]

    if args.server_filter:
        servers = [s for s in servers if args.server_filter.lower() in s.name.lower()]

    payload: dict = {
        "generated_at": _ts(),
        "metadata": {
            "mode": args.mode,
            "iterations": args.iterations,
            "phase_timeout_s": args.phase_timeout,
            "npx_download": args.npx_download,
        },
        "servers": [],
    }

    if args.resume and out_path.exists():
        payload = _load_json(out_path)

    for spec in servers:
        print(f"\n== {spec.name} ==")

        # Fast skip for missing executables to avoid confusing long failures.
        cmd_is_path = (os.sep in spec.command) or spec.command.startswith(".")
        if cmd_is_path:
            if not Path(spec.command).exists():
                server_result = ServerRunResult(
                    name=spec.name,
                    command=spec.command,
                    args=spec.args,
                    iterations=args.iterations,
                    mode=args.mode,
                )
                server_result.notes.append(f"SKIPPED: command not found: {spec.command}")
                payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
                payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)
                print(f"[{_ts()}] skipped: command not found: {spec.command}")
                continue
        else:
            if shutil.which(spec.command) is None:
                server_result = ServerRunResult(
                    name=spec.name,
                    command=spec.command,
                    args=spec.args,
                    iterations=args.iterations,
                    mode=args.mode,
                )
                server_result.notes.append(f"SKIPPED: command not in PATH: {spec.command}")
                payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
                payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)
                print(f"[{_ts()}] skipped: command not in PATH: {spec.command}")
                continue

        completed = _load_completed_iterations(out_path, spec.name) if args.resume and out_path.exists() else set()
        server_result = ServerRunResult(
            name=spec.name,
            command=spec.command,
            args=spec.args,
            iterations=args.iterations,
            mode=args.mode,
        )

        if args.mode == "session":
            print(f"[{_ts()}] session: starting server once, then calling tools/call {args.iterations}x")
            try:
                init_phase, list_phase, call_results = _run_persistent_session(
                    spec,
                    iterations=args.iterations,
                    phase_timeout_s=args.phase_timeout,
                    call_timeout_s=args.call_timeout,
                    protocol_versions=protocol_versions,
                )
            except Exception as exc:
                init_phase = PhaseResult(ok=False, ms=0.0, error=f"exception: {exc}")
                list_phase = PhaseResult(ok=False, ms=0.0, error="skipped (session exception)")
                call_results = []
            server_result.session_initialize = init_phase
            server_result.session_list_tools = list_phase
            server_result.results.extend(call_results)

            print(
                f"[{_ts()}]   session initialize: {'ok' if init_phase.ok else 'fail'} {init_phase.ms:.1f}ms | "
                f"list_tools: {'ok' if list_phase.ok else 'fail'} {list_phase.ms:.1f}ms"
            )
            for it_res in server_result.results:
                ct = it_res.call_tool
                print(
                    f"[{_ts()}]   call {it_res.iteration}/{args.iterations}: "
                    f"{'ok' if ct.ok else 'fail'} {ct.ms:.1f}ms | tool={it_res.chosen_tool}"
                )

            payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
            payload["servers"].append(asdict(server_result))
            _write_json(out_path, payload)
        else:
            for i in range(1, args.iterations + 1):
                if i in completed:
                    print(f"[{_ts()}] iter {i}/{args.iterations}: skipped (already completed)")
                    continue

                print(f"[{_ts()}] iter {i}/{args.iterations}: starting")
                try:
                    it_res = _run_one_iteration(spec, i, args.phase_timeout, args.call_timeout, protocol_versions)
                except Exception as exc:
                    # Catch-all so the whole run doesn't die; record as a failed iteration.
                    it_res = IterationResult(
                        iteration=i,
                        initialize=PhaseResult(ok=False, ms=0.0, error=f"exception: {exc}"),
                        list_tools=PhaseResult(ok=False, ms=0.0, error="skipped"),
                        call_tool=PhaseResult(ok=False, ms=0.0, error="skipped"),
                    )

                server_result.results.append(it_res)
                init = it_res.initialize
                lt = it_res.list_tools
                ct = it_res.call_tool
                print(
                    f"[{_ts()}]   initialize: {'ok' if init.ok else 'fail'} {init.ms:.1f}ms | "
                    f"list_tools: {'ok' if lt.ok else 'fail'} {lt.ms:.1f}ms | "
                    f"call_tool: {'ok' if ct.ok else 'fail'} {ct.ms:.1f}ms | "
                    f"tool={it_res.chosen_tool}"
                )

                # Stream checkpoint after each iteration.
                # Merge into payload in a stable way.
                existing = [s for s in payload.get("servers") if (s.get("name") or "") == spec.name]
                if existing:
                    srv_obj = existing[0]
                    srv_obj["results"] = [asdict(r) for r in server_result.results]
                else:
                    payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)

        # Print summary
        print("\nSummary:")
        if args.mode == "session":
            si = server_result.session_initialize
            sl = server_result.session_list_tools
            print(
                "  session_initialize:",
                {
                    "ok": 1 if (si and si.ok) else 0,
                    "total": 1,
                    "mean_ms": si.ms if si else None,
                    "p95_ms": si.ms if si else None,
                },
            )
            print(
                "  session_list_tools:",
                {
                    "ok": 1 if (sl and sl.ok) else 0,
                    "total": 1,
                    "mean_ms": sl.ms if sl else None,
                    "p95_ms": sl.ms if sl else None,
                },
            )
        else:
            print("  initialize:", _summarize_phase(server_result.results, "initialize"))
            print("  list_tools:", _summarize_phase(server_result.results, "list_tools"))
        print("  call_tool:", _summarize_phase(server_result.results, "call_tool"))

        # Write final per-server checkpoint
        existing = [s for s in payload.get("servers") if (s.get("name") or "") == spec.name]
        if existing:
            existing[0]["results"] = [asdict(r) for r in server_result.results]
        else:
            payload["servers"].append(asdict(server_result))
        _write_json(out_path, payload)

    print(f"\nSaved results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
