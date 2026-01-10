#!/usr/bin/env python3
"""
Story-Focused Benchmark Visualizations (Slides 01-08)

THE STORY: Wolfies iMessage Gateway is the fastest, most consistent
iMessage interface for LLMs. MCP protocol adds ~1s overhead per session.

Slides:
01_llm_loop_score.png       - Total wall time for N=5 loop (Setup + 5x Work)
02_first_vs_warm.png        - First Call (Setup+Work) vs Warm Call (Work)
03_amortization.png         - Avg ms/call vs N calls (1..30)
04_workload_leaderboards.png - Top 5 leaderboard for each workload (2x2)
05_coverage_heatmap.png     - Capability matrix (OK/TIMEOUT/UNSUPPORTED)
06_mcp_setup_tax.png        - Session initialization time comparison
07_latency_vs_tokens.png    - Scatter plot (Speed vs Payload size)
08_read_vs_write.png        - Wolfies Read vs Write cost
"""

from pathlib import Path
import json
import csv
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "visualizations" / "story_focused"


def _latest_path(pattern: str, fallback: str) -> Path:
    matches = sorted(REPO_ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if matches:
        return matches[0]
    return REPO_ROOT / fallback

# =============================================================================
# DATA PATHS
# =============================================================================

MCP_JSON = _latest_path(
    "Texting/benchmarks/results/normalized_workloads_*_validated.json",
    "Texting/benchmarks/results/normalized_workloads_20260107_202056_node22_validated.json",
)
MCP_CSV = _latest_path(
    "Texting/benchmarks/results/normalized_headline_combined_*_validated*.csv",
    "Texting/benchmarks/results/normalized_headline_combined_20260107_202056_node22_validated_validated.csv",
)
WOLFIES_DAEMON = REPO_ROOT / "Texting/gateway/benchmarks_quick_with_daemon_v3.json"
WOLFIES_SEND = REPO_ROOT / "Texting/benchmarks/results/competitor_tier_a_with_send_run2.json"

# =============================================================================
# THEME & LAYOUT
# =============================================================================

THEME = {
    "font_mono": "JetBrains Mono, SF Mono, Menlo, monospace",
    "font_sans": "Inter, SF Pro Display, system-ui, sans-serif",
    "bg_dark": "#0a0a0f",
    "bg_card": "#12121a",
    "grid": "#18182a",
    "text_bright": "#f5f5fa",
    "text_muted": "#9999bb",
    "text_dim": "#555577",
    "wolfie": "#10b981",  # Emerald
    "wolfie_glow": "rgba(16, 185, 129, 0.25)",
    "competitor": "#f97316",  # Orange
    "competitor_slow": "#ea580c",
    "competitor_alt": "#64748b",  # Slate
    "accent_blue": "#3b82f6",
}

BASE_FOOTNOTE = "Node 22 • n=5 iterations • call_timeout=30s • phase_timeout=40s"


def base_layout(fig, title, subtitle):
    """Apply consistent dark theme."""
    fig.update_layout(
        template="plotly_dark",
        font=dict(family=THEME["font_sans"], color=THEME["text_bright"], size=14),
        title=dict(
            text=(
                f"<span style='font-size: 28px; font-weight: 700;'>{title}</span>"
                f"<br><span style='font-size: 15px; color: {THEME['text_muted']}; font-weight: 400;'>{subtitle}</span>"
            ),
            x=0.02,
            y=0.95,
            xanchor="left",
            yanchor="top",
        ),
        paper_bgcolor=THEME["bg_dark"],
        plot_bgcolor=THEME["bg_dark"],
        margin=dict(t=110, b=70, l=100, r=60),
        xaxis=dict(
            gridcolor=THEME["grid"],
            gridwidth=1,
            zerolinecolor=THEME["grid"],
            tickfont=dict(color=THEME["text_muted"], size=13),
            title_font=dict(color=THEME["text_muted"], size=13),
        ),
        yaxis=dict(
            gridcolor=THEME["grid"],
            gridwidth=1,
            zerolinecolor=THEME["grid"],
            tickfont=dict(color=THEME["text_bright"], size=13),
            title_font=dict(color=THEME["text_muted"], size=13),
        ),
    )
    return fig


def add_footnote(fig, extra_text=None):
    """Add standardized footnote."""
    note = BASE_FOOTNOTE
    if extra_text:
        note += f" • {extra_text}"

    fig.add_annotation(
        text=f"<span style='font-size: 10px; color: {THEME['text_dim']}'>{note}</span>",
        x=0.5,
        y=-0.12,
        xref="paper",
        yref="paper",
        showarrow=False,
        xanchor="center",
    )
    return fig


# =============================================================================
# DATA LOADING UTILS
# =============================================================================


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_csv(path):
    with open(path) as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_mean_workload_ms(server_workloads, workload_id):
    """Get mean ms for a specific workload ID if OK."""
    for w in server_workloads:
        if w["workload_id"] == workload_id:
            # Check if any results ok
            ok_res = [r["ms"] for r in w.get("results", []) if r.get("ok")]
            if ok_res:
                return sum(ok_res) / len(ok_res)
    return None


def get_wolfie_bench(results_list, name):
    """Get benchmark result by name from Wolfies list."""
    for r in results_list:
        if r["name"] == name:
            return r
    return None


# =============================================================================
# SLIDE 01: LLM LOOP SCOREBOARD
# =============================================================================


def create_llm_loop_score():
    """Ranked horizontal bar chart of Total Wall Time for N=5 loop."""
    N_LOOPS = 5
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_daemon_res = wolf_daemon["results"]

    data_points = []

    # 1. MCP Servers (only if they support W1+W2+W3)
    for s in mcp_data["servers"]:
        w1 = get_mean_workload_ms(s["workloads"], "W1_RECENT")
        w2 = get_mean_workload_ms(s["workloads"], "W2_SEARCH")
        w3 = get_mean_workload_ms(s["workloads"], "W3_THREAD")

        if w1 and w2 and w3:
            setup = s["session_initialize"]["ms"]
            work_per_loop = w1 + w2 + w3
            total = setup + (N_LOOPS * work_per_loop)
            data_points.append(
                {
                    "name": s["name"]
                    .split(":")[1]
                    .strip()
                    .split("(")[0]
                    .strip(),  # Cleanup name
                    "setup": setup,
                    "work": N_LOOPS * work_per_loop,
                    "total": total,
                    "type": "mcp",
                }
            )

    # 2. Wolfies Daemon
    d_setup = get_wolfie_bench(wolf_daemon_res, "daemon_startup_ready")["mean_ms"]
    d_recent = get_wolfie_bench(wolf_daemon_res, "daemon_recent_10")["mean_ms"]
    d_search = get_wolfie_bench(wolf_daemon_res, "daemon_text_search_http_20")[
        "mean_ms"
    ]
    d_bundle = get_wolfie_bench(wolf_daemon_res, "daemon_bundle")[
        "mean_ms"
    ]  # Proxy for thread

    d_work_loop = d_recent + d_search + d_bundle
    data_points.append(
        {
            "name": "Wolfies Daemon",
            "setup": d_setup,
            "work": N_LOOPS * d_work_loop,
            "total": d_setup + (N_LOOPS * d_work_loop),
            "type": "wolfie",
        }
    )

    # 3. Wolfies CLI
    c_recent = get_wolfie_bench(wolf_daemon_res, "recent_conversations_10")["mean_ms"]
    c_search = get_wolfie_bench(wolf_daemon_res, "search_small")["mean_ms"]
    c_bundle = get_wolfie_bench(wolf_daemon_res, "bundle_compact")["mean_ms"]

    c_work_loop = c_recent + c_search + c_bundle
    data_points.append(
        {
            "name": "Wolfies CLI",
            "setup": 0,
            "work": N_LOOPS * c_work_loop,
            "total": 0 + (N_LOOPS * c_work_loop),
            "type": "wolfie",
        }
    )

    # Sort ASC (lower is better)
    data_points.sort(key=lambda x: x["total"])

    # Plot
    fig = go.Figure()

    names = [d["name"] for d in data_points]
    setups = [d["setup"] for d in data_points]
    works = [d["work"] for d in data_points]

    # Colors
    colors = [
        THEME["wolfie"] if d["type"] == "wolfie" else THEME["competitor"]
        for d in data_points
    ]

    # Setup bars (hatched)
    fig.add_trace(
        go.Bar(
            y=names,
            x=setups,
            orientation="h",
            name="Setup (1x)",
            marker=dict(
                color=[c if s > 0 else "rgba(0,0,0,0)" for c, s in zip(colors, setups)],
                pattern=dict(shape="/", fgcolor=THEME["bg_card"], bgcolor=colors),
                line=dict(width=0),
            ),
            hovertemplate="Setup: %{x:.0f}ms<extra></extra>",
        )
    )

    # Work bars (solid)
    fig.add_trace(
        go.Bar(
            y=names,
            x=works,
            orientation="h",
            name=f"Work ({N_LOOPS}x loops)",
            marker=dict(color=colors),
            text=[f"<b>{d['total'] / 1000:.1f}s</b>" for d in data_points],
            textposition="outside",
            textfont=dict(color=THEME["text_bright"], family=THEME["font_mono"]),
            hovertemplate="Work: %{x:.0f}ms<extra></extra>",
        )
    )

    fig.update_layout(barmode="stack")
    fig = base_layout(
        fig,
        f"LLM Loop Scoreboard (N={N_LOOPS})",
        "Loop: Recent + Search + Thread/Payload",
    )
    fig = add_footnote(fig, "Sorted by total wall time (lower is better)")

    # Invert Y to show rank 1 at top
    fig.update_yaxes(autorange="reversed")

    return fig


# =============================================================================
# SLIDE 02: FIRST CALL VS WARM CALL
# =============================================================================


def create_first_vs_warm():
    """First Call (setup+1) vs Warm Call (1)."""
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    # Wolfies
    cli_warm = get_wolfie_bench(wolf_res, "bundle_compact")["mean_ms"]
    daemon_setup = get_wolfie_bench(wolf_res, "daemon_startup_ready")["mean_ms"]
    daemon_warm = get_wolfie_bench(wolf_res, "daemon_bundle")["mean_ms"]

    data = [
        {"name": "Wolfies CLI", "setup": 0, "warm": cli_warm, "type": "wolfie"},
        {
            "name": "Wolfies Daemon",
            "setup": daemon_setup,
            "warm": daemon_warm,
            "type": "wolfie",
        },
    ]

    # MCP (Pick 2)
    targets = ["cardmagic/messages", "imessage-mcp (deno"]
    for s in mcp_data["servers"]:
        if any(t in s["name"] for t in targets):
            w3 = get_mean_workload_ms(s["workloads"], "W3_THREAD")
            if w3:
                data.append(
                    {
                        "name": s["name"].split(":")[1].strip().split("(")[0],
                        "setup": s["session_initialize"]["ms"],
                        "warm": w3,
                        "type": "mcp",
                    }
                )

    # Sort by total first call
    data.sort(key=lambda x: x["setup"] + x["warm"])

    fig = go.Figure()
    names = [d["name"] for d in data]

    # Setup bars
    fig.add_trace(
        go.Bar(
            y=names,
            x=[d["setup"] for d in data],
            orientation="h",
            name="Setup",
            marker=dict(
                color=[
                    THEME["wolfie"] if d["type"] == "wolfie" else THEME["competitor"]
                    for d in data
                ],
                pattern=dict(shape="/", fgcolor="rgba(0,0,0,0.5)"),
            ),
            text=[f"{d['setup']:.0f}ms" if d["setup"] > 0 else "" for d in data],
            textposition="auto",
        )
    )

    # Warm bars
    fig.add_trace(
        go.Bar(
            y=names,
            x=[d["warm"] for d in data],
            orientation="h",
            name="Work (1 call)",
            marker=dict(
                color=[
                    THEME["wolfie"] if d["type"] == "wolfie" else THEME["competitor"]
                    for d in data
                ]
            ),
            text=[f"{d['warm']:.0f}ms" for d in data],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig.add_annotation(
        x=1000,
        y=2.5,
        text="MCP ≈ 1s handshake tax",
        showarrow=True,
        arrowhead=2,
        ax=-20,
        ay=-40,
        font=dict(color=THEME["competitor"]),
    )

    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
    fig = base_layout(
        fig, "First Call vs Warm Call", "Cost of cold start + first operation"
    )
    fig = add_footnote(fig, "Warm call based on W3_THREAD / Bundle")
    return fig


# =============================================================================
# SLIDE 03: AMORTIZATION CURVE
# =============================================================================


def create_amortization_curve():
    """Line chart: Avg ms/call vs N (1..30)."""
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    N_range = list(range(1, 31))

    fig = go.Figure()

    # Helper to plot line
    def add_curve(name, setup, call, color, dash="solid"):
        y_vals = [(setup + (n * call)) / n for n in N_range]
        fig.add_trace(
            go.Scatter(
                x=N_range,
                y=y_vals,
                name=name,
                line=dict(color=color, width=3, dash=dash),
                mode="lines",
            )
        )
        return y_vals

    # Wolfies CLI (Flat)
    cli_call = get_wolfie_bench(wolf_res, "bundle_compact")["mean_ms"]
    add_curve("Wolfies CLI", 0, cli_call, THEME["wolfie"], "dash")

    # Wolfies Daemon
    d_setup = get_wolfie_bench(wolf_res, "daemon_startup_ready")["mean_ms"]
    d_call = get_wolfie_bench(wolf_res, "daemon_bundle")["mean_ms"]
    add_curve("Wolfies Daemon", d_setup, d_call, THEME["wolfie"])

    # MCP (Pick 2)
    targets = ["cardmagic/messages", "imessage-mcp (deno"]
    colors = [THEME["competitor"], THEME["competitor_alt"]]

    for i, s in enumerate(mcp_data["servers"]):
        if any(t in s["name"] for t in targets):
            name = s["name"].split(":")[1].strip().split("(")[0]
            w3 = get_mean_workload_ms(s["workloads"], "W3_THREAD")
            if w3:
                # Use a different color for each MCP
                c = colors.pop(0) if colors else THEME["competitor_slow"]
                add_curve(f"MCP: {name}", s["session_initialize"]["ms"], w3, c)

    fig.update_layout(
        xaxis_title="Number of Calls (N)",
        yaxis_title="Average Latency per Call (ms)",
        yaxis_type="log",
        legend=dict(x=0.7, y=0.95),
    )

    fig = base_layout(
        fig, "Amortization Curve (N=1..30)", "When does the setup cost pay off?"
    )
    fig = add_footnote(fig, "Log scale Y-axis • Formula: (setup + N*call) / N")
    return fig


# =============================================================================
# SLIDE 04: WORKLOAD LEADERBOARDS
# =============================================================================


def create_leaderboards():
    """2x2 Grid of top 5 performers per workload."""
    csv_data = load_csv(MCP_CSV)

    workloads = ["W0_UNREAD", "W1_RECENT", "W2_SEARCH", "W3_THREAD"]

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[f"<b>{w}</b>" for w in workloads],
        horizontal_spacing=0.15,
        vertical_spacing=0.2,
    )

    for idx, w_id in enumerate(workloads):
        row = (idx // 2) + 1
        col = (idx % 2) + 1

        # Filter rankings for this workload
        rankings = [
            r
            for r in csv_data
            if r["table"] == "workload_rankings" and r["workload"] == w_id
        ]

        # Sort by rank numerically, take top 5
        rankings.sort(key=lambda x: int(x["rank"]))
        top_5 = rankings[:5]

        # Reverse for horiz bar (top rank at top)
        top_5.reverse()

        if not top_5:
            continue

        names = [r["server"].split(":")[1].strip().split("(")[0][:20] for r in top_5]
        means = [float(r["mean_ms"]) for r in top_5]
        tools = [r["tool"] for r in top_5]

        fig.add_trace(
            go.Bar(
                y=names,
                x=means,
                orientation="h",
                marker_color=THEME["accent_blue"],
                text=[
                    f"{m:.0f}ms<br><span style='font-size:10px'>{t}</span>"
                    for m, t in zip(means, tools)
                ],
                textposition="auto",
            ),
            row=row,
            col=col,
        )

        # Annotate Unsupported
        fig.add_annotation(
            text="*Unsupported tools hidden",
            xref=f"x{idx + 1}",
            yref=f"y{idx + 1}",
            x=0,
            y=-0.2,
            showarrow=False,
            font=dict(size=10, color=THEME["text_dim"]),
        )

    fig = base_layout(
        fig, "Per-Workload Leaderboards", "Top 5 Performing MCP Tools (Mean Latency)"
    )
    fig = add_footnote(fig)
    return fig


# =============================================================================
# SLIDE 05: COVERAGE HEATMAP
# =============================================================================


def create_heatmap():
    """Matrix of Server vs Workload status."""
    mcp_data = load_json(MCP_JSON)

    servers = [
        s["name"].split(":")[1].strip().split("(")[0] for s in mcp_data["servers"]
    ]
    workloads = ["W0_UNREAD", "W1_RECENT", "W2_SEARCH", "W3_THREAD"]

    z = []
    text = []

    # Define mapping: 3=OK, 2=PARTIAL, 1=TIMEOUT, 0=UNSUPPORTED
    status_map = {"ok": 3, "fail": 1, "unsupported": 0}

    for s in mcp_data["servers"]:
        row_z = []
        row_text = []
        for w_id in workloads:
            # Find workload result
            w_res = next((w for w in s["workloads"] if w["workload_id"] == w_id), None)

            if not w_res:
                row_z.append(0)
                row_text.append("N/A")
                continue

            status = w_res.get("status")
            if status:
                summary = w_res.get("summary") or {}
                mean_ms = summary.get("mean_ms")
                validation_counts = (w_res.get("validation_summary") or {}).get("counts") or {}
                valid_ok = validation_counts.get("ok_valid", 0)
                total = len(w_res.get("results") or [])

                if status == "unsupported":
                    row_z.append(0)
                    row_text.append("UNSUP")
                elif status == "ok_valid":
                    row_z.append(3)
                    row_text.append(
                        f"OK ({int(mean_ms) if mean_ms is not None else 'n/a'}ms)"
                    )
                elif status == "partial_valid":
                    row_z.append(2)
                    row_text.append(f"PARTIAL {valid_ok}/{total}")
                elif status == "ok_empty":
                    row_z.append(1)
                    row_text.append("EMPTY")
                elif status == "fail_timeout":
                    row_z.append(1)
                    row_text.append("TIMEOUT")
                else:
                    row_z.append(1)
                    row_text.append("FAIL")
            else:
                # Fallback for legacy results
                if "unsupported" in w_res.get("notes", []) or w_res["tool_name"] is None:
                    row_z.append(0)
                    row_text.append("UNSUP")
                else:
                    ok_count = len([r for r in w_res["results"] if r.get("ok")])
                    total = len(w_res["results"])

                    if ok_count == total and total > 0:
                        row_z.append(3)
                        row_text.append(
                            f"OK ({int(get_mean_workload_ms(s['workloads'], w_id))}ms)"
                        )
                    elif ok_count > 0:
                        row_z.append(2)
                        row_text.append(f"PARTIAL {ok_count}/{total}")
                    else:
                        # Check for timeout error specifically
                        errs = set(r.get("error") for r in w_res["results"])
                        if "TIMEOUT" in errs:
                            row_z.append(1)
                            row_text.append("TIMEOUT")
                        else:
                            row_z.append(1)
                            row_text.append("FAIL")

        z.append(row_z)
        text.append(row_text)

    # Colorscale: 0=Dark(Unsup), 1=Red(Fail), 2=Yellow(Partial), 3=Green(OK)
    colorscale = [
        [0.0, THEME["bg_card"]],
        [0.25, THEME["bg_card"]],
        [0.25, THEME["competitor_slow"]],
        [0.5, THEME["competitor_slow"]],
        [0.5, THEME["competitor"]],
        [0.75, THEME["competitor"]],
        [0.75, THEME["wolfie"]],
        [1.0, THEME["wolfie"]],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=workloads,
            y=servers,
            text=text,
            texttemplate="%{text}",
            colorscale=colorscale,
            showscale=False,
            xgap=2,
            ygap=2,
        )
    )

    # Reverse Y to match reading order
    fig.update_yaxes(autorange="reversed")

    fig = base_layout(
        fig, "Coverage & Reliability Heatmap", "Capability Matrix across the ecosystem"
    )
    fig = add_footnote(fig, "TIMEOUT > 30s per call")
    return fig


# =============================================================================
# SLIDE 06: MCP SETUP TAX
# =============================================================================


def create_mcp_tax():
    """Bar chart of session_initialize.ms."""
    mcp_data = load_json(MCP_JSON)

    data = []
    for s in mcp_data["servers"]:
        data.append(
            {
                "name": s["name"].split(":")[1].strip().split("(")[0],
                "init_ms": s["session_initialize"]["ms"],
            }
        )

    data.sort(key=lambda x: x["init_ms"], reverse=True)  # Desc for horizontal

    names = [d["name"] for d in data]
    vals = [d["init_ms"] for d in data]

    fig = go.Figure(
        go.Bar(
            y=names,
            x=vals,
            orientation="h",
            marker_color=THEME["annotated_tax_region"]
            if "annotated" in THEME
            else THEME["competitor"],
            text=[f"{v:.0f}ms" for v in vals],
            textposition="outside",
        )
    )

    # Shade the tax region (950-1100ms)
    fig.add_shape(
        type="rect",
        x0=950,
        x1=1100,
        y0=-1,
        y1=len(names),
        fillcolor="rgba(255,100,0, 0.1)",
        line_width=0,
        layer="below",
    )

    fig.add_annotation(
        x=1025,
        y=len(names) / 2,
        text="~1s MCP Handshake",
        font=dict(color=THEME["competitor"], size=20),
        showarrow=False,
    )

    fig = base_layout(
        fig, "MCP Setup Tax", "Session initialization overhead per server"
    )
    fig = add_footnote(
        fig,
        "This cost is paid once per session (not per call), but affects CLI/short-lived usage.",
    )
    return fig


# =============================================================================
# SLIDE 07: LATENCY VS TOKENS
# =============================================================================


def create_latency_tokens():
    """Scatter: Latency vs Tokens (or Bytes)."""
    mcp_data = load_json(MCP_JSON)
    wolf_send = load_json(WOLFIES_SEND)

    fig = go.Figure()

    # 1. Wolfies (Emerald)
    # Using 'competitor_tier_a' names, filter for "minimal" reads
    wolf_res = next(t for t in wolf_send["tool_results"] if "Wolfies" in t["name"])

    w_x, w_y, w_sz, w_txt = [], [], [], []
    for cmd in wolf_res["commands"]:
        if "minimal" in cmd["label"] and cmd["read_only"]:
            w_x.append(cmd["mean_ms"])
            w_y.append(cmd["approx_tokens_mean"])
            w_sz.append(math.log(cmd["stdout_bytes_mean"] + 1) * 5)  # Scale bubble
            w_txt.append(cmd["label"])

    fig.add_trace(
        go.Scatter(
            x=w_x,
            y=w_y,
            mode="markers+text",
            marker=dict(size=w_sz, color=THEME["wolfie"], opacity=0.8),
            text=w_txt,
            textposition="top center",
            name="Wolfies CLI",
        )
    )

    # 2. MCP (Orange)
    m_x, m_y, m_sz, m_txt = [], [], [], []
    for s in mcp_data["servers"]:
        name = s["name"].split(":")[1].split("(")[0].strip()
        for w in s["workloads"]:
            if w["results"] and not "unsupported" in w.get("notes", []):
                # Only if OK
                ok_res = [r for r in w["results"] if r.get("ok")]
                if ok_res:
                    mean_ms = sum(r["ms"] for r in ok_res) / len(ok_res)
                    tok_vals = [
                        r.get("payload_tokens_est") if r.get("payload_tokens_est") is not None else r.get("approx_tokens")
                        for r in ok_res
                    ]
                    tok_vals = [v for v in tok_vals if v is not None]
                    mean_tok = sum(tok_vals) / len(tok_vals) if tok_vals else None
                    byte_vals = [
                        r.get("payload_bytes") if r.get("payload_bytes") is not None else r.get("stdout_bytes")
                        for r in ok_res
                    ]
                    byte_vals = [v for v in byte_vals if v is not None]
                    mean_bytes = sum(byte_vals) / len(byte_vals) if byte_vals else None

                    if mean_ms < 2000 and mean_tok is not None:  # Filter outliers for readability
                        m_x.append(mean_ms)
                        m_y.append(mean_tok)
                        if mean_bytes is not None:
                            m_sz.append(math.log(mean_bytes + 1) * 5)
                        else:
                            m_sz.append(4)
                        m_txt.append(f"{name}<br>{w['workload_id']}")

    fig.add_trace(
        go.Scatter(
            x=m_x,
            y=m_y,
            mode="markers",
            marker=dict(size=m_sz, color=THEME["competitor"], opacity=0.6),
            name="MCP Tools",
            hovertext=m_txt,
        )
    )

    # Annotate Quandrant
    fig.add_annotation(
        x=50,
        y=100,
        text="<b>Golden Zone</b><br>Fast + Small Payload",
        showarrow=False,
        font=dict(color=THEME["wolfie"]),
        bgcolor=THEME["bg_card"],
        borderpad=5,
    )

    fig.update_layout(
        xaxis_title="Latency (ms)",
        yaxis_title="Response Size (Approx Tokens)",
        yaxis_type="log",
    )

    fig = base_layout(
        fig,
        "Latency vs Token Cost",
        "Efficiency frontier: optimal tools are bottom-left",
    )
    fig = add_footnote(fig, "Bubble size = Raw bytes output")
    return fig


# =============================================================================
# SLIDE 08: READ VS WRITE
# =============================================================================


def create_read_vs_write():
    """Bar chart: Wolfies Read ops vs Write op."""
    wolf_send = load_json(WOLFIES_SEND)
    wolf_res = next(t for t in wolf_send["tool_results"] if "Wolfies" in t["name"])

    # Select commands
    targets_read = ["recent_10_minimal", "unread_minimal", "bundle_minimal"]
    target_write = "send_message"

    data = []

    for cmd in wolf_res["commands"]:
        if cmd["label"] in targets_read:
            data.append({"name": cmd["label"], "ms": cmd["mean_ms"], "type": "read"})
        elif cmd["label"] == target_write:
            data.append({"name": "SEND Message", "ms": cmd["mean_ms"], "type": "write"})

    # Sort
    data.sort(key=lambda x: x["ms"])

    colors = [
        THEME["wolfie"] if d["type"] == "read" else THEME["competitor"] for d in data
    ]

    fig = go.Figure(
        go.Bar(
            x=[d["name"] for d in data],
            y=[d["ms"] for d in data],
            marker_color=colors,
            text=[f"{d['ms']:.0f}ms" for d in data],
            textposition="outside",
        )
    )

    fig.add_annotation(
        x="SEND Message",
        y=160,
        text="Requires Permissions + Automation",
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(color=THEME["competitor"]),
    )

    fig = base_layout(
        fig,
        "Read vs Write Latency",
        "Sending messages is slower due to AppleScript/Automation",
    )
    fig = add_footnote(fig, "Send is opt-in; depends on Messages.app automation")
    return fig


# =============================================================================
# MAIN
# =============================================================================


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # (Func, Filename)
    charts = [
        (create_llm_loop_score, "01_llm_loop_score.png"),
        (create_first_vs_warm, "02_first_vs_warm.png"),
        (create_amortization_curve, "03_amortization.png"),
        (create_leaderboards, "04_workload_leaderboards.png"),
        (create_heatmap, "05_coverage_heatmap.png"),
        (create_mcp_tax, "06_mcp_setup_tax.png"),
        (create_latency_tokens, "07_latency_vs_tokens.png"),
        (create_read_vs_write, "08_read_vs_write.png"),
    ]

    print(f"📊 Generating 8 Story Visualizations in {OUTPUT_DIR}/")
    print("=" * 60)

    for func, fname in charts:
        print(f"  → Rendering {fname}...")
        try:
            fig = func()
            fig.write_image(OUTPUT_DIR / fname, width=1600, height=900, scale=2)
            print(f"    ✓ Saved")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback

            traceback.print_exc()

    print("=" * 60)
    print("✅ Done.")


if __name__ == "__main__":
    main()
