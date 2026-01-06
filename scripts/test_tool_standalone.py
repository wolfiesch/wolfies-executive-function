#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional


@dataclass
class TestResult:
    """Result of testing a tool."""

    tool_name: str
    tests_passed: int
    tests_failed: int
    errors: list[str]
    recommendations: list[str]


@dataclass
class StageResult:
    name: str
    success: bool
    message: str
    output: str | None = None
    skipped: bool = False


@dataclass(frozen=True)
class ToolConfigView:
    name: str
    tool_type: str
    command: list[str]
    cwd: Path | None
    env: dict[str, str] | None
    entrypoint: Path | None


PY_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):")
PY_IMPORT_RE = re.compile(r"(ModuleNotFoundError|ImportError):\s*(.+)")
NODE_ERROR_RE = re.compile(r"^(Error|TypeError|ReferenceError|SyntaxError):\s+.+", re.MULTILINE)
NODE_MODULE_RE = re.compile(r"(Cannot find module|MODULE_NOT_FOUND)")
DENO_ERROR_RE = re.compile(r"(error:|Uncaught)", re.IGNORECASE)

SAFE_TOOL_ALIASES = [
    "list_contacts",
    "contacts",
    "get_contacts",
    "recent_messages",
    "recent",
    "unread",
    "groups",
    "list_groups",
    "list_chats",
    "search",
    "search_messages",
    "semantic_search",
    "analytics",
    "stats",
]


def _install_stub_module(name: str, attrs: dict[str, Any] | None = None) -> None:
    parts = name.split(".")
    for index in range(1, len(parts) + 1):
        module_name = ".".join(parts[:index])
        if module_name not in sys.modules:
            module = ModuleType(module_name)
            if index < len(parts):
                module.__path__ = []
            sys.modules[module_name] = module
            if index > 1:
                parent = sys.modules[".".join(parts[:index - 1])]
                setattr(parent, parts[index - 1], module)
    if attrs:
        module = sys.modules[name]
        for key, value in attrs.items():
            setattr(module, key, value)


def _load_benchmark_module(path: Path) -> Any:
    missing_modules: dict[str, dict[str, Any] | None] = {
        "numpy": None,
        "psutil": None,
        "tqdm": {"tqdm": lambda *args, **kwargs: []},
        "mcp": {"ClientSession": type("ClientSession", (), {})},
        "mcp.client.stdio": {
            "StdioServerParameters": type("StdioServerParameters", (), {}),
            "stdio_client": lambda *args, **kwargs: None,
        },
    }

    stubs_added: list[str] = []
    for module_name, attrs in missing_modules.items():
        try:
            __import__(module_name)
        except ImportError:
            _install_stub_module(module_name, attrs)
            stubs_added.append(module_name)

    try:
        import importlib.util

        module_name = f"benchmark_all_{int(time.time())}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load benchmark module at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for module_name in stubs_added:
            if module_name in sys.modules:
                del sys.modules[module_name]


def load_tool_configs() -> list[ToolConfigView]:
    benchmark_path = Path(__file__).with_name("benchmark_all.py")
    if not benchmark_path.exists():
        fallback = Path.home() / "benchmarks" / "imessage-mcp" / "scripts" / "benchmark_all.py"
        if fallback.exists():
            benchmark_path = fallback
        else:
            raise FileNotFoundError(f"benchmark_all.py not found at {benchmark_path}")

    module = _load_benchmark_module(benchmark_path)
    tool_configs = module.build_tool_configs()
    return [
        ToolConfigView(
            name=config.name,
            tool_type=config.tool_type,
            command=list(config.command),
            cwd=config.cwd,
            env=dict(config.env) if config.env else None,
            entrypoint=config.entrypoint,
        )
        for config in tool_configs
    ]


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def find_tool_config(tool_name: str, tools: list[ToolConfigView]) -> ToolConfigView | None:
    for tool in tools:
        if tool.name == tool_name:
            return tool
    normalized = normalize_name(tool_name)
    for tool in tools:
        if normalize_name(tool.name) == normalized:
            return tool
    for tool in tools:
        if normalized in normalize_name(tool.name):
            return tool
    return None


