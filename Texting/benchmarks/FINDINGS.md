# Benchmark Findings (Maximalist Competitor Sweep)

This file documents what we measured while validating the claim:
> “fastest end-to-end tool for LLMs to interface with iMessage”

“End-to-end” here means **tool runner end-to-end**:
- process spawn → command completes → stdout captured
- plus **LLM-facing output cost proxies** (stdout bytes, rough token estimate)

Canonical workload definitions live in `Texting/gateway/END_TO_END_BENCHMARKS.md`.

---

## Environment (important for honesty)

These numbers are **machine-specific** and vary with:
- Messages DB size and indexing
- macOS version + disk speed
- cold vs warm file cache
- Full Disk Access / permissions

Representative environment observed during these runs:
- Python 3.13.2
- Node v25.2.1 / npm 11.6.2 / npx 11.6.2
- macOS Messages `~/Library/Messages/chat.db` readable (Full Disk Access granted)

---

## Raw artifacts (reproducibility)

All results are written as JSON under `Texting/benchmarks/results/`.

Key files:
- Tier A (includes Wolfies gateway + jean-claude + imessage-exporter + imsg + messages):
  - `Texting/benchmarks/results/competitor_tier_a_with_imsg.json`
- Focused runs:
  - `Texting/benchmarks/results/competitor_imsg_only.json`
  - `Texting/benchmarks/results/competitor_osx_messages_exporter_only.json`
  - `Texting/benchmarks/results/competitor_messages_cli.json`
  - `Texting/benchmarks/results/competitor_npx_mcp_ready.json`

Installation reports (what was actually installable on this box):
- npm globals:
  - `Texting/benchmarks/results/install_report_npm_batch1.json`
- PyPI name-sweep:
  - `Texting/benchmarks/results/install_report_pip_all_score10.json`

---

## Quick headline results (what mattered most)

### steipete/imsg (native Swift CLI)

Built locally from source into a universal binary:
- `Texting/benchmarks/vendor/imsg/bin/imsg`

Focused benchmark: `Texting/benchmarks/results/competitor_imsg_only.json`

Highlights (median latency):
- `imsg --help`: ~**5.5ms**
- `imsg chats --limit 10 --json`: ~**66ms**
- `imsg history --chat-id <sample> --limit 10 --json`: ~**360ms**

Interpretation (honest):
- imsg **dominates cold-start startup** (native binary vs Python CLI).
- For “list chats/recent”, imsg is not obviously faster than Wolfies gateway in these runs.
- For “fetch last N messages”, imsg was **much slower** here than Wolfies `messages`/`bundle` paths.

### cfinke/OSX-Messages-Exporter (PHP exporter)

This is primarily a **bulk exporter to HTML**, not a bounded read API.

We installed PHP via Homebrew to make it runnable.

Focused benchmark: `Texting/benchmarks/results/competitor_osx_messages_exporter_only.json`
- `php …/messages-exporter.php --help`: ~**43ms median**

Interpretation:
- Not a direct threat to “LLM end-to-end tool” claims; it’s not designed for low-latency bounded queries.

### npm: `cardmagic/messages` (CLI/MCP)

Installed globally so it can run without `npx`.

Focused benchmark: `Texting/benchmarks/results/competitor_messages_cli.json`

Highlights (median latency):
- `messages --help`: ~**50ms**
- `messages recent --limit 10`: ~**62ms**
- `messages search http --limit 10 --context 0`: ~**642ms**

Interpretation:
- CLI is plausible competition for “agent-friendly UX”.
- Search path here is **~10× slower** than Wolfies keyword search on this box.
- Output is not JSON by default, which increases LLM parsing friction (and token overhead for schema discovery).

### npx MCP servers (stdio, long-lived processes)

Two Node packages behaved as **long-lived stdio servers**, not “help then exit” CLIs:
- `@iflow-mcp/imessage-mcp-server`
- `@foxychat-mcp/apple-imessages`

We benchmarked **time-to-ready** (spawn → prints readiness marker → terminated),
because `--help` does not exit for these tools.

Focused benchmark: `Texting/benchmarks/results/competitor_npx_mcp_ready.json`
- `@iflow-mcp/imessage-mcp-server`: ~**1000ms median** time-to-ready
- `@foxychat-mcp/apple-imessages`: ~**784ms median** time-to-ready

Interpretation (honest):
- Cold-spawn overhead is large relative to a ~50ms Python CLI call.
- This is **not yet** a full MCP end-to-end benchmark (initialize → tools/list → tools/call).
  To compare fairly, we need an MCP-protocol benchmark runner.

---

## Tier A comparative conclusions (what we can claim)

Tier A suite run:
- `Texting/benchmarks/results/competitor_tier_a_with_imsg.json`

The most defensible claim directionally supported by the data:
- Wolfies gateway is **very strong on “LLM end-to-end”** when measured as:
  - cold spawn time for bounded reads (unread/recent/search)
  - plus **output token overhead controls** (`--minimal`, `bundle`)
- imsg is faster at *starting*, but not clearly better at the multi-op “LLM workload”.
- `imessage-exporter` can be fast for search, but emits very large stdout for search
  (tens of KB → ~10k+ tokens), and its CLI lacks output limiting flags (fairness issue for LLM cost).

Important caveat:
- Any search benchmark that returns “no matches” will look artificially good on output cost.
  For fair “end-to-end LLM” claims, ensure the search query returns a consistent, bounded result set.

---

## Installation reality (part of “end-to-end”)

From `Texting/benchmarks/results/install_report_pip_all_score10.json`:
- Most “imessage-named” PyPI candidates installed successfully.
- Two failed:
  - `imessage-github-relay`: no matching distribution available (yanked / none published)
  - `ityou-imessage`: build failed on Python 3.13 due to ancient dependency syntax

This matters for public claims: “fastest” is meaningless if install is brittle.

---

## How to rerun (small, safe batches)

Install competitors (pip + npm), produces an auditable report:
```bash
python3 Texting/benchmarks/install_competitors.py --pip --npm
```

Run Tier A suite (3 iterations, read-only):
```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier a \
  --iterations 3 \
  --output Texting/benchmarks/results/competitor_tier_a_with_imsg.json
```

Run npx MCP readiness only (no-download mode):
```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier extended \
  --iterations 3 \
  --allow-npx \
  --tool-filter "npx MCP" \
  --output Texting/benchmarks/results/competitor_npx_mcp_ready.json
```

---

## Next (to make the Twitter claim bulletproof)

1) Add an MCP-protocol benchmark runner:
   - spawn MCP server
   - initialize
   - tools/list
   - tools/call for the canonical workloads
   - measure p50/p95 + stdout bytes / token proxy per call

2) Expand “thread fetch” to be apples-to-apples:
   - Wolfies: last N messages by contact / chat id
   - imsg: history by chat id
   - messages: thread/by-contact equivalent if available

3) Publish the raw JSON artifacts with the thread so readers can verify.

