#!/usr/bin/env python3
"""
Normalized MCP workload benchmarks (read-only by default).

This runner executes a small, fixed set of workloads across MCP servers
with strict timeouts and real-time telemetry. It does NOT persist tool
arguments or tool outputs (PII safety), except for redacted debug payloads
when validity checks fail.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import select
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp import types


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CLI = REPO_ROOT / "gateway" / "imessage_client.py"


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _approx_tokens_from_bytes(byte_count: int | None) -> int | None:
    if byte_count is None:
        return None
    return int(math.ceil(byte_count / 4.0))


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


DEFAULT_MIN_BYTES = {
    "W0_UNREAD": 150,
    "W1_RECENT": 200,
    "W2_SEARCH": 200,
    "W3_THREAD": 150,
}

DEFAULT_MIN_ITEMS = {
    "W0_UNREAD": 0,
    "W1_RECENT": 1,
    "W2_SEARCH": 1,
    "W3_THREAD": 1,
}

MAX_PAYLOAD_BYTES = _env_int("IMESSAGE_BENCH_MAX_PAYLOAD_BYTES", 10_000_000)
MAX_PAYLOAD_TOKENS = _env_int("IMESSAGE_BENCH_MAX_PAYLOAD_TOKENS", 2_500_000)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _safe_json_dumps(obj: Any, *, sort_keys: bool = False) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=sort_keys, separators=(",", ":") if sort_keys else None)
    except TypeError:
        return json.dumps(obj, ensure_ascii=False, sort_keys=sort_keys, separators=(",", ":") if sort_keys else None, default=str)


def _preflight_chat_db() -> Tuple[bool, str]:
    """
    Fail fast if Full Disk Access is missing (common root cause of failures).
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


def _redact_stderr_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b[A-Za-z0-9._-]+\.local\b", "[REDACTED_HOST]", text)
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


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: Dict[str, Any]


@dataclass(frozen=True)
class TargetSelector:
    tool: ToolCall
    kind: str


@dataclass(frozen=True)
class WorkloadSpec:
    workload_id: str
    label: str
    read_only: bool = True


@dataclass
class McpServerSpec:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    install_hint: str = ""
    workload_map: Dict[str, ToolCall] = field(default_factory=dict)
    target_selector: Optional[TargetSelector] = None


@dataclass
class PhaseResult:
    ok: bool
    ms: float
    error: Optional[str] = None
    stdout_bytes: Optional[int] = None
    approx_tokens: Optional[int] = None


@dataclass
class CallResult:
    iteration: int
    ok: bool
    ms: float
    error: Optional[str]
    stdout_bytes: Optional[int]
    approx_tokens: Optional[int]
    payload_bytes: Optional[int] = None
    payload_tokens_est: Optional[int] = None
    payload_fingerprint: Optional[str] = None
    payload_item_count: Optional[int] = None
    validation_status: Optional[str] = None
    validation_reason: Optional[str] = None