def resolve_executable(command: str) -> str | None:
    path = Path(command)
    if path.is_absolute() or path.parent != Path("."):
        if path.exists():
            return str(path)
        return None
    return shutil.which(command)


def build_env(config_env: dict[str, str] | None) -> dict[str, str] | None:
    if not config_env:
        return None
    env = os.environ.copy()
    env.update(config_env)
    return env


def run_command(
    command: list[str],
    timeout: int,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int | None, str, str, bool]:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr, False
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or "", exc.stderr or "", True


def probe_process(
    command: list[str],
    wait_s: float,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int | None, str, str, bool]:
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(timeout=wait_s)
        return proc.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        return proc.returncode, stdout, stderr, True


def summarize_output(output: str) -> str:
    if not output:
        return "Unknown error"
    for pattern in (PY_IMPORT_RE, NODE_ERROR_RE, NODE_MODULE_RE, DENO_ERROR_RE):
        match = pattern.search(output)
        if match:
            return match.group(0).strip()
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[0] if lines else "Unknown error"


def extract_error_signatures(output: str) -> list[str]:
    signatures: list[str] = []
    if not output:
        return signatures
    if PY_TRACEBACK_RE.search(output):
        signatures.append("Traceback detected")
    for match in PY_IMPORT_RE.finditer(output):
        signatures.append(match.group(0).strip())
    for match in NODE_ERROR_RE.finditer(output):
        signatures.append(match.group(0).strip())
    if NODE_MODULE_RE.search(output):
        signatures.append("Node module resolution error")
    if DENO_ERROR_RE.search(output):
        signatures.append("Deno runtime error")
    if "Permission" in output or "permission" in output:
        signatures.append("Permission error")
    return signatures


def collect_recommendations(
    errors: list[str],
    outputs: list[str],
    config: ToolConfigView | None,
) -> list[str]:
    combined = "\n".join(errors + outputs)
    recs: list[str] = []

    if "missing_executable" in combined or "Executable missing" in combined:
        if config:
            recs.append(f"Install or expose `{config.command[0]}` on PATH")
        else:
            recs.append("Install the required runtime and ensure it is on PATH")
    if "missing_entrypoint" in combined or "Entrypoint missing" in combined:
        if config and config.entrypoint:
            recs.append(f"Verify entrypoint exists: {config.entrypoint}")
        recs.append("Ensure the repo is checked out and build artifacts exist")
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        recs.append("Check PYTHONPATH includes the repository root")
        if config and config.cwd:
            recs.append(f"Try: pip install -e {config.cwd}")
    if "Node module resolution error" in combined or "Cannot find module" in combined:
        if config and config.cwd:
            recs.append(f"Run npm install in {config.cwd}")
        recs.append("Rebuild the project (npm run build / pnpm build)")
    if "Deno runtime error" in combined or "deno" in combined:
        if config and config.entrypoint:
            recs.append(f"Run: deno cache {config.entrypoint}")
        recs.append("Check Deno permissions and dependency cache")
    if "permission" in combined.lower():
        recs.append("Grant Full Disk Access to the terminal running the tool")
    if "mcp package not available" in combined:
        recs.append("Install MCP client support: pip install mcp")

    deduped: list[str] = []
    for rec in recs:
        if rec not in deduped:
            deduped.append(rec)
    return deduped


