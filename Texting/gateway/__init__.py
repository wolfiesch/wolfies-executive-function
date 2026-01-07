"""Gateway CLI for iMessage operations."""

from pathlib import Path

# Version management
try:
    from .__version__ import __version__
except ImportError:
    __version__ = "4.0.0"

__all__ = ["__version__"]
