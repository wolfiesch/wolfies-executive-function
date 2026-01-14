# FGP Browser Gateway - Comprehensive Benchmark Results

**Generated:** 01/13/2026 11:21 PM PST (via pst-timestamp)
**Environment:** macOS, Chrome 131 headless, FGP daemon v0.1.0

---

## Single-Operation Comparison (FGP vs Playwright MCP)

Direct head-to-head benchmark, 5 iterations each:

| Operation | FGP Browser | Playwright MCP | Speedup |
|-----------|-------------|----------------|---------|
| Navigate  | **8ms**     | 2,328ms        | **291x** |
| Extract (ARIA) | **11ms** | 2,484ms     | **226x** |
| Screenshot | **29ms**   | 1,635ms        | **56x** |

**Why the massive difference?**
- Playwright MCP spawns a new Node.js process + browser for each call (~2.3s overhead)
- FGP Browser uses a warm daemon with persistent browser connection

---

## Multi-Step Workflow Comparison

Real-world agent workflows (5 iterations, mean latency):

| Workflow | Steps | FGP Total | MCP Estimate | Speedup |
|----------|-------|-----------|--------------|---------|
| Login Flow | 5 | **659ms** | 11,500ms | **17.5x** |
| Search+Extract | 6 | **771ms** | 13,800ms | **17.9x** |
| Form Submit | 7 | **304ms** | 16,100ms | **52.9x** |
| Pagination Loop | 10 | **1,087ms** | 23,000ms | **21.2x** |

**Key insight:** More steps = bigger compound advantage

---

## Per-Operation Latency Breakdown

After initial page load, all operations are nearly instant:

| Operation | FGP Latency | Notes |
|-----------|-------------|-------|
| navigate | 96-240ms | Network-bound (first visit) |
| navigate (cached) | 7-9ms | Page already loaded |
| fill (input) | 16-22ms | DOM interaction |
| click | 11-16ms | DOM interaction |
| snapshot (ARIA) | 3-5ms | Single-pass extraction |
| check (checkbox) | <1ms | JavaScript evaluation |
| screenshot | 24-34ms | PNG encoding |
| select (dropdown) | ~5ms | JavaScript evaluation |
| scroll | ~3ms | JavaScript evaluation |
| press_combo | ~5ms | CDP keyboard events |

---

## Architecture Comparison

| Aspect | Playwright MCP | FGP Browser |
|--------|----------------|-------------|
| Startup | Cold spawn each call (~2.3s) | Warm daemon (always ready) |
| Browser | Launches new browser | Single persistent browser |
| Sessions | Single page | Multiple isolated contexts |
| Concurrency | Blocked ("browser in use") | Parallel sessions supported |
| Token overhead | ~150 tokens/call | ~30 tokens/call |
| State persistence | Lost between calls | Cookies, localStorage preserved |

---

## Supported Operations

| Feature | Method | Status |
|---------|--------|--------|
| Navigate | `browser.open` | ✅ |
| ARIA Snapshot | `browser.snapshot` | ✅ |
| Screenshot | `browser.screenshot` | ✅ |
| Click | `browser.click` | ✅ |
| Fill Input | `browser.fill` | ✅ |
| Press Key | `browser.press` | ✅ |
| Select Dropdown | `browser.select` | ✅ |
| Checkbox/Radio | `browser.check` | ✅ |
| Hover | `browser.hover` | ✅ |
| Scroll | `browser.scroll` | ✅ |
| Key Combos | `browser.press_combo` | ✅ |
| File Upload | `browser.upload` | ✅ |
| Session Management | `session.*` | ✅ |

---

## Benchmark Files

- Single-op results: `benchmarks/results/browser_20260113_232032.json`
- Workflow results: `benchmarks/results/browser_workflow_20260113_212715.json`
- Benchmark scripts:
  - `benchmarks/browser_benchmark.py` (single-op comparison)
  - `benchmarks/browser_workflow_benchmark.py` (workflow comparison)

---

## Reproduce Benchmarks

```bash
# Start FGP browser daemon
~/projects/fgp/browser/target/release/browser-gateway start

# Run single-operation benchmark (FGP vs Playwright MCP)
python3 benchmarks/browser_benchmark.py --iterations 5

# Run workflow benchmarks
python3 benchmarks/browser_workflow_benchmark.py --iterations 5
```