def build_args_from_schema(schema: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    if not schema:
        return {}, None
    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []

    contact = os.getenv("IMESSAGE_BENCH_CONTACT") or os.getenv("IMESSAGE_BENCH_PHONE")
    args: dict[str, Any] = {}

    for name in required:
        key = name.lower()
        if key in {"query", "search", "text"}:
            args[name] = "test"
        elif key in {"limit", "count", "n"}:
            args[name] = 5
        elif key in {"hours"}:
            args[name] = 24
        elif key in {"days"}:
            args[name] = 7
        elif key in {"contact", "recipient", "handle", "phone"}:
            if contact:
                args[name] = contact
        elif key in {"group_id", "chat_id"}:
            group_id = os.getenv("IMESSAGE_BENCH_GROUP_ID")
            if group_id:
                args[name] = group_id
        elif key in {"message", "body", "content"}:
            args[name] = "diagnostic test"
        elif name in properties and "default" in properties[name]:
            args[name] = properties[name]["default"]

    missing = [name for name in required if name not in args]
    if missing:
        return None, f"missing_required_args: {', '.join(missing)}"
    return args, None


def select_basic_tool(tools: list[Any]) -> tuple[str | None, dict[str, Any] | None]:
    if not tools:
        return None, None
    normalized_tools = [(normalize_name(tool.name), tool) for tool in tools]

    for alias in SAFE_TOOL_ALIASES:
        for normalized, tool in normalized_tools:
            if alias == normalized or alias in normalized:
                return tool.name, tool.inputSchema

    for _, tool in normalized_tools:
        schema = tool.inputSchema
        required = (schema or {}).get("required", []) if schema else []
        if not required:
            return tool.name, tool.inputSchema

    return None, None


async def mcp_list_tools(
    command: list[str],
    cwd: Path | None,
    env: dict[str, str] | None,
    timeout: int,
) -> Any:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=command[0],
        args=command[1:],
        cwd=str(cwd) if cwd else None,
        env=env,
    )
    async with asyncio.timeout(timeout):
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await session.list_tools()


async def mcp_call_tool(
    command: list[str],
    cwd: Path | None,
    env: dict[str, str] | None,
    timeout: int,
    tool_name: str,
    args: dict[str, Any],
) -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=command[0],
        args=command[1:],
        cwd=str(cwd) if cwd else None,
        env=env,
    )
    async with asyncio.timeout(timeout):
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                await session.call_tool(tool_name, args)


