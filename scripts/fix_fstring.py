#!/usr/bin/env python3
"""Fix f-string syntax errors in benchmark_all.py"""

from pathlib import Path

file_path = Path.home() / "benchmarks" / "imessage-mcp" / "scripts" / "benchmark_all.py"
content = file_path.read_text()

# Fix the escaped quote in f-strings
content = content.replace(r"{\' \'.join(command)}", r"{' '.join(command)}")

file_path.write_text(content)
print("✓ Fixed f-string syntax")
