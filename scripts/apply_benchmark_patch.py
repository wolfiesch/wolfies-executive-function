#!/usr/bin/env python3
"""Apply the Codex-generated patch to benchmark_all.py"""

from pathlib import Path

# Read the current file
benchmark_file = Path.home() / "benchmarks" / "imessage-mcp" / "scripts" / "benchmark_all.py"
content = benchmark_file.read_text()

# Split into lines for easier manipulation
lines = content.split('\n')

# Find insertion points
ensure_output_dir_end = None
resolve_benchmark_start = None
cli_operation_start = None
main_start = None

for i, line in enumerate(lines):
    if 'def ensure_output_dir(path: Path)' in line:
        # Find end of this function (next function or blank lines)
        for j in range(i+1, len(lines)):
            if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                ensure_output_dir_end = j
                break
            elif lines[j].startswith('def '):
                ensure_output_dir_end = j
                break

    if 'def resolve_benchmark_context(' in line:
        resolve_benchmark_start = i

    if 'def _cli_operation(self, operation: str, iteration: int)' in line:
        cli_operation_start = i

    if 'def main(' in line:
        main_start = i

print(f"Found ensure_output_dir_end at line {ensure_output_dir_end}")
print(f"Found resolve_benchmark_context at line {resolve_benchmark_start}")
print(f"Found _cli_operation at line {cli_operation_start}")
print(f"Found main at line {main_start}")

# Prepare the new validation functions
validation_functions = '''
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

# Insert validation functions after ensure_output_dir
if ensure_output_dir_end:
    lines.insert(ensure_output_dir_end, validation_functions)

# Update resolve_benchmark_context signature
if resolve_benchmark_start:
    for i in range(resolve_benchmark_start, min(resolve_benchmark_start + 10, len(lines))):
        if 'def resolve_benchmark_context(' in lines[i]:
            lines[i] = lines[i].replace(
                'def resolve_benchmark_context(cli_path: Path, settings: BenchmarkSettings)',
                'def resolve_benchmark_context(cli_path: Path | None, settings: BenchmarkSettings)'
            )
            break

# Update resolve_benchmark_context body
if resolve_benchmark_start:
    for i in range(resolve_benchmark_start, min(resolve_benchmark_start + 50, len(lines))):
        if 'cli_base = [sys.executable, str(cli_path)]' in lines[i]:
            lines[i] = '    cli_base = [sys.executable, str(cli_path)] if cli_path else None'
        elif 'if not contact_name:' in lines[i] and 'cli_base' not in lines[i]:
            lines[i] = '    if not contact_name and cli_base:'
        elif 'if not group_id:' in lines[i] and 'cli_base' not in lines[i]:
            lines[i] = '    if not group_id and cli_base:'

# Find and update _cli_operation method
if cli_operation_start:
    # Find the subprocess.Popen call
    for i in range(cli_operation_start, min(cli_operation_start + 100, len(lines))):
        # Add debug logging before start = time.perf_counter()
        if 'command = self.config.command + args' in lines[i]:
            lines.insert(i+1, '        print(f"[DEBUG] Running: {\' \'.join(command)}", file=sys.stderr)')

        # Update stdout handling
        if 'stdout=subprocess.DEVNULL,' in lines[i]:
            lines[i] = lines[i].replace('stdout=subprocess.DEVNULL,', 'stdout=subprocess.PIPE,')

        # Add stdin=subprocess.DEVNULL after stderr
        if 'stderr=subprocess.PIPE,' in lines[i] and 'stdin' not in lines[i]:
            lines.insert(i+1, '                stdin=subprocess.DEVNULL,')

        # Initialize stdout and stderr variables
        if 'success = False' in lines[i] and 'stdout = ""' not in lines[i+1]:
            lines.insert(i+1, '        stdout = ""')
            lines.insert(i+2, '        stderr = ""')

        # Update except subprocess.TimeoutExpired block
        if 'except Exception as exc:' in lines[i] and i > cli_operation_start + 40:
            # Insert the new timeout handling
            timeout_handler = '''        except subprocess.TimeoutExpired as exc:
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
'''
            lines[i] = timeout_handler
            break

# Find main() and add CLI validation
if main_start:
    for i in range(main_start, min(main_start + 200, len(lines))):
        if 'context = resolve_benchmark_context(CLI_PATH, settings)' in lines[i]:
            # Replace with new logic
            new_main_logic = '''    tools = build_tool_configs(tool_filter=args.tools)

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

    context = resolve_benchmark_context(cli_path_for_context, settings)
'''
            # Remove old lines
            if 'tools = build_tool_configs(tool_filter=args.tools)' in lines[i-1]:
                lines[i-1] = ''
            lines[i] = new_main_logic
            break

# Write back
output = '\n'.join(lines)
benchmark_file.write_text(output)

print(f"\nPatch applied successfully to {benchmark_file}")
print("Changes:")
print("  - Added validate_cli_startup() function")
print("  - Added validate_cli_basic_commands() function")
print("  - Updated _cli_operation() with better subprocess handling")
print("  - Updated resolve_benchmark_context() signature")
print("  - Added pre-flight CLI validation in main()")
