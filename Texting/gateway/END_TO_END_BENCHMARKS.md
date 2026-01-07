# End-to-End Benchmark Suite (LLM ↔ iMessage)

This document defines a **public, reproducible** benchmark suite for measuring the *end-to-end* cost of an LLM interfacing with iMessage via a local tool.

The goal is to make “fastest end-to-end” a **defensible** claim by specifying:
- **Workloads** (what the LLM asks for)
- **Metrics** (what we measure)
- **Constraints** (what counts as fair)
- **Reporting format** (so others can reproduce and compare)

> Scope note: “End-to-end” here means **tool-runner end-to-end** (process start → tool output) plus **LLM-facing cost proxies** (output bytes/tokens). It does *not* include the model’s own reasoning time.

---

## Workloads (Canonical)

All workloads are **read-only by default**. The send workload is **opt-in**.

### W0: Unread
- **Unread count**: returns a count only.
- **Unread list**: returns a list of unread messages (bounded by `--limit`).

### W1: List chats / recent
- Recent chats / recent conversations (e.g., last 10).

### W2: Keyword search
- Search for a keyword (e.g., `"http"` or `"meeting"`).
- Bounded by `--limit`.

### W3: Fetch last N messages for a given chat/contact
- Fetch the last `N` messages for a specific contact/chat.
- Includes a variant that uses a **stable chat identifier** when possible.

### W4 (Optional): Attachments / links extraction
- Extract recent attachments and/or links (bounded by `--limit`).

### W5 (Opt-in): Send message
- Send a message to a **configured test destination** (often “self”).
- Must be opt-in because it creates real side effects.

---

## Inputs & Fairness Rules

### Limits and sampling
- Every workload must have a clear **limit** (10/20/50) to prevent “dump the DB” unfairness.
- If the tool requires a contact/chat id, the benchmark runner should:
  - pick a sample contact deterministically (e.g., first in contacts list), or
  - accept an override (`--contact`, `--chat-id`) for reproducibility.

### Cold vs warm
We report **both**:
- **Cold**: new process per call (common LLM tool-runner model).
- **Warm**: daemon mode (persistent process + cached DB connection).

### Output handling
We report:
- **runtime (stdout discarded)**: isolates compute/IO cost.
- **runtime (stdout captured)**: represents real tool-runner cost (data must be read).

---

## Metrics (Canonical)

### Performance
- **p50** latency (median)
- **p95** latency
- **mean** latency (useful, but p50/p95 matter more)
- **success rate** (% of runs returning exit code 0)
- **timeouts** (count)

### LLM-facing output cost proxies
Because LLM “end-to-end” is often dominated by output size:
- **stdout bytes** (captured)
- **approx token estimate**

Token estimate should be clearly labeled as approximate, e.g.:
- `approx_tokens = ceil(stdout_bytes / 4)`

This is not exact, but is directionally useful and reproducible.

---

## Reporting Format

Benchmark runners should emit machine-readable JSON including:
- tool name + version
- workload name
- config (iterations, timeouts, cold/warm)
- latency distribution (p50/p95/mean/min/max/std)
- stdout bytes + approx tokens
- success rate

---

## Current Implementations / Raw Data

- Gateway CLI suite: `Texting/gateway/benchmarks.py` + `Texting/gateway/benchmark_results.json`
- Bundle workload: `python3 Texting/gateway/imessage_client.py bundle --json --compact ...`
- Daemon warm-path suite: `python3 Texting/gateway/benchmarks.py --quick --include-daemon --json`
- Competitor suite (PyPI sweep): `Texting/benchmarks/competitor_benchmarks.py`
- Flattened CSV output: `Texting/benchmarks/competitor_benchmarks.csv`

---

## Why This Suite Exists

For LLM tool integrations, “fastest” is not just:
- executing a SQL query quickly

It is:
- **cold-start latency** (process + imports)
- **repeat-call latency** (daemon/persistence)
- **output size** (LLM ingest cost)
- **reliability** (timeouts and failures kill UX)

This suite is meant to measure all of the above in a way that others can reproduce.