def test_tool(tool_name: str, timeout: int = 10) -> TestResult:
    """
    Test tool can start and respond to basic operations.

    Tests:
    1. Executable/entrypoint exists
    2. Tool can start (no import errors)
    3. MCP handshake works (list tools)
    4. Basic operation succeeds

    Returns structured result with errors.
    """

    stages: list[StageResult] = []
    errors: list[str] = []
    outputs: list[str] = []

    if not tool_name:
        result = TestResult(
            tool_name="(missing)",
            tests_passed=0,
            tests_failed=4,
            errors=["Tool name is required"],
            recommendations=["Provide a tool name from benchmark_all.py"],
        )
        result._stages = stages
        return result

    try:
        tools = load_tool_configs()
    except Exception as exc:
        message = f"Failed to load tool configs: {exc}"
        result = TestResult(
            tool_name=tool_name,
            tests_passed=0,
            tests_failed=4,
            errors=[message],
            recommendations=["Verify benchmark_all.py and its dependencies"],
        )
        stages.extend(
            [
                StageResult("Executable exists", False, "Skipped (config load failed)", skipped=True),
                StageResult("Tool startup", False, "Skipped (config load failed)", skipped=True),
                StageResult("MCP handshake", False, "Skipped (config load failed)", skipped=True),
                StageResult("Basic operation", False, "Skipped (config load failed)", skipped=True),
            ]
        )
        result._stages = stages
        return result

    config = find_tool_config(tool_name, tools)
    if not config:
        result = TestResult(
            tool_name=tool_name,
            tests_passed=0,
            tests_failed=4,
            errors=[f"Tool not found: {tool_name}"],
            recommendations=["Use a tool name from benchmark_all.py"],
        )
        stages.extend(
            [
                StageResult("Executable exists", False, "Skipped (unknown tool)", skipped=True),
                StageResult("Tool startup", False, "Skipped (unknown tool)", skipped=True),
                StageResult("MCP handshake", False, "Skipped (unknown tool)", skipped=True),
                StageResult("Basic operation", False, "Skipped (unknown tool)", skipped=True),
            ]
        )
        result._stages = stages
        return result

    env = build_env(config.env)

    # Stage 1: executable/entrypoint exists
    exec_path = resolve_executable(config.command[0])
    missing: list[str] = []
    if not exec_path:
        missing.append(f"Executable missing: {config.command[0]}")
        errors.append("missing_executable")
    if config.entrypoint and not config.entrypoint.exists():
        missing.append(f"Entrypoint missing: {config.entrypoint}")
        errors.append("missing_entrypoint")

    if missing:
        stages.append(StageResult("Executable exists", False, "; ".join(missing)))
        stages.append(StageResult("Tool startup", False, "Skipped (executable missing)", skipped=True))
        stages.append(StageResult("MCP handshake", False, "Skipped (startup failed)", skipped=True))
        stages.append(StageResult("Basic operation", False, "Skipped (startup failed)", skipped=True))
        result = TestResult(
            tool_name=config.name,
            tests_passed=0,
            tests_failed=4,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    stages.append(StageResult("Executable exists", True, exec_path or config.command[0]))

    # Stage 2: tool can start
    startup_ok = False
    startup_output = ""
    if config.tool_type == "cli":
        code, stdout, stderr, timed_out = run_command(
            config.command + ["--help"], timeout, cwd=config.cwd, env=env
        )
        startup_output = (stdout or "") + ("\n" + stderr if stderr else "")
        if timed_out:
            startup_ok = False
            errors.append("startup timeout")
        elif code == 0:
            startup_ok = True
        else:
            startup_ok = False
    else:
        code, stdout, stderr, timed_out = probe_process(
            config.command, min(2, timeout), cwd=config.cwd, env=env
        )
        startup_output = (stdout or "") + ("\n" + stderr if stderr else "")
        if timed_out and not extract_error_signatures(startup_output):
            startup_ok = True
        elif code == 0 and not extract_error_signatures(startup_output):
            startup_ok = False
            errors.append("process exited immediately")
        else:
            startup_ok = False

    if not startup_ok:
        summary = summarize_output(startup_output)
        stages.append(StageResult("Tool startup", False, summary, startup_output.strip() or None))
        errors.extend(extract_error_signatures(startup_output))
        outputs.append(startup_output)
        stages.append(StageResult("MCP handshake", False, "Skipped (startup failed)", skipped=True))
        stages.append(StageResult("Basic operation", False, "Skipped (startup failed)", skipped=True))
        result = TestResult(
            tool_name=config.name,
            tests_passed=1,
            tests_failed=3,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    stages.append(StageResult("Tool startup", True, "OK"))

    # Stage 3: MCP handshake or CLI skip
    tools_response = None
    if config.tool_type != "mcp":
        stages.append(StageResult("MCP handshake", False, "Skipped (non-MCP tool)", skipped=True))
        code, stdout, stderr, timed_out = run_command(
            config.command + ["contacts", "--json"], timeout, cwd=config.cwd, env=env
        )
        output = (stdout or "") + ("\n" + stderr if stderr else "")
        if timed_out:
            stages.append(StageResult("Basic operation", False, "Timed out", output.strip() or None))
            errors.append("basic operation timeout")
            outputs.append(output)
        elif code == 0:
            stages.append(StageResult("Basic operation", True, "contacts --json"))
        else:
            stages.append(StageResult("Basic operation", False, summarize_output(output), output.strip() or None))
            errors.extend(extract_error_signatures(output))
            outputs.append(output)
        passed = sum(1 for stage in stages if stage.success)
        result = TestResult(
            tool_name=config.name,
            tests_passed=passed,
            tests_failed=4 - passed,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    try:
        tools_response = asyncio.run(
            mcp_list_tools(config.command, config.cwd, env, timeout)
        )
        tool_count = len(getattr(tools_response, "tools", []))
        stages.append(StageResult("MCP handshake", True, f"list_tools returned {tool_count} tools"))
    except Exception as exc:
        probe_code, stdout, stderr, _ = probe_process(
            config.command, min(2, timeout), cwd=config.cwd, env=env
        )
        output = (stdout or "") + ("\n" + stderr if stderr else "")
        message = f"{exc}"
        stages.append(StageResult("MCP handshake", False, message, output.strip() or None))
        errors.append(message)
        outputs.append(output)

    if tools_response is None:
        stages.append(StageResult("Basic operation", False, "Skipped (handshake failed)", skipped=True))
        passed = sum(1 for stage in stages if stage.success)
        result = TestResult(
            tool_name=config.name,
            tests_passed=passed,
            tests_failed=4 - passed,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    # Stage 4: basic operation (MCP)
    tool_name_choice, schema = select_basic_tool(tools_response.tools)
    if not tool_name_choice:
        stages.append(StageResult("Basic operation", False, "Skipped (no safe tool found)", skipped=True))
        passed = sum(1 for stage in stages if stage.success)
        result = TestResult(
            tool_name=config.name,
            tests_passed=passed,
            tests_failed=4 - passed,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    args, arg_error = build_args_from_schema(schema)
    if arg_error:
        stages.append(StageResult("Basic operation", False, f"Skipped ({arg_error})", skipped=True))
        errors.append(arg_error)
        passed = sum(1 for stage in stages if stage.success)
        result = TestResult(
            tool_name=config.name,
            tests_passed=passed,
            tests_failed=4 - passed,
            errors=errors,
            recommendations=collect_recommendations(errors, outputs, config),
        )
        result._stages = stages
        return result

    try:
        asyncio.run(
            mcp_call_tool(
                config.command,
                config.cwd,
                env,
                timeout,
                tool_name_choice,
                args or {},
            )
        )
        stages.append(StageResult("Basic operation", True, f"call_tool {tool_name_choice}"))
    except Exception as exc:
        probe_code, stdout, stderr, _ = probe_process(
            config.command, min(2, timeout), cwd=config.cwd, env=env
        )
        output = (stdout or "") + ("\n" + stderr if stderr else "")
        stages.append(StageResult("Basic operation", False, f"{exc}", output.strip() or None))
        errors.append(str(exc))
        outputs.append(output)

    passed = sum(1 for stage in stages if stage.success)
    result = TestResult(
        tool_name=config.name,
        tests_passed=passed,
        tests_failed=4 - passed,
        errors=errors,
        recommendations=collect_recommendations(errors, outputs, config),
    )
    result._stages = stages
    return result


def print_result(result: TestResult) -> None:
    print(f"Testing: {result.tool_name}")
    print("=" * 46)

    stages: list[StageResult] = getattr(result, "_stages", [])
    for stage in stages:
        marker = "✓" if stage.success else "✗"
        print(f"{marker} {stage.name}: {stage.message}")
        if stage.output:
            print("\n  Error output:")
            print(textwrap.indent(stage.output.strip(), "  "))
            print()

    print(f"Results: {result.tests_passed}/4 tests passed")

    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"- {rec}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test competitor tools")
    parser.add_argument("tool", nargs="?", help="Tool name to test")
    parser.add_argument("--all", action="store_true", help="Test all failed tools")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout per test")

    args = parser.parse_args()

    if args.all:
        failed_tools = [
            "Our CLI",
            "carterlasalle/mac_messages_mcp",
            "wyattjoh/imessage-mcp",
            "tchbw/mcp-imessage",
            "shirhatti/mcp-server-imessage",
            "jonmmease/jons-mcp-imessage",
        ]
        for tool in failed_tools:
            result = test_tool(tool, args.timeout)
            print_result(result)
        return 0

    result = test_tool(args.tool, args.timeout)
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
