#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TOOL_RE = re.compile(r"Benchmarking\s+([^\s]+)\s*(?:\(\d+/\d+\))?:")
TRACEBACK_START = "Traceback (most recent call last):"
MODULE_NOT_FOUND_RE = re.compile(r"\bModuleNotFoundError: .+")
IMPORT_ERROR_RE = re.compile(r"\bImportError: .+")
NODE_ERROR_RE = re.compile(
    r"^(Error|TypeError|ReferenceError)(?:\s+\[[^\]]+\])?:\s+.+"
)
STACK_LINE_RE = re.compile(r"^\s*at\s+.+")
DENO_ERROR_RE = re.compile(r"^\s*error:\s+.+")
DENO_UNCAUGHT_RE = re.compile(r"^\s*Uncaught\b.*")


def _add_error(
    errors: dict[str, list[str]],
    seen: dict[str, set[str]],
    tool: str | None,
    message: str,
) -> None:
    tool_name = tool or "unknown"
    if tool_name not in errors:
        errors[tool_name] = []
        seen[tool_name] = set()
    if message in seen[tool_name]:
        return
    errors[tool_name].append(message)
    seen[tool_name].add(message)


def _capture_traceback(lines: list[str], start_index: int) -> tuple[list[str], int]:
    block = [lines[start_index].rstrip("\n")]
    i = start_index + 1
    while i < len(lines) and len(block) < 20:
        if TOOL_RE.search(lines[i]):
            break
        block.append(lines[i].rstrip("\n"))
        i += 1
    return block, i


def _capture_stack(lines: list[str], start_index: int) -> tuple[list[str], int]:
    block = [lines[start_index].rstrip("\n")]
    i = start_index + 1
    while i < len(lines) and len(block) < 20:
        if STACK_LINE_RE.match(lines[i]):
            block.append(lines[i].rstrip("\n"))
            i += 1
            continue
        break
    return block, i


def extract_errors_from_log(log_path: Path) -> dict[str, list[str]]:
    """
    Extract Python tracebacks, Node errors, etc. from log files.

    Returns: {tool_name: [error_messages]}
    """
    errors: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    current_tool: str | None = None

    content = log_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        tool_match = TOOL_RE.search(line)
        if tool_match:
            current_tool = tool_match.group(1)
            i += 1
            continue

        if line.startswith(TRACEBACK_START):
            block, next_i = _capture_traceback(lines, i)
            message = "Full traceback:\n" + "\n".join(block)
            _add_error(errors, seen, current_tool, message)
            i = next_i
            continue

        if MODULE_NOT_FOUND_RE.search(line) or IMPORT_ERROR_RE.search(line):
            _add_error(errors, seen, current_tool, line.strip())
            i += 1
            continue

        stripped = line.strip()
        if NODE_ERROR_RE.match(stripped):
            block, next_i = _capture_stack(lines, i)
            message = "\n".join([b.strip() for b in block])
            _add_error(errors, seen, current_tool, message)
            i = next_i
            continue

        if DENO_ERROR_RE.match(stripped) or DENO_UNCAUGHT_RE.match(stripped):
            block, next_i = _capture_stack(lines, i)
            message = "\n".join([b.strip() for b in block])
            _add_error(errors, seen, current_tool, message)
            i = next_i
            continue

        i += 1

    return errors


def format_pretty(errors: dict[str, list[str]], log_path: Path | None = None) -> str:
    header_name = log_path.name if log_path else "log"
    lines: list[str] = [f"=== Errors Extracted from {header_name} ===", ""]

    if not errors:
        lines.append("No errors found.")
        lines.append("")
    else:
        for tool, messages in errors.items():
            lines.append(f"{tool}:")
            for message in messages:
                parts = message.splitlines()
                if len(parts) == 1:
                    lines.append(f"  - {parts[0]}")
                else:
                    lines.append(f"  - {parts[0]}")
                    for part in parts[1:]:
                        lines.append(f"    {part}")
            lines.append("")

    total_errors = sum(len(messages) for messages in errors.values())
    lines.append("=== Summary ===")
    lines.append(f"Total tools with errors: {len(errors)}")
    lines.append(f"Total errors found: {total_errors}")

    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract errors from benchmark logs")
    parser.add_argument("log_file", help="Path to log file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Save to file")

    args = parser.parse_args()

    log_path = Path(args.log_file).expanduser()
    errors = extract_errors_from_log(log_path)

    if args.json:
        output = json.dumps(errors, indent=2)
    else:
        output = format_pretty(errors, log_path)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output)
