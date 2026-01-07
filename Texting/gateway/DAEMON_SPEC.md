# iMessage Daemon Mode (Python) — Spec v1

Status: **draft, implement now**

Goal: make “fastest end-to-end for LLMs” a defensible claim by minimizing:
- cold per-call overhead (imports, SQLite open, contact parsing)
- stdout bytes / token overhead
- failure rate / hanging behavior

This spec focuses on **Python daemon + thin Python client**. Native client is out of scope for v1.

Related docs:
- Canonical workload suite: `Texting/gateway/END_TO_END_BENCHMARKS.md`
- High-level daemon rationale: `Texting/gateway/DAEMON_DESIGN.md`

---

## 1) Definitions

**End-to-end (tool-runner) latency**:
- process spawn (client) → connect to daemon → daemon executes → client prints stdout

**Warm**:
- daemon already running, SQLite connection/caches hot

**Cold**:
- daemon not running (or caches cold). In v1 we do **not** auto-start by default.

---

## 2) Architecture

### Components

1) **Daemon process** (long-lived)
- Owns:
  - SQLite connection(s) to `~/Library/Messages/chat.db` (read-only)
  - prepared queries and lightweight caches
  - output shaping (minimal/compact/fields/max_text_chars)

2) **Thin client** (spawn-per-call, stdlib only)
- Owns:
  - argument parsing
  - unix socket connect + request/response
  - stdout printing (LLM-facing output)

### Transport

- UNIX domain socket:
  - default path: `~/.wolfies-imessage/daemon.sock`
  - permissions: `0600` (owner only)

### Concurrency model

v1: **single-request-at-a-time** server (sequential)
- simplest correctness (SQLite + TCC)
- predictable p95
- matches real LLM tool runners (rarely concurrent on a single machine)

Future: ThreadingMixIn + lock or async queue if needed.

---

## 3) Protocol (NDJSON)

Framing: one JSON object per line (newline-delimited JSON).

### Request

```json
{"id":"uuid","v":1,"method":"bundle","params":{"include":"unread_count,recent"}}
```

- `id`: string, unique per request (client-generated)
- `v`: protocol version integer (v1)
- `method`: string
- `params`: object (method-specific)

### Response

```json
{"id":"uuid","ok":true,"result":{...},"error":null,"meta":{"server_ms":12.3,"protocol_v":1}}
```

- `ok`: boolean
- `result`: any JSON value (present when ok=true)
- `error`: object or null (present when ok=false)
- `meta.server_ms`: time spent in the daemon (not including client spawn)

### Error object

```json
{"code":"INVALID_PARAMS","message":"limit must be 1..500","details":{"limit":0}}
```

---

## 4) Methods (v1)

All methods are **read-only by default**. “Send” is explicitly out of scope for v1.

### `health`
Params: `{}`  
Result:
```json
{"pid":123,"started_at":"...","version":"...","socket":"...","chat_db":"...","can_read_db":true}
```

### `unread_count`
Params: `{}`  
Result: `{ "count": 123 }`

### `unread_messages`
Params:
```json
{"limit":20,"minimal":true,"max_text_chars":120}
```
Result: `{"messages":[...]}`

### `recent`
Params:
```json
{"limit":10,"minimal":true,"max_text_chars":120}
```
Result: `{"messages":[...]}`

### `text_search`
Params:
```json
{"query":"http","limit":20,"since":"2026-01-01","minimal":true,"max_text_chars":120}
```
Result: `{"results":[...]}`

### `messages_by_phone`
Params:
```json
{"phone":"+14155551234","limit":20,"minimal":true,"max_text_chars":120}
```
Result: `{"messages":[...]}`

### `bundle`
Params:
```json
{
  "include":"meta,unread_count,unread_messages,recent,search,contact_messages",
  "unread_limit":20,
  "recent_limit":10,
  "query":"http",
  "search_limit":20,
  "contact":null,
  "phone":null,
  "messages_limit":20,
  "since":null,
  "days":null,
  "search_scoped_to_contact":false,
  "minimal":true,
  "compact":false,
  "fields":null,
  "max_text_chars":120
}
```
Result: same shape as the CLI `bundle --json` output.

---

## 5) Output shaping rules (LLM cost control)

The daemon applies the same output controls as the CLI:
- `minimal`: default preset fields (`date, phone, is_from_me, text` + `match_snippet` when relevant) and default truncation
- `compact`: minified JSON output and compact default fields
- `fields`: explicit allowlist overrides presets
- `max_text_chars`: truncates large text fields (text/match_snippet/etc.)

Design rule: daemon returns a full JSON response wrapper, but the thin client may print:
- default: `response.result` only (lowest token cost)
- optional: `--raw-response` prints wrapper for debugging

---

## 6) Lifecycle / CLI

### Daemon commands (manual)

- `python3 Texting/gateway/imessage_daemon.py start [--foreground]`
- `python3 Texting/gateway/imessage_daemon.py stop`
- `python3 Texting/gateway/imessage_daemon.py status`

### Thin client commands (LLM tool runner)

- `python3 Texting/gateway/imessage_daemon_client.py unread --limit 20 --minimal`
- `python3 Texting/gateway/imessage_daemon_client.py bundle --minimal --query http --search-limit 20`

v1 does **not** auto-start the daemon on demand (TCC/Full Disk Access pitfalls).

---

## 7) macOS permissions (TCC caveat)

The daemon must be started from an environment that has **Full Disk Access** to read:
- `~/Library/Messages/chat.db`

Background launchers (launchd) may not inherit the same access; v1 assumes “start from terminal”.

---

## 8) Benchmarks (acceptance criteria)

Add a warm-daemon benchmark suite that measures:
- p50/p95 for each canonical read workload
- stdout bytes + token proxy
- success rate

We explicitly report:
- `daemon_start_ms` (one-time)
- `warm_call_ms` (per call)

Existing benchmark hook:
```bash
python3 Texting/gateway/benchmarks.py --quick --include-daemon --json
```

Acceptance for “v1 is worth it”:
- warm call p50 improves vs direct CLI for at least unread/recent/search on the same machine
- success rate remains ~100% (no hangs)

---

## 9) Testing (v1)

Unit tests (no Messages DB required):
- protocol parsing/framing (NDJSON)
- dispatcher (unknown method, invalid params)
- client prints `result` by default

Integration tests (macOS-only, optional):
- run if chat.db readable; otherwise skip
