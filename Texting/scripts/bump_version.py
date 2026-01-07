#!/usr/bin/env python3
"""Bump version across all package files.

Usage:
    python scripts/bump_version.py major  # 4.0.0 -> 5.0.0
    python scripts/bump_version.py minor  # 4.0.0 -> 4.1.0
    python scripts/bump_version.py patch  # 4.0.0 -> 4.0.1
"""

import sys
import re
import json
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_current_version():
    """Read current version from __version__.py."""
    version_file = get_project_root() / "gateway" / "__version__.py"

    if not version_file.exists():
        print(f"Error: {version_file} not found")
        sys.exit(1)

    content = version_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)

    if not match:
        print(f"Error: Could not parse version from {version_file}")
        sys.exit(1)

    return match.group(1)


def bump_version(current_version: str, level: str) -> str:
    """Bump version based on level (major, minor, patch)."""
    major, minor, patch = map(int, current_version.split('.'))

    if level == 'major':
        return f"{major + 1}.0.0"
    elif level == 'minor':
        return f"{major}.{minor + 1}.0"
    elif level == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"Error: Invalid level '{level}'. Use: major, minor, or patch")
        sys.exit(1)


def update_version_file(new_version: str):
    """Update gateway/__version__.py."""
    version_file = get_project_root() / "gateway" / "__version__.py"
    content = version_file.read_text()

    # Update __version__
    content = re.sub(
        r'__version__\s*=\s*["\'][0-9]+\.[0-9]+\.[0-9]+["\']',
        f'__version__ = "{new_version}"',
        content
    )

    # Update __version_info__
    major, minor, patch = new_version.split('.')
    content = re.sub(
        r'__version_info__\s*=\s*\([0-9]+,\s*[0-9]+,\s*[0-9]+\)',
        f'__version_info__ = ({major}, {minor}, {patch})',
        content
    )

    version_file.write_text(content)
    print(f"✅ Updated {version_file}")


def update_json_file(file_path: Path, new_version: str):
    """Update version in a JSON file."""
    if not file_path.exists():
        print(f"⚠️  Skipped {file_path} (not found)")
        return

    content = json.loads(file_path.read_text())

    # Update version field (handles both flat and nested structures)
    if 'version' in content:
        content['version'] = new_version

    # Handle marketplace.json (nested structure)
    if 'plugins' in content:
        for plugin in content['plugins']:
            if 'version' in plugin:
                plugin['version'] = new_version

    file_path.write_text(json.dumps(content, indent=2) + '\n')
    print(f"✅ Updated {file_path}")


def main():
    """Main entry point."""
    if len(sys.argv) != 2 or sys.argv[1] not in ['major', 'minor', 'patch']:
        print(__doc__)
        print("\nError: Invalid usage")
        print("Usage: python scripts/bump_version.py [major|minor|patch]")
        sys.exit(1)

    level = sys.argv[1]
    root = get_project_root()

    # Read current version
    current_version = read_current_version()
    print(f"\n📦 Current version: {current_version}")

    # Calculate new version
    new_version = bump_version(current_version, level)
    print(f"📦 New version: {new_version} ({level} bump)\n")

    # Confirm
    response = input(f"Bump version from {current_version} to {new_version}? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        sys.exit(0)

    print()

    # Update all files
    update_version_file(new_version)
    update_json_file(root / ".claude-plugin" / "plugin.json", new_version)
    update_json_file(root / ".claude-plugin" / "marketplace.json", new_version)

    print(f"\n✨ Version bumped to {new_version}")
    print("\nNext steps:")
    print(f"  1. git add -A")
    print(f"  2. git commit -m 'chore: bump version to {new_version}'")
    print(f"  3. git tag v{new_version}")
    print(f"  4. python3 -m build  # Rebuild distribution")


if __name__ == "__main__":
    main()
