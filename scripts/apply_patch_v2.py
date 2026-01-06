#!/usr/bin/env python3
"""Apply Codex patch to benchmark_all.py with careful section-by-section approach"""

import re
from pathlib import Path

benchmark_file = Path.home() / "benchmarks" / "imessage-mcp" / "scripts" / "benchmark_all.py"
content = benchmark_file.read_text()

# 1. Add validation functions after ensure_output_dir
validation_funcs = '''

def validate_cli_startup(cli_path: Path, timeout_s: int = 5) -> tuple[bool, str]:
    """Validate CLI can start and respond to --help."""

    command = [sys.executable, str(cli_path), "--help"]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=timeout_s,
            check=False,
        )

        if result.returncode != 0:
            return False, f"Exit code {result.returncode}: {result.stderr[:200]}"

        if "usage:" not in result.stdout.lower():
            return False, "No usage info in --help output"

        return True, result.stdout[:100]
    except subprocess.TimeoutExpired:
        return False, f"--help timed out after {timeout_s}s"
    except Exception as exc:
        return False, f"Exception: {exc}"


def validate_cli_basic_commands(cli_path: Path, timeout_s: int = 10) -> list[tuple[str, bool, str]]:
    """Test basic CLI commands to identify which fail."""

    test_commands = [
        (["contacts", "--json"], "list_contacts"),
        (["recent", "--limit", "5", "--json"], "recent_messages"),
    ]

    results = []
    for args, name in test_commands:
        command = [sys.executable, str(cli_path)] + args
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=timeout_s,
                check=False,
            )

            success = result.returncode == 0
            message = "OK" if success else f"Exit {result.returncode}: {result.stderr[:100]}"
            results.append((name, success, message))
        except subprocess.TimeoutExpired:
            results.append((name, False, f"Timeout after {timeout_s}s"))
        except Exception as exc:
            results.append((name, False, f"Exception: {exc}"))

    return results
'''

# Insert after ensure_output_dir function
pattern = r'(def ensure_output_dir\(path: Path\) -> None:.*?path\.mkdir\(parents=True, exist_ok=True\))'
replacement = r'\1' + validation_funcs
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# 2. Update resolve_benchmark_context signature
content = content.replace(
    'def resolve_benchmark_context(cli_path: Path, settings: BenchmarkSettings) -> BenchmarkContext:',
    'def resolve_benchmark_context(cli_path: Path | None, settings: BenchmarkSettings) -> BenchmarkContext:'
)

# 3. Update cli_base assignment
content = content.replace(
    '    cli_base = [sys.executable, str(cli_path)]',
    '    cli_base = [sys.executable, str(cli_path)] if cli_path else None'
)

# 4. Add cli_base check to contact resolution
content = re.sub(
    r'(\s+)if not contact_name:\n(\s+)contacts = run_cli_json',
    r'\1if not contact_name and cli_base:\n\2contacts = run_cli_json',
    content
)

# 5. Add cli_base check to group resolution
content = re.sub(
    r'(\s+)if not group_id:\n(\s+)groups = run_cli_json',
    r'\1if not group_id and cli_base:\n\2groups = run_cli_json',
    content
)

# 6. Update subprocess.Popen in _cli_operation
content = content.replace(
    '            proc = subprocess.Popen(\n                command,\n                stdout=subprocess.DEVNULL,\n                stderr=subprocess.PIPE,\n                text=True,',
    '            proc = subprocess.Popen(\n                command,\n                stdout=subprocess.PIPE,\n                stderr=subprocess.PIPE,\n                stdin=subprocess.DEVNULL,\n                text=True,'
)

# 7. Add debug logging before subprocess
content = re.sub(
    r'(\s+command = self\.config\.command \+ args)\n(\s+start = time\.perf_counter\(\))',
    r'\1\n        print(f"[DEBUG] Running: {\' \'.join(command)}", file=sys.stderr)\n\2',
    content
)

# 8. Add stdout/stderr initialization
content = re.sub(
    r'(\s+success = False)\n(\s+proc: subprocess\.Popen)',
    r'\1\n        stdout = ""\n        stderr = ""\n\n\2',
    content
)

# 9. Update error handling in subprocess block
old_except = '''            else:
                error = stderr.strip() if stderr else "process_error"
        except Exception as exc:
            error = exc
            try:
                if proc:
                    proc.kill()
            except Exception:
                pass'''

new_except = '''            else:
                if stderr:
                    error = stderr.strip()
                elif stdout:
                    error = stdout.strip()
                else:
                    error = "process_error"
        except subprocess.TimeoutExpired as exc:
            error = exc
            try:
                if proc:
                    proc.kill()
            except Exception:
                pass
            if proc:
                try:
                    stdout, stderr = proc.communicate(timeout=1)
                except Exception:
                    stdout, stderr = "", ""
            if stdout:
                print(f"[DEBUG] Timeout stdout: {stdout[:200]}", file=sys.stderr)
            if stderr:
                print(f"[DEBUG] Timeout stderr: {stderr[:200]}", file=sys.stderr)
        except Exception as exc:
            error = exc
            try:
                if proc:
                    proc.kill()
            except Exception:
                pass
            if proc:
                try:
                    stdout, stderr = proc.communicate(timeout=1)
                except Exception:
                    stdout, stderr = "", ""'''

content = content.replace(old_except, new_except)

# 10. Update main() function
old_main_section = '''    context = resolve_benchmark_context(CLI_PATH, settings)
    tools = build_tool_configs(tool_filter=args.tools)'''

new_main_section = '''    tools = build_tool_configs(tool_filter=args.tools)

    cli_path_for_context: Path | None = None
    cli_configs = [config for config in tools if config.name == "Our CLI"]
    if cli_configs:
        cli_path_for_context = cli_configs[0].entrypoint
        print("\\n=== Validating CLI ===")

        if cli_path_for_context is None:
            print("FAIL CLI validation failed: Missing entrypoint path")
            print("\\nSkipping CLI benchmarks.")
            tools = [config for config in tools if config.name != "Our CLI"]
            cli_path_for_context = None
        else:
            success, message = validate_cli_startup(cli_path_for_context, settings.timeout_s)
            if not success:
                print(f"FAIL CLI validation failed: {message}")
                print("\\nSkipping CLI benchmarks.")
                tools = [config for config in tools if config.name != "Our CLI"]
                cli_path_for_context = None
            else:
                print("OK CLI starts successfully")

                print("\\nTesting basic commands:")
                test_results = validate_cli_basic_commands(cli_path_for_context, settings.timeout_s)
                for name, success, message in test_results:
                    status = "OK" if success else "FAIL"
                    print(f"  {status} {name}: {message}")

        print("=" * 40 + "\\n")

    context = resolve_benchmark_context(cli_path_for_context, settings)'''

content = content.replace(old_main_section, new_main_section)

# Write back
benchmark_file.write_text(content)
print("✓ Patch applied successfully!")
print(f"  Modified: {benchmark_file}")
print(f"  Backup at: {benchmark_file}.backup")
