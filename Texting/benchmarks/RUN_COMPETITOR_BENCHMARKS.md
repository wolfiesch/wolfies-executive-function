# Running Competitor Benchmarks (Safe + Observable)

This suite is designed to avoid the “hours-long silent run” failure mode by:
- **Preflight**: fails fast if `chat.db` isn’t readable (Full Disk Access).
- **Timeouts**: every command has a bounded timeout.
- **Streaming checkpoints**: `--output` is updated as the run progresses.
- **Resume**: `--resume` skips completed commands from a prior `--output` file.

## Read-only vs R/W

- **Default**: read-only benchmarks only.
- **R/W (send)**: opt-in with `--include-rw` and `IMESSAGE_BENCH_SEND_TO` (kept out of output artifacts).

## Recommended first run (minimal, 5 iterations)

Tier A (most relevant), read-only:

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier a \
  --iterations 5 \
  --output Texting/benchmarks/results/competitor_tier_a.json
```

If something fails, fix it and resume:

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier a \
  --iterations 5 \
  --output Texting/benchmarks/results/competitor_tier_a.json \
  --resume
```

## Chunking runs

Run just one tool (or a subset) to keep runs short:

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier all \
  --iterations 5 \
  --tool-filter "Wolfies" \
  --output Texting/benchmarks/results/chunk_wolfies.json
```

Or cap the number of tools:

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier all \
  --iterations 5 \
  --max-tools 3 \
  --output Texting/benchmarks/results/chunk_first3.json
```

## Optional: include npx-based competitors

These can be slow on first run because `npx` may download packages. Disabled by default.

Recommended (maximalist) workflow:
1) preinstall npm packages globally (so benchmarks can run in no-download mode)
2) run the suite with `--allow-npx` (defaults to `npx --no-install`)

Preinstall:

```bash
python3 Texting/benchmarks/install_competitors.py --npm
```

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier extended \
  --iterations 5 \
  --allow-npx \
  --output Texting/benchmarks/results/extended_npx.json
```

If you explicitly want to allow downloads during benchmarks (not recommended for “end-to-end”):

```bash
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier extended \
  --iterations 1 \
  --allow-npx \
  --npx-download \
  --output Texting/benchmarks/results/extended_npx_download.json
```

## Findings

Summary and honest caveats are documented in:
- `Texting/benchmarks/FINDINGS.md`

## Optional: R/W send benchmarks (opt-in)

**Warning:** this will send messages.

```bash
export IMESSAGE_BENCH_SEND_TO="<test-number>"
python3 Texting/benchmarks/competitor_benchmarks.py \
  --tier a \
  --iterations 5 \
  --include-rw \
  --output Texting/benchmarks/results/with_send.json
```