@dataclass
class WorkloadResult:
    workload_id: str
    tool_name: Optional[str] = None
    read_only: bool = True
    status: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    valid_summary: Dict[str, Any] = field(default_factory=dict)
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    warmup_results: List[CallResult] = field(default_factory=list)
    results: List[CallResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ServerRunResult:
    name: str
    command: str
    args: List[str]
    mode: str = "session"
    session_initialize: Optional[PhaseResult] = None
    session_list_tools: Optional[PhaseResult] = None
    workloads: List[WorkloadResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _call_tool(
    proc: subprocess.Popen[bytes],
    *,
    request_id: int,
    tool_name: str,
    tool_args: Dict[str, Any],
    timeout_s: int,
    context: Optional[str] = None,
) -> CallResult:
    _, call = _call_tool_raw(
        proc,
        request_id=request_id,
        tool_name=tool_name,
        tool_args=tool_args,
        timeout_s=timeout_s,
        context=context,
    )
    return call


def _call_tool_raw(
    proc: subprocess.Popen[bytes],
    *,
    request_id: int,
    tool_name: str,
    tool_args: Dict[str, Any],
    timeout_s: int,
    context: Optional[str] = None,
) -> Tuple[Optional[dict], CallResult]:
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
    call_resp, call_err, call_bytes = _read_jsonrpc_response(proc, expected_id=request_id, timeout_s=timeout_s)
    call_ms = (time.perf_counter() - t0) * 1000
    call_ok = call_err is None and call_resp is not None and "error" not in call_resp
    result_obj = (call_resp or {}).get("result")
    payload_bytes = _payload_bytes_from_result(result_obj)
    payload_tokens = _approx_tokens_from_bytes(payload_bytes) if payload_bytes is not None else None
    payload_fingerprint = _payload_fingerprint(result_obj)
    payload_item_count = _count_items(_extract_json_payload(call_resp))

    if payload_bytes is not None and payload_bytes > MAX_PAYLOAD_BYTES and context:
        print(f"[{_ts()}]   metric drop: {context} (payload_bytes>{MAX_PAYLOAD_BYTES})")
    if payload_tokens is not None:
        if payload_tokens <= 0 and context:
            print(f"[{_ts()}]   metric drop: {context} (payload_tokens<=0)")
            payload_tokens = None
        elif payload_tokens > MAX_PAYLOAD_TOKENS and context:
            print(f"[{_ts()}]   metric drop: {context} (payload_tokens>{MAX_PAYLOAD_TOKENS})")
            payload_tokens = None
    return (
        call_resp,
        CallResult(
            iteration=request_id,
            ok=call_ok,
            ms=call_ms,
            error=call_err or ((call_resp or {}).get("error") or {}).get("message"),
            stdout_bytes=call_bytes,
            approx_tokens=_approx_tokens_from_bytes(call_bytes),
            payload_bytes=payload_bytes,
            payload_tokens_est=payload_tokens,
            payload_fingerprint=payload_fingerprint,
            payload_item_count=payload_item_count,
        ),
    )


def _tool_names_from_list(tools_resp: dict) -> set[str]:
    tool_list = (tools_resp.get("result") or {}).get("tools") or []
    return {str(t.get("name") or "") for t in tool_list if isinstance(t, dict)}


def _extract_text_blocks(resp: Optional[dict]) -> List[str]:
    if not resp or not isinstance(resp, dict):
        return []
    result = resp.get("result") or {}
    content = result.get("content")
    if not isinstance(content, list):
        return []
    texts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return texts


def _extract_json_payload(resp: Optional[dict]) -> Optional[Any]:
    if not resp or not isinstance(resp, dict):
        return None
    result = resp.get("result")
    if isinstance(result, dict):
        if "content" in result and isinstance(result["content"], list):
            for item in result["content"]:
                if not isinstance(item, dict):
                    continue
                if "json" in item:
                    return item.get("json")
                text = item.get("text")
                if isinstance(text, str):
                    stripped = text.strip()
                    if stripped.startswith("{") or stripped.startswith("["):
                        try:
                            return json.loads(stripped)
                        except Exception:
                            continue
        return result
    return resp


def _payload_bytes_from_result(result_obj: Optional[Any]) -> Optional[int]:
    if result_obj is None:
        return None
    raw = _safe_json_dumps(result_obj)
    byte_count = len(raw.encode("utf-8"))
    if byte_count <= 0:
        return None
    return byte_count


def _payload_fingerprint(result_obj: Optional[Any]) -> Optional[str]:
    if result_obj is None:
        return None
    canonical = _safe_json_dumps(result_obj, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _count_items(obj: Any) -> Optional[int]:
    if obj is None:
        return None
    max_len: Optional[int] = None

    def visit(node: Any) -> None:
        nonlocal max_len
        if isinstance(node, list):
            max_len = max(max_len or 0, len(node))
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            for val in node.values():
                visit(val)

    visit(obj)
    return max_len


def _redact_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _redact_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_payload(v) for v in obj]
    if isinstance(obj, str):
        text = obj
        text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[REDACTED_EMAIL]", text)
        text = re.sub(r"\+\d{8,15}", "[REDACTED_NUMBER]", text)
        text = re.sub(r"(?<!\d)\d{10,16}(?!\d)", "[REDACTED_NUMBER]", text)
        text = re.sub(
            r"(?<!\d)(?:\(\d{3}\)|\d{3})[-. ]?\d{3}[-. ]?\d{4}(?!\d)",
            "[REDACTED_NUMBER]",
            text,
        )
        return text
    return obj


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "server"


def _find_first_key(obj: Any, keys: Tuple[str, ...]) -> Optional[Any]:
    if isinstance(obj, dict):
        for key in keys:
            if key in obj:
                return obj[key]
        for val in obj.values():
            found = _find_first_key(val, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_key(item, keys)
            if found is not None:
                return found
    return None


def _extract_target_from_response(kind: str, resp: Optional[dict]) -> Optional[str]:
    payload = _extract_json_payload(resp)
    texts = _extract_text_blocks(resp)

    if kind == "cardmagic_contact":
        for text in texts:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                if line.lower().startswith("top "):
                    continue
                if line.startswith("└─"):
                    continue
                if " (" in line:
                    return line.split(" (", 1)[0].strip()
        return None

    if kind == "chat_guid":
        if isinstance(payload, dict) and isinstance(payload.get("chats"), list):
            for chat in payload["chats"]:
                if not isinstance(chat, dict):
                    continue
                guid = chat.get("guid") or chat.get("chatGuid") or chat.get("chat_guid")
                if guid:
                    return str(guid)
        found = _find_first_key(payload, ("chatGuid", "chat_guid", "guid"))
        return str(found) if found is not None else None

    if kind == "photon_chat_id":
        for text in texts:
            for line in text.splitlines():
                line = line.strip()
                if line.lower().startswith("chat id:"):
                    return line.split(":", 1)[1].strip()
        if isinstance(payload, dict) and isinstance(payload.get("conversations"), list):
            for conv in payload["conversations"]:
                if not isinstance(conv, dict):
                    continue
                chat_id = conv.get("chatId") or conv.get("chat_id") or conv.get("id")
                if chat_id:
                    return str(chat_id)
        found = _find_first_key(payload, ("chatId", "chat_id"))
        return str(found) if found is not None else None

    if kind == "chat_id":
        if isinstance(payload, dict) and isinstance(payload.get("conversations"), list):
            for conv in payload["conversations"]:
                if not isinstance(conv, dict):
                    continue
                chat_id = conv.get("chat_id") or conv.get("chatId")
                if chat_id is not None:
                    return str(chat_id)
        found = _find_first_key(payload, ("chat_id", "chatId"))
        return str(found) if found is not None else None

    if kind == "imcp_sender":
        if isinstance(payload, dict):
            parts = payload.get("hasPart") or payload.get("haspart") or []
            if isinstance(parts, list):
                for msg in parts:
                    if not isinstance(msg, dict):
                        continue
                    sender = msg.get("sender")
                    if isinstance(sender, dict):
                        sender = sender.get("@id") or sender.get("id")
                    if isinstance(sender, str):
                        normalized = sender.strip()
                        if normalized and normalized.lower() not in {"me", "unknown"}:
                            return normalized
        return None

    if kind == "phone_number":
        if isinstance(payload, dict):
            found = _find_first_key(payload, ("phone", "phoneNumber", "number", "contact"))
            if isinstance(found, str) and found.strip():
                return found.strip()
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", "\n".join(texts))
        if email_match:
            return email_match.group(0)
        number_match = re.search(r"\+?\d[\d\s().-]{7,}\d", "\n".join(texts))
        if number_match:
            return number_match.group(0).strip()
        return None

    return None


def _resolve_args(value: Any, target: Optional[str]) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_args(v, target) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_args(v, target) for v in value]
    if isinstance(value, str) and value == "__TARGET__":
        return target
    return value


def _parse_overrides(values: Optional[List[str]], *, label: str) -> Dict[str, int]:
    overrides: Dict[str, int] = {}
    if not values:
        return overrides
    for raw in values:
        if not raw:
            continue
        if "=" not in raw:
            raise ValueError(f"{label} overrides must be in WORKLOAD_ID=VALUE format")
        key, val = raw.split("=", 1)
        key = key.strip().upper()
        try:
            overrides[key] = int(val.strip())
        except ValueError as exc:
            raise ValueError(f"{label} override for {key} must be an int") from exc
    return overrides


def _build_thresholds(
    workloads: Dict[str, WorkloadSpec],
    overrides: Dict[str, int],
    defaults: Dict[str, int],
    env_suffix: str,
) -> Dict[str, int]:
    thresholds: Dict[str, int] = {}
    for workload_id in workloads.keys():
        default = defaults.get(workload_id, 0)
        env_name = f"IMESSAGE_BENCH_MIN_{workload_id}_{env_suffix}"
        thresholds[workload_id] = overrides.get(workload_id, _env_int(env_name, default))
    return thresholds


def _validate_payload(
    *,
    workload_id: str,
    payload_bytes: Optional[int],
    payload_item_count: Optional[int],
    strict_validity: bool,
    min_bytes: Dict[str, int],
    min_items: Dict[str, int],
) -> Tuple[bool, str]:
    if not strict_validity:
        return True, "strict_validity_disabled"
    if payload_bytes is None:
        return False, "missing_payload_bytes"
    min_bytes_required = min_bytes.get(workload_id, 0)
    if payload_bytes < min_bytes_required:
        return False, f"payload_bytes_below_min({payload_bytes}<{min_bytes_required})"
    min_items_required = min_items.get(workload_id, 0)
    if payload_item_count is not None and payload_item_count < min_items_required:
        return False, f"items_below_min({payload_item_count}<{min_items_required})"
    return True, "valid"


def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _p95(values: List[float]) -> Optional[float]:
    if not values:
        return None
    values_sorted = sorted(values)
    if len(values_sorted) == 1:
        return values_sorted[0]
    idx = int(0.95 * (len(values_sorted) - 1))
    return values_sorted[idx]


def _summarize_calls(calls: List[CallResult], *, status_filter: Optional[set[str]] = None) -> dict:
    filtered = [c for c in calls if c.ok]
    if status_filter is not None:
        filtered = [c for c in filtered if c.validation_status in status_filter]
    ms_vals = [c.ms for c in filtered]
    payload_bytes_vals = [c.payload_bytes for c in filtered if c.payload_bytes is not None]
    payload_tokens_vals = [c.payload_tokens_est for c in filtered if c.payload_tokens_est is not None]
    return {
        "ok": len(filtered),
        "total": len(calls),
        "mean_ms": _mean(ms_vals),
        "p95_ms": _p95(ms_vals),
        "mean_payload_bytes": _mean([float(v) for v in payload_bytes_vals]) if payload_bytes_vals else None,
        "mean_payload_tokens": _mean([float(v) for v in payload_tokens_vals]) if payload_tokens_vals else None,
    }


def _summarize_validation(calls: List[CallResult]) -> dict:
    status_counts = Counter(c.validation_status for c in calls if c.validation_status)
    reason_counts = Counter(c.validation_reason for c in calls if c.validation_reason)
    return {
        "counts": dict(status_counts),
        "top_reasons": [r for r, _ in reason_counts.most_common(3)],
    }


def _apply_validation_to_call(
    call: CallResult,
    *,
    workload_id: str,
    strict_validity: bool,
    min_bytes: Dict[str, int],
    min_items: Dict[str, int],
) -> None:
    if not call.ok:
        call.validation_status = "fail_timeout" if call.error == "TIMEOUT" else "fail"
        call.validation_reason = call.error
        return
    is_valid, reason = _validate_payload(
        workload_id=workload_id,
        payload_bytes=call.payload_bytes,
        payload_item_count=call.payload_item_count,
        strict_validity=strict_validity,
        min_bytes=min_bytes,
        min_items=min_items,
    )
    call.validation_status = "ok_valid" if is_valid else "ok_empty"
    if not is_valid:
        call.validation_reason = reason
    elif reason not in {"valid", "strict_validity_disabled"}:
        call.validation_reason = reason


def _run_label_from_path(out_path: Path) -> str:
    stem = out_path.stem
    if stem.startswith("normalized_workloads_"):
        return stem[len("normalized_workloads_") :]
    return stem


def _derive_workload_status(workload: WorkloadResult) -> str:
    if workload.tool_name is None or any(
        "unsupported" in note or "tool not found" in note for note in workload.notes
    ):
        return "unsupported"
    ok_calls = [c for c in workload.results if c.ok]
    if not ok_calls:
        if any(c.validation_status == "fail_timeout" for c in workload.results):
            return "fail_timeout"
        return "fail"
    valid = [c for c in ok_calls if c.validation_status == "ok_valid"]
    empty = [c for c in ok_calls if c.validation_status == "ok_empty"]
    if valid and not empty:
        return "ok_valid"
    if empty and not valid:
        return "ok_empty"
    return "partial_valid"


def _write_debug_payloads(
    *,
    out_path: Path,
    run_label: str,
    server_name: str,
    workloads: List[WorkloadResult],
    debug_samples: Dict[str, Any],
    min_bytes: Dict[str, int],
    min_items: Dict[str, int],
) -> None:
    base_dir = out_path.parent / "debug_payloads" / run_label / _slugify(server_name)
    manifest_path = base_dir / "manifest.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        manifest = _load_json(manifest_path)

    for workload in workloads:
        if workload.status not in {"ok_empty", "partial_valid"}:
            continue
        sample = debug_samples.get(workload.workload_id)
        if sample is None:
            continue
        payload_path = base_dir / f"{workload.workload_id}.json"
        _write_json(payload_path, sample)
        manifest[workload.workload_id] = {
            "status": workload.status,
            "notes": workload.notes,
            "validation_summary": workload.validation_summary,
            "min_bytes": min_bytes.get(workload.workload_id),
            "min_items": min_items.get(workload.workload_id),
        }

    if manifest:
        _write_json(manifest_path, manifest)


def _format_ms(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def _format_workload_cell(workload: dict) -> str:
    status = workload.get("status") or ""
    summary = workload.get("summary") or {}
    mean_ms = summary.get("mean_ms")
    p95_ms = summary.get("p95_ms")
    if status == "unsupported":
        return "UNSUPPORTED"
    if status == "fail_timeout":
        return "FAIL (TIMEOUT)"
    if status == "fail":
        return "FAIL"
    if mean_ms is None or p95_ms is None:
        return status.upper() if status else ""
    label = f"{mean_ms:.3f}ms (p95 {p95_ms:.3f})"
    if status == "ok_empty":
        return f"OK_EMPTY {label}"
    if status == "partial_valid":
        return f"PARTIAL {label}"
    return label


def _write_csv(path: Path, rows: List[dict], fieldnames: Optional[List[str]] = None) -> None:
    if not rows:
        return
    if fieldnames is None:
        keys = set()
        for row in rows:
            keys.update(row.keys())
        fieldnames = sorted(keys)
    _ensure_parent(path)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_md_table(headers: List[str], rows: List[List[str]]) -> str:
    header_line = "|" + "|".join(headers) + "|"
    sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [header_line, sep_line]
    for row in rows:
        safe = ["" if cell is None else str(cell) for cell in row]
        lines.append("|" + "|".join(safe) + "|")
    return "\n".join(lines)


def _write_headline_tables(payload: dict, out_path: Path) -> None:
    metadata = payload.get("metadata") or {}
    run_label = metadata.get("run_label") or _run_label_from_path(out_path)
    node_version = metadata.get("node_version") or ""
    workloads = metadata.get("workloads") or []
    validation = metadata.get("validation") or {}

    server_rows: List[dict] = []
    tool_rows: List[dict] = []
    ranking_rows: List[dict] = []

    for server in payload.get("servers") or []:
        init = server.get("session_initialize") or {}
        listing = server.get("session_list_tools") or {}
        server_row = {
            "table": "server_summary",
            "server": server.get("name", ""),
            "run": run_label,
            "node": node_version,
            "init_ok": init.get("ok", ""),
            "init_ms": init.get("ms", ""),
            "list_ok": listing.get("ok", ""),
            "list_ms": listing.get("ms", ""),
        }

        workload_map = {w.get("workload_id"): w for w in server.get("workloads") or []}
        for workload_id in workloads:
            workload = workload_map.get(workload_id)
            if not workload:
                workload = {
                    "status": "unsupported",
                    "results": [],
                    "notes": ["unsupported workload (missing)"],
                }
            summary = workload.get("summary") or {}
            validation_summary = workload.get("validation_summary") or {}
            counts = validation_summary.get("counts") or {}
            results = workload.get("results") or []
            ok_total = sum(1 for r in results if r.get("ok"))
            ok_valid = counts.get("ok_valid", 0)
            server_row[f"{workload_id}_status"] = workload.get("status", "")
            server_row[f"{workload_id}_ok"] = f"{ok_valid}/{len(results)}" if results else "0/0"
            server_row[f"{workload_id}_mean_ms"] = summary.get("mean_ms", "")
            server_row[f"{workload_id}_p95_ms"] = summary.get("p95_ms", "")
            server_row[f"{workload_id}_error"] = next((r.get("error") for r in results if r.get("error")), "")
            server_row[f"{workload_id}_tool"] = workload.get("tool_name", "")
            notes = list(workload.get("notes") or [])
            if ok_total and ok_total != ok_valid:
                notes.append(f"raw_ok={ok_total}/{len(results)}")
            server_row[f"{workload_id}_notes"] = "; ".join(notes)

            tool_rows.append(
                {
                    "table": "tool_mapping",
                    "server": server.get("name", ""),
                    "run": run_label,
                    "node": node_version,
                    "workload": workload_id,
                    "tool": workload.get("tool_name", ""),
                    "status": workload.get("status", ""),
                    "ok": f"{ok_valid}/{len(results)}" if results else "0/0",
                    "mean_ms": summary.get("mean_ms", ""),
                    "p95_ms": summary.get("p95_ms", ""),
                    "error": next((r.get("error") for r in results if r.get("error")), ""),
                    "notes": "; ".join(notes),
                    "init_ok": init.get("ok", ""),
                    "init_ms": init.get("ms", ""),
                    "list_ok": listing.get("ok", ""),
                    "list_ms": listing.get("ms", ""),
                }
            )

        server_rows.append(server_row)

    for workload_id in workloads:
        candidates = []
        for server in payload.get("servers") or []:
            workload = next(
                (w for w in server.get("workloads") or [] if w.get("workload_id") == workload_id),
                None,
            )
            if not workload or workload.get("status") != "ok_valid":
                continue
            valid_summary = workload.get("valid_summary") or {}
            mean_ms = valid_summary.get("mean_ms")
            if mean_ms is None:
                continue
            candidates.append(
                {
                    "server": server.get("name", ""),
                    "tool": workload.get("tool_name", ""),
                    "mean_ms": mean_ms,
                    "p95_ms": valid_summary.get("p95_ms"),
                }
            )
        candidates.sort(key=lambda x: x["mean_ms"])
        for idx, cand in enumerate(candidates, start=1):
            ranking_rows.append(
                {
                    "table": "workload_rankings",
                    "workload": workload_id,
                    "rank": idx,
                    "server": cand["server"],
                    "run": run_label,
                    "node": node_version,
                    "mean_ms": cand["mean_ms"],
                    "p95_ms": cand["p95_ms"],
                    "tool": cand["tool"],
                }
            )

    results_dir = out_path.parent
    md_path = results_dir / f"normalized_headline_tables_{run_label}_validated.md"
    server_csv = results_dir / f"normalized_headline_server_summary_{run_label}_validated.csv"
    tool_csv = results_dir / f"normalized_headline_tool_mapping_{run_label}_validated.csv"
    ranking_csv = results_dir / f"normalized_headline_workload_rankings_{run_label}_validated.csv"
    combined_csv = results_dir / f"normalized_headline_combined_{run_label}_validated.csv"

    _write_csv(server_csv, server_rows, fieldnames=list(server_rows[0].keys()) if server_rows else None)
    _write_csv(tool_csv, tool_rows, fieldnames=list(tool_rows[0].keys()) if tool_rows else None)
    _write_csv(ranking_csv, ranking_rows, fieldnames=list(ranking_rows[0].keys()) if ranking_rows else None)

    combined_rows = server_rows + tool_rows + ranking_rows
    _write_csv(combined_csv, combined_rows)

    md_lines = [
        "# Normalized MCP Headline Tables (Validated)",
        "",
        "## Run Metadata",
        f"- {run_label}: iterations={metadata.get('iterations')} warmup={metadata.get('warmup')} "
        f"phase_timeout_s={metadata.get('phase_timeout_s')} call_timeout_s={metadata.get('call_timeout_s')} "
        f"workloads={','.join(workloads)}",
        f"- strict_validity={validation.get('strict_validity')} min_bytes={validation.get('min_bytes')} "
        f"min_items={validation.get('min_items')}",
        "",
        "## Server Summary Table",
    ]

    if payload.get("servers"):
        headers = ["server", "run", "node", "init_ok", "init_ms", "list_ok", "list_ms"] + workloads
        rows = []
        for server in payload.get("servers") or []:
            init = server.get("session_initialize") or {}
            listing = server.get("session_list_tools") or {}
            workload_map = {w.get("workload_id"): w for w in server.get("workloads") or []}
            cell_values = [
                _format_workload_cell(workload_map.get(workload_id, {"status": "unsupported"}))
                for workload_id in workloads
            ]
            rows.append(
                [
                    server.get("name", ""),
                    str(run_label),
                    str(node_version),
                    str(init.get("ok", "")),
                    _format_ms(init.get("ms")),
                    str(listing.get("ok", "")),
                    _format_ms(listing.get("ms")),
                    *cell_values,
                ]
            )
        md_lines.append(_write_md_table(headers, rows))
    else:
        md_lines.append("(no results)")

    md_lines.extend(
        [
            "",
            "## Tool Mapping Table",
        ]
    )
    if tool_rows:
        headers = ["server", "run", "workload", "tool", "status", "ok", "mean_ms", "p95_ms", "error", "notes"]
        rows = [
            [
                row["server"],
                str(row["run"]),
                row["workload"],
                row["tool"],
                row["status"],
                row["ok"],
                _format_ms(row["mean_ms"]) if row.get("mean_ms") != "" else "",
                _format_ms(row["p95_ms"]) if row.get("p95_ms") != "" else "",
                row["error"] or "",
                row["notes"] or "",
            ]
            for row in tool_rows
        ]
        md_lines.append(_write_md_table(headers, rows))
    else:
        md_lines.append("(no results)")

    md_lines.extend(
        [
            "",
            "## Workload Rankings (ok_valid only)",
            "Rankings exclude ok_empty.",
            "",
        ]
    )

    for workload_id in workloads:
        md_lines.append(f"### {workload_id}")
        rows = [r for r in ranking_rows if r.get("workload") == workload_id]
        if not rows:
            md_lines.append("(no ok_valid results)")
            md_lines.append("")
            continue
        headers = ["rank", "server", "run", "node", "mean_ms", "p95_ms", "tool"]
        table_rows = [
            [
                str(r["rank"]),
                r["server"],
                str(r["run"]),
                str(r["node"]),
                _format_ms(r["mean_ms"]),
                _format_ms(r["p95_ms"]),
                r["tool"],
            ]
            for r in rows
        ]
        md_lines.append(_write_md_table(headers, table_rows))
        md_lines.append("")

    _ensure_parent(md_path)
    md_path.write_text("\n".join(md_lines))


def _run_session(
    spec: McpServerSpec,
    workloads: Dict[str, WorkloadSpec],
    *,
    iterations: int,
    warmup: int,
    phase_timeout_s: int,
    call_timeout_s: int,
    protocol_versions: List[str],
    out_path: Path,
    payload: dict,
    strict_validity: bool,
    min_bytes: Dict[str, int],
    min_items: Dict[str, int],
    run_label: str,
) -> ServerRunResult:
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
        mode="session",
    )
    debug_samples: Dict[str, Any] = {}
    duplicate_workloads: set[str] = set()

    try:
        _drain_stderr(proc, max_seconds=1.0)

        # initialize
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
        server_result.session_initialize = PhaseResult(
            ok=init_ok,
            ms=init_ms,
            error=init_err,
            stdout_bytes=init_stdout_bytes,
            approx_tokens=_approx_tokens_from_bytes(init_stdout_bytes),
        )

        if not init_ok:
            return server_result

        _jsonrpc_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # list_tools
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
            approx_tokens=_approx_tokens_from_bytes(tools_bytes),
        )

        if not tools_ok or tools_resp is None:
            return server_result

        tool_names = _tool_names_from_list(tools_resp)
        env_target = os.environ.get("IMESSAGE_BENCH_TARGET") or os.environ.get("IMESSAGE_BENCH_SEND_TO")

        # run workloads
        next_id = 1000
        target_cache: Optional[str] = None
        for workload_id, workload in workloads.items():
            w_result = WorkloadResult(workload_id=workload_id, read_only=workload.read_only)
            mapping = spec.workload_map.get(workload_id)
            if not mapping:
                w_result.notes.append("unsupported workload (no tool mapping)")
                server_result.workloads.append(w_result)
                continue
            if mapping.name not in tool_names:
                w_result.notes.append(f"tool not found: {mapping.name}")
                server_result.workloads.append(w_result)
                continue
            w_result.tool_name = mapping.name

            resolved_args = mapping.args
            if workload_id == "W3_THREAD":
                if spec.target_selector is None:
                    if env_target:
                        target_cache = env_target
                    else:
                        w_result.notes.append("missing target selector for thread workload")
                        server_result.workloads.append(w_result)
                        continue
                if target_cache is None:
                    selector = spec.target_selector
                    next_id += 1
                    resp, sel_call = _call_tool_raw(
                        proc,
                        request_id=next_id,
                        tool_name=selector.tool.name,
                        tool_args=selector.tool.args,
                        timeout_s=call_timeout_s,
                    )
                    if not sel_call.ok:
                        if env_target:
                            target_cache = env_target
                        else:
                            w_result.notes.append(f"target selection failed: {sel_call.error}")
                            server_result.workloads.append(w_result)
                            continue
                    target_cache = _extract_target_from_response(selector.kind, resp)
                    if not target_cache:
                        if env_target:
                            target_cache = env_target
                        else:
                            w_result.notes.append("target selection returned no candidate")
                            server_result.workloads.append(w_result)
                            continue

                resolved_args = _resolve_args(mapping.args, target_cache)

            # warmup calls (not included in summary)
            for _ in range(max(warmup, 0)):
                next_id += 1
                warm = _call_tool(
                    proc,
                    request_id=next_id,
                    tool_name=mapping.name,
                    tool_args=resolved_args,
                    timeout_s=call_timeout_s,
                    context=f"{spec.name} {workload_id} warmup",
                )
                _apply_validation_to_call(
                    warm,
                    workload_id=workload_id,
                    strict_validity=strict_validity,
                    min_bytes=min_bytes,
                    min_items=min_items,
                )
                w_result.warmup_results.append(warm)
                print(
                    f"[{_ts()}]   warmup {workload_id}: "
                    f"{'ok' if warm.ok else 'fail'} {warm.ms:.1f}ms | tool={mapping.name}"
                )
                # checkpoint after warmup
                payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
                payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)

            # measured calls
            for i in range(1, iterations + 1):
                next_id += 1
                resp, call = _call_tool_raw(
                    proc,
                    request_id=next_id,
                    tool_name=mapping.name,
                    tool_args=resolved_args,
                    timeout_s=call_timeout_s,
                    context=f"{spec.name} {workload_id} {i}/{iterations}",
                )
                call.iteration = i
                _apply_validation_to_call(
                    call,
                    workload_id=workload_id,
                    strict_validity=strict_validity,
                    min_bytes=min_bytes,
                    min_items=min_items,
                )
                if call.ok and workload_id not in debug_samples:
                    result_obj = (resp or {}).get("result")
                    if result_obj is not None:
                        debug_samples[workload_id] = _redact_payload(result_obj)
                w_result.results.append(call)
                print(
                    f"[{_ts()}]   {workload_id} {i}/{iterations}: "
                    f"{'ok' if call.ok else 'fail'} {call.ms:.1f}ms | tool={mapping.name}"
                )
                # checkpoint after each call
                payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
                payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)

            server_result.workloads.append(w_result)

        if strict_validity:
            fingerprint_map: Dict[str, str] = {}
            for workload in server_result.workloads:
                fingerprints = [
                    c.payload_fingerprint
                    for c in workload.results
                    if c.ok and c.payload_fingerprint
                ]
                if fingerprints:
                    fingerprint_map[workload.workload_id] = Counter(fingerprints).most_common(1)[0][0]

            duplicates: Dict[str, List[str]] = {}
            for workload_id, fingerprint in fingerprint_map.items():
                duplicates.setdefault(fingerprint, []).append(workload_id)

            for workload_ids in duplicates.values():
                if len(workload_ids) < 2:
                    continue
                label = ", ".join(sorted(workload_ids))
                for workload in server_result.workloads:
                    if workload.workload_id in workload_ids:
                        duplicate_workloads.add(workload.workload_id)
                        for call in workload.results:
                            if call.ok and call.validation_status == "ok_valid":
                                call.validation_status = "ok_empty"
                                call.validation_reason = "duplicate_payload"
                        workload.notes.append(f"suspicious: identical payload across workloads {label}")

        for workload in server_result.workloads:
            workload.validation_summary = _summarize_validation(workload.results)
            workload.summary = _summarize_calls(workload.results)
            workload.valid_summary = _summarize_calls(workload.results, status_filter={"ok_valid"})
            workload.status = _derive_workload_status(workload)

        _write_debug_payloads(
            out_path=out_path,
            run_label=run_label,
            server_name=spec.name,
            workloads=server_result.workloads,
            debug_samples=debug_samples,
            min_bytes=min_bytes,
            min_items=min_items,
        )

        return server_result
    finally:
        _terminate(proc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run normalized MCP workloads across servers")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--phase-timeout", type=int, default=20)
    parser.add_argument("--call-timeout", type=int, default=10)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument(
        "--strict-validity",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enforce payload validity checks (default: true).",
    )
    parser.add_argument(
        "--min-bytes",
        action="append",
        default=[],
        help="Override min payload bytes per workload (WORKLOAD_ID=BYTES).",
    )
    parser.add_argument(
        "--min-items",
        action="append",
        default=[],
        help="Override min item count per workload (WORKLOAD_ID=COUNT).",
    )
    parser.add_argument("--server-filter", default=None)
    parser.add_argument(
        "--workloads",
        default=None,
        help="Comma-separated workload IDs to run (default: all)",
    )
    parser.add_argument(
        "--protocol-version",
        action="append",
        dest="protocol_versions",
        default=[],
        help="Protocol version to try for MCP initialize (repeatable). Default tries 2024-11-05 then latest.",
    )
    args = parser.parse_args()

    ok, err = _preflight_chat_db()
    if not ok:
        print(f"[{_ts()}] Preflight failed: {err}")
        print("Fix: grant Full Disk Access to your terminal and retry.")
        return 2

    protocol_versions = args.protocol_versions or ["2024-11-05", types.LATEST_PROTOCOL_VERSION]

    workloads_all = {
        "W0_UNREAD": WorkloadSpec(workload_id="W0_UNREAD", label="Unread messages (limit=1)"),
        "W1_RECENT": WorkloadSpec(workload_id="W1_RECENT", label="Recent messages / conversations"),
        "W2_SEARCH": WorkloadSpec(workload_id="W2_SEARCH", label="Keyword search (query=http)"),
        "W3_THREAD": WorkloadSpec(workload_id="W3_THREAD", label="Thread fetch for target conversation (limit=1)"),
    }
    if args.workloads:
        requested = {w.strip() for w in args.workloads.split(",") if w.strip()}
        workloads = {k: v for k, v in workloads_all.items() if k in requested}
    else:
        workloads = workloads_all

    try:
        min_bytes_overrides = _parse_overrides(args.min_bytes, label="min-bytes")
        min_items_overrides = _parse_overrides(args.min_items, label="min-items")
    except ValueError as exc:
        print(f"[{_ts()}] {exc}")
        return 2

    min_bytes = _build_thresholds(workloads, min_bytes_overrides, DEFAULT_MIN_BYTES, "BYTES")
    min_items = _build_thresholds(workloads, min_items_overrides, DEFAULT_MIN_ITEMS, "ITEMS")

    servers: List[McpServerSpec] = [
        McpServerSpec(
            name="brew MCP: cardmagic/messages (messages --mcp)",
            command="messages",
            args=["--mcp"],
            workload_map={
                "W1_RECENT": ToolCall("recent_messages", {"limit": 1}),
                "W2_SEARCH": ToolCall("search_messages", {"query": "http", "limit": 1}),
                "W3_THREAD": ToolCall("get_thread", {"contact": "__TARGET__", "limit": 1}),
            },
            target_selector=TargetSelector(
                tool=ToolCall("list_conversations", {"limit": 1}),
                kind="cardmagic_contact",
            ),
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
            workload_map={
                "W1_RECENT": ToolCall("get_recent_messages", {"limit": 1}),
                "W2_SEARCH": ToolCall("search_messages", {"query": "http", "limit": 1}),
                "W3_THREAD": ToolCall(
                    "get_messages_from_chat",
                    {"chatGuid": "__TARGET__", "limit": 1, "offset": 0},
                ),
            },
            target_selector=TargetSelector(
                tool=ToolCall("get_chats", {"limit": 1, "offset": 0}),
                kind="chat_guid",
            ),
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
            workload_map={
                "W1_RECENT": ToolCall("get_recent_messages", {"limit": 1}),
                "W2_SEARCH": ToolCall("search_messages", {"query": "http", "limit": 1}),
                "W3_THREAD": ToolCall("get_conversation_messages", {"chat_id": "__TARGET__", "limit": 1}),
            },
            target_selector=TargetSelector(
                tool=ToolCall("list_conversations", {"limit": 1, "offset": 0}),
                kind="chat_id",
            ),
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
            install_hint="Ensure iMCP.app is running with MCP Server enabled and Messages service activated.",
            workload_map={
                "W1_RECENT": ToolCall("messages_fetch", {"limit": 1}),
                "W2_SEARCH": ToolCall("messages_fetch", {"query": "http", "limit": 1}),
                "W3_THREAD": ToolCall("messages_fetch", {"participants": ["__TARGET__"], "limit": 1}),
            },
            target_selector=TargetSelector(
                tool=ToolCall("messages_fetch", {"limit": 1}),
                kind="imcp_sender",
            ),
        ),
        McpServerSpec(
            name="github MCP: TextFly/photon-imsg-mcp (node stdio)",
            command="node",
            args=[
                str(
                    REPO_ROOT
                    / "benchmarks"
                    / "vendor"
                    / "github_mcp"
                    / "photon-imsg-mcp"
                    / "dist"
                    / "index.js"
                )
            ],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "photon-imsg-mcp"),
            workload_map={
                "W0_UNREAD": ToolCall("photon_read_messages", {"limit": 1, "unreadOnly": True}),
                "W1_RECENT": ToolCall("photon_get_conversations", {"limit": 1}),
                "W3_THREAD": ToolCall("photon_read_messages", {"chatId": "__TARGET__", "limit": 1}),
            },
            target_selector=TargetSelector(
                tool=ToolCall("photon_get_conversations", {"limit": 1}),
                kind="photon_chat_id",
            ),
        ),
        McpServerSpec(
            name="github MCP: sameelarif/imessage-mcp (node tsx)",
            command=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "sameelarif-imessage-mcp"
                / "node_modules"
                / ".bin"
                / "tsx"
            ),
            args=["src/index.ts"],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "sameelarif-imessage-mcp"),
            workload_map={
                "W0_UNREAD": ToolCall("get-unread-messages", {}),
                "W1_RECENT": ToolCall("get-messages", {"limit": 1}),
                "W2_SEARCH": ToolCall("search-messages", {"query": "http", "limit": 1}),
                "W3_THREAD": ToolCall("get-conversation", {"contact": "__TARGET__", "limit": 1}),
            },
            target_selector=TargetSelector(
                tool=ToolCall("list-contacts", {"limit": 1}),
                kind="phone_number",
            ),
        ),
        McpServerSpec(
            name="github MCP: imessage-query-fastmcp-mcp-server (uv script)",
            command="uv",
            args=["run", "--script", "imessage-query-server.py"],
            cwd=str(
                REPO_ROOT
                / "benchmarks"
                / "vendor"
                / "github_mcp"
                / "imessage-query-fastmcp-mcp-server"
            ),
            workload_map={
                "W3_THREAD": ToolCall(
                    "get_chat_transcript",
                    {"phone_number": "__TARGET__"},
                ),
            },
        ),
        McpServerSpec(
            name="github MCP: mcp-imessage (node stdio)",
            command="node",
            args=[
                str(
                    REPO_ROOT
                    / "benchmarks"
                    / "vendor"
                    / "github_mcp"
                    / "mcp-imessage"
                    / "build"
                    / "index.js"
                )
            ],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "mcp-imessage"),
            env={"DATABASE_URL": str(Path.home() / "Library" / "Messages" / "chat.db")},
            workload_map={
                "W3_THREAD": ToolCall("get-recent-chat-messages", {"phoneNumber": "__TARGET__", "limit": 1}),
            },
        ),
        McpServerSpec(
            name="github MCP: imessage-mcp-improved (node stdio)",
            command="node",
            args=[
                str(
                    REPO_ROOT
                    / "benchmarks"
                    / "vendor"
                    / "github_mcp"
                    / "imessage-mcp-improved"
                    / "server"
                    / "index.js"
                )
            ],
            cwd=str(REPO_ROOT / "benchmarks" / "vendor" / "github_mcp" / "imessage-mcp-improved"),
            workload_map={
                "W0_UNREAD": ToolCall("get_unread_imessages", {"limit": 1}),
            },
        ),
    ]

    if args.server_filter:
        servers = [s for s in servers if args.server_filter.lower() in s.name.lower()]

    out_path = Path(args.output)
    run_label = _run_label_from_path(out_path)
    node_version = ""
    try:
        node_proc = subprocess.run(["node", "--version"], capture_output=True, text=True, check=False)
        if node_proc.returncode == 0:
            node_version = (node_proc.stdout or "").strip()
    except Exception:
        node_version = ""
    payload: dict = {
        "generated_at": _ts(),
        "metadata": {
            "mode": "session",
            "iterations": args.iterations,
            "warmup": args.warmup,
            "phase_timeout_s": args.phase_timeout,
            "call_timeout_s": args.call_timeout,
            "workloads": list(workloads.keys()),
            "run_label": run_label,
            "node_version": node_version,
            "validation": {
                "strict_validity": args.strict_validity,
                "min_bytes": min_bytes,
                "min_items": min_items,
                "max_payload_bytes": MAX_PAYLOAD_BYTES,
                "max_payload_tokens": MAX_PAYLOAD_TOKENS,
            },
        },
        "servers": [],
    }

    for spec in servers:
        print(f"\n== {spec.name} ==")

        cmd_is_path = (os.sep in spec.command) or spec.command.startswith(".")
        if cmd_is_path:
            if not Path(spec.command).exists():
                server_result = ServerRunResult(
                    name=spec.name,
                    command=spec.command,
                    args=spec.args,
                    mode="session",
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
                    mode="session",
                )
                server_result.notes.append(f"SKIPPED: command not in PATH: {spec.command}")
                payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
                payload["servers"].append(asdict(server_result))
                _write_json(out_path, payload)
                print(f"[{_ts()}] skipped: command not in PATH: {spec.command}")
                continue

        try:
            server_result = _run_session(
                spec,
                workloads,
                iterations=args.iterations,
                warmup=args.warmup,
                phase_timeout_s=args.phase_timeout,
                call_timeout_s=args.call_timeout,
                protocol_versions=protocol_versions,
                out_path=out_path,
                payload=payload,
                strict_validity=args.strict_validity,
                min_bytes=min_bytes,
                min_items=min_items,
                run_label=run_label,
            )
        except Exception as exc:
            server_result = ServerRunResult(
                name=spec.name,
                command=spec.command,
                args=spec.args,
                mode="session",
            )
            server_result.notes.append(f"exception: {exc}")

        payload["servers"] = [s for s in payload.get("servers") if (s.get("name") or "") != spec.name]
        payload["servers"].append(asdict(server_result))
        _write_json(out_path, payload)

        print("\nSummary:")
        if server_result.session_initialize:
            print("  session_initialize:", server_result.session_initialize.ok, f"{server_result.session_initialize.ms:.1f}ms")
        if server_result.session_list_tools:
            print("  session_list_tools:", server_result.session_list_tools.ok, f"{server_result.session_list_tools.ms:.1f}ms")
        for w in server_result.workloads:
            summary = _summarize_calls(w.results)
            print(f"  {w.workload_id}: {summary} status={w.status}")

    _write_headline_tables(payload, out_path)
    print(f"\nSaved results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
