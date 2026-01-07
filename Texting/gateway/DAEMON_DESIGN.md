# Daemon + (Optional) Native Client: Design Notes

Goal: minimize **end-to-end** latency for LLM tool calls, where the common execution model is:
1) tool runner spawns a process
2) process does the work
3) stdout is captured and returned to the LLM

The two biggest latency buckets are:
- **process startup/import time**
- **database/query time + JSON serialization**

---

## Can we combine a native binary with a daemon?

Yes, and it can make sense depending on your tool-runner model.

There are three viable architectures:

### Option A: Python CLI only (current)
LLM tool call → `python3 …/imessage_client.py <cmd>` → stdout JSON

- Pros: simplest, already fast (~40–55ms p50 for core reads on this machine)
- Cons: pays Python startup/import on every call

### Option B: Python daemon + Python client
LLM tool call → `python3 wolfies-imessage <cmd>` (thin client) → UNIX socket → daemon → stdout JSON

- Pros: daemon can keep SQLite connection + caches warm
- Cons: still pays Python startup/import in the client per tool call

### Option C: Python daemon + native client (best “spawn-per-call” end-to-end)
LLM tool call → `wolfies-imessage <cmd>` (native) → UNIX socket → daemon → stdout JSON

- Pros: avoids Python startup/import on the client side while keeping warm caches in daemon
- Cons: more engineering complexity (build/distribution), but still smaller than rewriting the whole stack in native

### Option D: native daemon + native client (max performance, max effort)
Same as Option C, but daemon is also native.

- Pros: highest ceiling
- Cons: biggest rewrite; you must re-implement parsing/logic/edge cases

---

## Expected speeds (honest ranges)

These are practical ranges, not promises. The real floor is SQLite query cost + OS scheduling.

### Current (Python CLI, cold spawn per call)
Observed in this repo’s benchmarks:
- core reads: ~40–55ms p50

### Python daemon (warm) + Python client (spawn per call)
Likely improvement: remove re-init work inside the “server”, but still pay Python client startup.
- p50 often lands ~25–45ms depending on how thin the client is

### Python daemon (warm) + native client (spawn per call)
This is the sweet spot if your tool runner must spawn a fresh process each call.
- p50 plausible: ~8–25ms for small reads (unread/recent/search)
- p95 plausible: ~15–45ms

### Native daemon + native client (spawn per call)
Best case if you’re chasing absolute numbers.
- p50 plausible: ~3–12ms
- p95 plausible: ~8–25ms

Why not lower? Because:
- SQLite queries aren’t free (especially unread/search joins on large DBs)
- JSON serialization and copying bytes to stdout costs time
- OS scheduling jitter shows up in p95

---

## Why daemon mode helps

Daemon mode can keep these hot:
- SQLite connection (avoid open/close cost)
- prepared statements
- contact resolution cache
- optional caches like “recent chats list” for very short windows

It also enables batching:
- one request can return `{unread_count, unread_messages}` instead of two tool calls

Batching is often the biggest “LLM end-to-end” win because it reduces:
- process spawns
- output parsing work
- token costs

---

## Proposed daemon RPC shape

Transport:
- UNIX domain socket at `~/.wolfies-imessage/daemon.sock`

Request:
```json
{"id":"uuid","method":"unread","params":{"limit":20}}
```

Response:
```json
{"id":"uuid","ok":true,"result":{...},"meta":{"stdout_bytes":1234}}
```

Design rules:
- strict read-only by default
- send operations opt-in and clearly labeled
- stable, compact JSON (minimize token cost)

---

## Validation

Use the end-to-end suite defined in:
- `Texting/gateway/END_TO_END_BENCHMARKS.md`

Implementation spec (Python v1):
- `Texting/gateway/DAEMON_SPEC.md`

Measure:
- cold spawn (client) p50/p95
- warm daemon p50/p95
- stdout bytes + approximate tokens

Only claim “fastest end-to-end” after:
- rerunning GitHub MCP suite with the canonical workloads
- rerunning PyPI Tier A with the canonical workloads
- publishing raw JSON outputs for reproducibility
