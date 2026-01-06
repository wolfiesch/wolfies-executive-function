"""
Progressive validation system for CLI tools.

Stages:
1) startup   - basic launch (--help)
2) args      - argument parsing check
3) operation - single execution produces output
4) data      - output JSON matches expected schema
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


@dataclass
class ValidationResult:
    """Result of a single validation stage."""
    stage: str  # "startup", "args", "operation", "data"
    success: bool
    elapsed_ms: float
    error_message: Optional[str] = None
    stderr_output: Optional[str] = None
    command_run: Optional[list[str]] = None


@dataclass
class ToolValidation:
    """Complete validation report for a tool."""
    tool_name: str
    stages: list[ValidationResult]
    overall_success: bool
    recommended_action: str  # "benchmark", "skip", "debug"


@dataclass
class CommandResult:
    """Captured execution result for a CLI invocation."""
    command: list[str]
    stdout: str
    stderr: str
    returncode: int
    elapsed_ms: float
    timed_out: bool = False


class ToolValidator:
    """Progressive validation for CLI tools."""

    def __init__(self, cli_path: Path, timeout: int = 30):
        self.cli_path = cli_path
        self.timeout = timeout
        self.results_dir = Path("results/validation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.expected_fields_by_operation = {
            "search": ["results", "matches", "items"],
            "query": ["results", "items", "data"],
            "list": ["items", "results", "data"],
            "stats": ["stats", "total", "count"],
            "index": ["indexed", "count", "total"],
            "fetch": ["items", "data", "results"],
            "get": ["item", "data", "result"],
            "read": ["item", "data", "result"],
        }
        self.default_expected_fields = [
            "data",
            "results",
            "items",
            "messages",
            "records",
            "entries",
            "stats",
            "count",
            "total",
            "output",
            "response",
        ]

    def validate_tool(self, operations: list[str]) -> ToolValidation:
        """Run all 4 validation stages for a tool."""
        stages: list[ValidationResult] = []

        # Stage 1: Startup
        startup_result = self.validate_startup()
        stages.append(startup_result)
        if not startup_result.success:
            return ToolValidation(
                tool_name=str(self.cli_path),
                stages=stages,
                overall_success=False,
                recommended_action="debug",
            )

        # Stage 2-4: For each operation
        for operation in operations:
            args_result = self.validate_arguments(operation)
            stages.append(args_result)
            if not args_result.success:
                continue

            op_result = self.validate_operation(operation)
            stages.append(op_result)
            if not op_result.success:
                continue

            data_result = self.validate_data_structure(operation)
            stages.append(data_result)

        overall_success = startup_result.success and any(
            s.success for s in stages if s.stage in ["operation", "data"]
        )

        return ToolValidation(
            tool_name=str(self.cli_path),
            stages=stages,
            overall_success=overall_success,
            recommended_action="benchmark" if overall_success else "debug",
        )

    def validate_startup(self) -> ValidationResult:
        """Stage 1: Can tool start? (--help test, 5s timeout)."""
        command = [str(self.cli_path), "--help"]
        result = self._run_command(command, timeout=min(5, self.timeout))
        if result.timed_out:
            error_message = self._format_timeout_message(
                stage="startup",
                command=result.command,
                timeout_seconds=min(5, self.timeout),
                stdout=result.stdout,
                stderr=result.stderr,
            )
            self._write_debug_log(
                operation="startup",
                stage="startup",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="startup",
                result=result,
                error_message=error_message,
            )

        if result.returncode != 0:
            error_message = self._format_error_message(
                failure="Startup check failed (--help)",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Tool returned a non-zero exit code on --help.",
                recommendation="Ensure the CLI is executable and dependencies are installed.",
            )
            self._write_debug_log(
                operation="startup",
                stage="startup",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="startup",
                result=result,
                error_message=error_message,
            )

        return ValidationResult(
            stage="startup",
            success=True,
            elapsed_ms=result.elapsed_ms,
            command_run=result.command,
        )

    def validate_arguments(self, operation: str) -> ValidationResult:
        """Stage 2: Does it accept arguments? (10s timeout)."""
        command = self._build_command(operation)
        result = self._run_command(command, timeout=min(10, self.timeout))

        if result.timed_out:
            error_message = self._format_timeout_message(
                stage="args",
                command=result.command,
                timeout_seconds=min(10, self.timeout),
                stdout=result.stdout,
                stderr=result.stderr,
            )
            self._write_debug_log(
                operation=operation,
                stage="args",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="args",
                result=result,
                error_message=error_message,
            )

        if self._is_argparse_error(result.stderr):
            error_message = self._format_error_message(
                failure=f"Argument parsing failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="CLI rejected the provided arguments.",
                recommendation="Verify the subcommand and flags; run with --help to confirm usage.",
            )
            self._write_debug_log(
                operation=operation,
                stage="args",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="args",
                result=result,
                error_message=error_message,
            )

        if result.returncode != 0:
            error_message = self._format_error_message(
                failure=f"Argument validation failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Command exited with a non-zero status while validating arguments.",
                recommendation="Confirm the operation syntax and required parameters.",
            )
            self._write_debug_log(
                operation=operation,
                stage="args",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="args",
                result=result,
                error_message=error_message,
            )

        return ValidationResult(
            stage="args",
            success=True,
            elapsed_ms=result.elapsed_ms,
            command_run=result.command,
        )

    def validate_operation(self, operation: str) -> ValidationResult:
        """Stage 3: Single execution returns data? (30s timeout)."""
        command = self._build_command(operation)
        result = self._run_command(command, timeout=self.timeout)

        if result.timed_out:
            error_message = self._format_timeout_message(
                stage="operation",
                command=result.command,
                timeout_seconds=self.timeout,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            self._write_debug_log(
                operation=operation,
                stage="operation",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="operation",
                result=result,
                error_message=error_message,
            )

        if result.returncode != 0:
            error_message = self._format_error_message(
                failure=f"Operation execution failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Command returned a non-zero exit code during execution.",
                recommendation="Run the command manually to inspect the runtime error.",
            )
            self._write_debug_log(
                operation=operation,
                stage="operation",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="operation",
                result=result,
                error_message=error_message,
            )

        if not result.stdout.strip():
            error_message = self._format_error_message(
                failure=f"No output produced for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Command ran but produced no stdout output.",
                recommendation="Ensure the operation returns data and does not require extra flags.",
            )
            self._write_debug_log(
                operation=operation,
                stage="operation",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="operation",
                result=result,
                error_message=error_message,
            )

        return ValidationResult(
            stage="operation",
            success=True,
            elapsed_ms=result.elapsed_ms,
            command_run=result.command,
        )

    def validate_data_structure(self, operation: str) -> ValidationResult:
        """Stage 4: Output matches expected schema? (30s timeout)."""
        command = self._build_command(operation)
        result = self._run_command(command, timeout=self.timeout)

        if result.timed_out:
            error_message = self._format_timeout_message(
                stage="data",
                command=result.command,
                timeout_seconds=self.timeout,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            self._write_debug_log(
                operation=operation,
                stage="data",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="data",
                result=result,
                error_message=error_message,
            )

        if result.returncode != 0:
            error_message = self._format_error_message(
                failure=f"Data validation failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Command returned a non-zero exit code before JSON validation.",
                recommendation="Fix the runtime error before validating JSON schema.",
            )
            self._write_debug_log(
                operation=operation,
                stage="data",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="data",
                result=result,
                error_message=error_message,
            )

        if not result.stdout.strip():
            error_message = self._format_error_message(
                failure=f"No JSON output produced for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis="Command completed but returned an empty payload.",
                recommendation="Ensure the operation emits JSON to stdout.",
            )
            self._write_debug_log(
                operation=operation,
                stage="data",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="data",
                result=result,
                error_message=error_message,
            )

        parsed, parse_error = self._parse_json_output(result.stdout)
        if parse_error:
            error_message = self._format_error_message(
                failure=f"JSON parsing failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis=f"JSON decoder error: {parse_error}",
                recommendation="Ensure the tool emits valid JSON with double quotes and no trailing commas.",
            )
            self._write_debug_log(
                operation=operation,
                stage="data",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="data",
                result=result,
                error_message=error_message,
            )

        expected_fields = self._expected_fields_for_operation(operation)
        schema_ok, schema_error = self._validate_schema(parsed, expected_fields)
        if not schema_ok:
            error_message = self._format_error_message(
                failure=f"Schema validation failed for '{operation}'",
                command=result.command,
                stderr=result.stderr,
                stdout=result.stdout,
                diagnosis=schema_error,
                recommendation="Align the output structure with the expected JSON fields.",
            )
            self._write_debug_log(
                operation=operation,
                stage="data",
                command=result.command,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=error_message,
            )
            return self._failure_result(
                stage="data",
                result=result,
                error_message=error_message,
            )

        return ValidationResult(
            stage="data",
            success=True,
            elapsed_ms=result.elapsed_ms,
            command_run=result.command,
        )

    def _run_command(self, command: list[str], timeout: int) -> CommandResult:
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            return CommandResult(
                command=command,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                returncode=completed.returncode,
                elapsed_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return CommandResult(
                command=command,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                returncode=-1,
                elapsed_ms=elapsed_ms,
                timed_out=True,
            )

    def _build_command(self, operation: str) -> list[str]:
        tokens = shlex.split(operation) if operation else []
        if tokens:
            if tokens[0] == str(self.cli_path) or Path(tokens[0]).name == self.cli_path.name:
                return tokens
        return [str(self.cli_path)] + tokens

    def _is_argparse_error(self, stderr: str) -> bool:
        if not stderr:
            return False
        lowered = stderr.lower()
        return any(
            marker in lowered
            for marker in [
                "error: argument",
                "error: unrecognized arguments",
                "invalid choice",
                "the following arguments are required",
            ]
        )

    def _format_error_message(
        self,
        *,
        failure: str,
        command: list[str],
        stderr: str,
        stdout: str,
        diagnosis: str,
        recommendation: str,
    ) -> str:
        command_str = self._format_command(command)
        excerpt = self._excerpt(stderr or stdout)
        return "\n".join(
            [
                f"What failed: {failure}",
                f"Command: {command_str}",
                f"Error output: {excerpt}",
                f"Diagnosis: {diagnosis}",
                f"Recommendation: {recommendation}",
            ]
        )

    def _format_timeout_message(
        self,
        *,
        stage: str,
        command: list[str],
        timeout_seconds: int,
        stdout: str,
        stderr: str,
    ) -> str:
        command_str = self._format_command(command)
        excerpt = self._excerpt(stderr or stdout)
        return "\n".join(
            [
                f"What failed: {stage} stage timed out after {timeout_seconds}s",
                f"Command: {command_str}",
                f"Error output: {excerpt}",
                "Diagnosis: The command did not complete before the timeout.",
                "Recommendation: Increase the timeout or optimize the command runtime.",
            ]
        )

    def _parse_json_output(self, output: str) -> tuple[Optional[Any], Optional[str]]:
        try:
            return json.loads(output), None
        except json.JSONDecodeError as exc:
            return None, str(exc)

    def _expected_fields_for_operation(self, operation: str) -> list[str]:
        lowered = operation.lower()
        tokens = shlex.split(lowered) if lowered else []
        primary = tokens[0] if tokens else ""
        if primary in self.expected_fields_by_operation:
            return self.expected_fields_by_operation[primary]
        for key, fields in self.expected_fields_by_operation.items():
            if key in lowered:
                return fields
        return self.default_expected_fields

    def _validate_schema(self, parsed: Any, expected_fields: list[str]) -> tuple[bool, str]:
        if isinstance(parsed, dict):
            if not parsed:
                return False, "JSON object is empty; expected data fields."
            if any(field in parsed for field in expected_fields):
                return True, ""
            return (
                False,
                f"Missing expected fields. Expected one of: {', '.join(expected_fields)}.",
            )

        if isinstance(parsed, list):
            if not parsed:
                return False, "JSON list is empty; expected at least one record."
            first = parsed[0]
            if isinstance(first, dict):
                if any(field in first for field in expected_fields):
                    return True, ""
                return (
                    False,
                    "List items missing expected fields. "
                    f"Expected one of: {', '.join(expected_fields)}.",
                )
            return True, ""

        return False, f"Unsupported JSON type: {type(parsed).__name__}."

    def _excerpt(self, text: str, max_len: int = 400) -> str:
        if not text:
            return "<empty>"
        clean = text.strip()
        if len(clean) <= max_len:
            return clean
        return f"{clean[:max_len]}...[truncated]"

    def _format_command(self, command: list[str]) -> str:
        try:
            return shlex.join(command)
        except AttributeError:
            return " ".join(shlex.quote(part) for part in command)

    def _safe_operation_name(self, operation: str) -> str:
        base = operation.strip().lower() if operation else "operation"
        safe = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
        return safe or "operation"

    def _write_debug_log(
        self,
        *,
        operation: str,
        stage: str,
        command: list[str],
        stdout: str,
        stderr: str,
        error_message: str,
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_operation = self._safe_operation_name(operation)
        log_path = self.results_dir / f"debug_{safe_operation}_{timestamp}.log"
        command_str = self._format_command(command)
        log_lines = [
            f"timestamp: {datetime.now().isoformat()}",
            f"stage: {stage}",
            f"operation: {operation}",
            f"command: {command_str}",
            "",
            "stdout:",
            stdout.strip() or "<empty>",
            "",
            "stderr:",
            stderr.strip() or "<empty>",
            "",
            "error_message:",
            error_message or "<none>",
        ]
        log_path.write_text("\n".join(log_lines))

    def _failure_result(
        self,
        *,
        stage: str,
        result: CommandResult,
        error_message: str,
    ) -> ValidationResult:
        return ValidationResult(
            stage=stage,
            success=False,
            elapsed_ms=result.elapsed_ms,
            error_message=error_message,
            stderr_output=result.stderr,
            command_run=result.command,
        )
