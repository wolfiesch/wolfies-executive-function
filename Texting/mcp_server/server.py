"""
Compatibility shim for the archived MCP server.

This keeps local imports from resolving to unrelated global packages and
provides deprecation signals for migration tests. To restore the full MCP
server, see `mcp_server_archive/ARCHIVED.md`.
"""

from __future__ import annotations

app = object()


def _archived_notice() -> None:
    """Raise an error indicating the MCP server is archived."""
    raise RuntimeError(
        "MCP server is archived. See mcp_server_archive/ARCHIVED.md to restore."
    )


async def handle_index_messages(*_args, **_kwargs):
    """
    ⚠️ DEPRECATED: index_messages is deprecated.

    Use index_knowledge(source="imessage") instead.
    """
    _archived_notice()


async def handle_ask_messages(*_args, **_kwargs):
    """
    ⚠️ DEPRECATED: ask_messages is deprecated.

    Use search_knowledge instead.
    """
    _archived_notice()


async def handle_migrate_rag_data(*_args, **_kwargs):
    """Compatibility stub for the migration tool handler."""
    _archived_notice()


if __name__ == "__main__":
    raise SystemExit(
        "MCP server is archived. See mcp_server_archive/ARCHIVED.md to restore."
    )
