# Competitor Discovery (GitHub/PyPI/Web)

This document captures what we can (and cannot) discover automatically about potential iMessage tooling competitors to add to the benchmark suite.

## How discovery works

Discovery is performed by `Texting/benchmarks/discover_competitors.py`, which queries:

- **GitHub**: public search API (`search/repositories`)
- **npm**: public registry search API
- **crates.io**: public API search
- **PyPI**: **name-based matching only** using the canonical `/simple/` index (see limitation below)

Example run:

```bash
python3 Texting/benchmarks/discover_competitors.py \
  --out Texting/benchmarks/results/discovery.json
```

## Key limitations (important)

### PyPI “full text search” is not available

- PyPI disabled XML-RPC search (the old `pip search` backend).
- The human-facing search endpoint is bot-protected and does not return results in a scrape-friendly way.
- Result: we can **only** discover packages whose **names** match a substring (via `/simple/`), not packages where only the *description* mentions iMessage.

If we want “true PyPI full-text search” again, we’d need an external index/service (or a maintained curated list).

### GitHub search is rate-limited

- The GitHub search API is rate limited, especially unauthenticated.
- Set `GITHUB_TOKEN` to increase coverage and reduce the chance of partial results.

## What to add to benchmarks (shortlist)

Below are high-signal candidates that commonly show up in discovery results, and are plausible additions for “fastest end-to-end LLM ↔ iMessage interface”.

### Likely benchmark-worthy (CLI or MCP server)

- `steipete/imsg` (GitHub): CLI for Messages.app (agent-friendly positioning).
- `ReagentX/imessage-exporter` (GitHub + crates.io + Homebrew): Rust CLI exporter/diagnostics; already a strong “narrow fast tool” comparator.
- `cfinke/OSX-Messages-Exporter` (GitHub): older but popular exporter; useful for historical/compatibility comparison.
- `cardmagic/messages` (GitHub + npm): explicitly positioned as **CLI and MCP server** for Messages (high relevance).
- `marissamarym/imessage-mcp-server` (GitHub / PyPI variants): an MCP server worth comparing with “properly configured MCP”.
- `tchbw/mcp-imessage`, `wyattjoh/imessage-mcp`, `carterlasalle/mac_messages_mcp` (GitHub): already in the MCP benchmark set, but should remain in the canonical list.

### npm MCP servers to consider (new surface area)

Discovery frequently finds npm packages that claim to be MCP servers for iMessage/Messages:

- `@iflow-mcp/imessage-mcp-server`
- `@foxychat-mcp/apple-imessages`
- `@cardmagic/messages`

These are worth evaluating because they may be the “real competition” if the ecosystem shifts toward Node MCP servers.

### “Library/parsing only” (not directly comparable, but useful for ceilings)

- `imessage-parser` (npm): parser for `attributedBody` format.
- `imessage-database` (crate): iMessage SQLite parsers.
- Python libs like `imessage-reader` (PyPI): fast import, but not an end-to-end tool without a CLI/integration layer.

## Next steps (recommended)

1. Convert the shortlist into a **Tier A+** benchmark set:
   - include at least one **fast narrow tool** (e.g., `imessage-exporter`)
   - include at least one **agent-oriented CLI** (e.g., `imsg`)
   - include 1–3 **npm MCP servers** that are actually usable non-interactively
2. For each candidate, determine benchability:
   - Does `--help` return immediately (no TUI)?
   - Are there read-only commands comparable to: unread / recent / search / thread?
   - Can it run without external services?
3. Expand the benchmark harness to support non-Python competitors cleanly:
   - isolate install/setup (Homebrew/npm/cargo) from timing runs
   - ensure stdout handling matches LLM tool runners (capture output vs discard)

