#!/usr/bin/env python3
"""
Reindex RAG with proper contact name resolution.

Clears existing index and reindexes all recent messages with
contact names from macOS Contacts.

Usage:
    python3 scripts/reindex_rag.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import MessageRetriever


def main():
    """Clear and reindex RAG."""
    print("=" * 60)
    print("iMessage RAG Reindex")
    print("=" * 60)

    # Initialize retriever
    print("\nInitializing retriever...")
    retriever = MessageRetriever(
        persist_directory=str(Path(__file__).parent.parent / "data" / "chroma"),
        contacts_config=str(Path(__file__).parent.parent / "config" / "contacts.json"),
    )

    # Show current stats
    stats = retriever.get_stats()
    print(f"\nCurrent index: {stats.get('chunk_count', 0)} chunks")

    # Clear existing
    print("\nClearing existing index...")
    deleted = retriever.clear_index()
    print(f"Deleted {deleted} chunks")

    # Reindex with 90 days
    print("\nIndexing messages (last 90 days)...")
    added = retriever.index_recent_messages(days=90, limit=1000)
    print(f"Added {added} new chunks")

    # Show new stats
    stats = retriever.get_stats()
    print(f"\nNew index stats:")
    print(f"  Chunks: {stats.get('chunk_count', 0)}")
    print(f"  Contacts: {len(stats.get('contacts', []))}")
    print(f"  Date range: {stats.get('oldest_date', 'N/A')} to {stats.get('newest_date', 'N/A')}")

    if stats.get("contacts"):
        print(f"\nIndexed contacts:")
        for contact in sorted(stats.get("contacts", []))[:15]:
            print(f"    {contact}")
        if len(stats.get("contacts", [])) > 15:
            print(f"    ... and {len(stats.get('contacts', [])) - 15} more")

    print("\n✓ Reindex complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
