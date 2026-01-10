#!/usr/bin/env python3
"""
Story-Focused Benchmark Visualizations v3 (Slides 01-10)

Updates in v3:
- adaptive ms formatting
- strict axis/unit handling
- new ECDF and Pareto charts
- refined specific slides (amortization, tax, etc.)
"""

from pathlib import Path
import json
import csv
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "visualizations" / "story_focused"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=THEME["text_muted"])),
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


def format_ms(ms):
    """Adaptive formatting: >=100 (0d), 10-99 (1d), 1-9.99 (2d), <1 (3d)."""
    if ms is None:
        return "N/A"
    if ms >= 100:
        return f"{ms:.0f}ms"
    elif ms >= 10:
        return f"{ms:.1f}ms"
    elif ms >= 1:
        return f"{ms:.2f}ms"
    elif ms > 0:
        return f"{ms:.3f}ms"
    else:
        return "0ms"


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
    for w in server_workloads:
        if w["workload_id"] == workload_id:
            ok_res = [r["ms"] for r in w.get("results", []) if r.get("ok")]
            if ok_res:
                return sum(ok_res) / len(ok_res)
    return None


def get_wolfie_bench(results_list, name):
    for r in results_list:
        if r["name"] == name:
            return r
    return None


# =============================================================================
# GITHUB INFO MAPPING: user/repo format with star counts
# =============================================================================

GITHUB_INFO = {
    # Key: substring to match in raw server name → Value: (Clean Display Name, Stars)
    "cardmagic/messages": ("cardmagic/messages", 212),
    "wyattjoh/imessage-mcp": ("wyattjoh/imessage-mcp", 18),
    "mattt/iMCP": ("mattt/iMCP", 986),
    "jonmmease/jons-mcp-imessage": ("jonmmease/jons-mcp-imessage", 2),
    "TextFly/photon-imsg-mcp": ("TextFly/photon-imsg-mcp", 700),
    "sameelarif/imessage-mcp": ("sameelarif/imessage-mcp", 22),
    "imessage-query-fastmcp": ("imessage-query-fastmcp", 5),
    "mcp-imessage": ("tchbw/mcp-imessage", 6),
    "imessage-mcp-improved": ("imessage-mcp-improved", 3),
}


def clean_name(name):
    """Convert raw server name to user/repo ★stars format."""
    # First try to match against GITHUB_INFO
    for key, (display, stars) in GITHUB_INFO.items():
        if key in name:
            return f"{display} ★{stars}"

    # Fallback: parse from raw name
    base = name.split(":")[1].strip().split("(")[0].strip() if ":" in name else name
    return base


# =============================================================================
# 01: LLM LOOP SCOREBOARD
# =============================================================================


def create_llm_loop_score():
    N_LOOPS = 5
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    data_points = []

    # 1. MCP
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
                    "name": clean_name(s["name"]),
                    "setup": setup,
                    "work": N_LOOPS * work_per_loop,
                    "total": total,
                    "type": "mcp",
                }
            )

    # 2. Wolfies
    d_setup = get_wolfie_bench(wolf_res, "daemon_startup_ready")["mean_ms"]
    d_recent = get_wolfie_bench(wolf_res, "daemon_recent_10")["mean_ms"]
    d_search = get_wolfie_bench(wolf_res, "daemon_text_search_http_20")["mean_ms"]
    d_bundle = get_wolfie_bench(wolf_res, "daemon_bundle")["mean_ms"]
    d_work = d_recent + d_search + d_bundle
    data_points.append(
        {
            "name": "Wolfies Daemon",
            "setup": d_setup,
            "work": N_LOOPS * d_work,
            "total": d_setup + (N_LOOPS * d_work),
            "type": "wolfie",
        }
    )

    c_recent = get_wolfie_bench(wolf_res, "recent_conversations_10")["mean_ms"]
    c_search = get_wolfie_bench(wolf_res, "search_small")["mean_ms"]
    c_bundle = get_wolfie_bench(wolf_res, "bundle_compact")["mean_ms"]
    c_work = c_recent + c_search + c_bundle
    data_points.append(
        {
            "name": "Wolfies CLI",
            "setup": 0,
            "work": N_LOOPS * c_work,
            "total": 0 + (N_LOOPS * c_work),
            "type": "wolfie",
        }
    )

    data_points.sort(key=lambda x: x["total"])
    # Simplify: Keep top 8 + Wolfies
    if len(data_points) > 10:
        data_points = [x for x in data_points if x["type"] == "wolfie"] + [
            x for x in data_points if x["type"] == "mcp"
        ][:8]
        data_points.sort(key=lambda x: x["total"])

    fig = go.Figure()
    names = [d["name"] for d in data_points]

    # Setup
    colors = [
        THEME["wolfie"] if d["type"] == "wolfie" else THEME["competitor"]
        for d in data_points
    ]
    fig.add_trace(
        go.Bar(
            y=names,
            x=[d["setup"] for d in data_points],
            orientation="h",
            name="Setup (1x)",
            marker=dict(
                color=[
                    c if d["setup"] > 0 else "rgba(0,0,0,0)"
                    for c, d in zip(colors, data_points)
                ],
                pattern=dict(shape="/", fgcolor=THEME["bg_card"], bgcolor=colors),
            ),
            text=[
                format_ms(d["setup"]) if d["setup"] > 10 else "" for d in data_points
            ],
            textposition="auto",
        )
    )

    # Work
    fig.add_trace(
        go.Bar(
            y=names,
            x=[d["work"] for d in data_points],
            orientation="h",
            name=f"Work ({N_LOOPS}x loops)",
            marker=dict(color=colors),
            text=[f"<b>{d['total'] / 1000:.2f}s</b>" for d in data_points],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
    fig = base_layout(
        fig,
        f"LLM Loop Scoreboard (N={N_LOOPS})",
        "Total Wall Time: Setup + 5x (Recent + Search + Thread)",
    )
    fig = add_footnote(fig, "Lower is better")
    return fig


# =============================================================================
# 02: FIRST CALL VS WARM CALL
# =============================================================================


def create_first_vs_warm():
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    # Wolfies
    cli_warm = get_wolfie_bench(wolf_res, "search_small")[
        "mean_ms"
    ]  # Use search for heavier load
    daemon_setup = get_wolfie_bench(wolf_res, "daemon_startup_ready")["mean_ms"]
    daemon_warm = get_wolfie_bench(wolf_res, "daemon_text_search_http_20")["mean_ms"]

    data = [
        {"name": "Wolfies CLI", "setup": 0, "warm": cli_warm, "type": "wolfie"},
        {
            "name": "Wolfies Daemon",
            "setup": daemon_setup,
            "warm": daemon_warm,
            "type": "wolfie",
        },
    ]

    # MCP (Pick 2 with Search support)
    targets = ["cardmagic/messages", "imessage-mcp (deno"]
    for s in mcp_data["servers"]:
        if any(t in s["name"] for t in targets):
            w2 = get_mean_workload_ms(s["workloads"], "W2_SEARCH")
            if w2:
                data.append(
                    {
                        "name": clean_name(s["name"]),
                        "setup": s["session_initialize"]["ms"],
                        "warm": w2,
                        "type": "mcp",
                    }
                )

    data.sort(key=lambda x: x["setup"] + x["warm"])

    fig = go.Figure()
    names = [d["name"] for d in data]

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
            text=[format_ms(d["setup"]) if d["setup"] > 0 else "" for d in data],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            y=names,
            x=[d["warm"] for d in data],
            orientation="h",
            name="Work (Search)",
            marker=dict(
                color=[
                    THEME["wolfie"] if d["type"] == "wolfie" else THEME["competitor"]
                    for d in data
                ]
            ),
            text=[format_ms(d["warm"]) for d in data],
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
        fig, "First Call vs Warm Call", "Cost of cold start + first W2_SEARCH operation"
    )
    fig = add_footnote(fig, "Using Search workload to show non-trivial execution time")
    return fig


# =============================================================================
# 03: AMORTIZATION CURVE
# =============================================================================


def create_amortization_curve():
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    N_range = list(range(1, 41))  # Extend bit further
    fig = go.Figure()

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

    # Wolfies
    cli_call = get_wolfie_bench(wolf_res, "search_small")["mean_ms"]
    add_curve("Wolfies CLI", 0, cli_call, THEME["wolfie"], "dash")

    d_setup = get_wolfie_bench(wolf_res, "daemon_startup_ready")["mean_ms"]
    d_call = get_wolfie_bench(wolf_res, "daemon_text_search_http_20")["mean_ms"]
    add_curve("Wolfies Daemon", d_setup, d_call, THEME["wolfie"])

    # MCP
    targets = ["cardmagic/messages", "imessage-mcp (deno"]
    colors = [THEME["competitor"], THEME["competitor_alt"]]
    for s in mcp_data["servers"]:
        if any(t in s["name"] for t in targets):
            w2 = get_mean_workload_ms(s["workloads"], "W2_SEARCH")
            if w2:
                c = colors.pop(0) if colors else THEME["competitor_slow"]
                add_curve(
                    f"MCP: {clean_name(s['name'])}",
                    s["session_initialize"]["ms"],
                    w2,
                    c,
                )

    fig.update_layout(
        xaxis_title="Number of Calls (N)",
        yaxis_title="Average Latency per Call (ms) - Log Scale",
        yaxis_type="log",
        yaxis=dict(
            tickvals=[10, 30, 100, 300, 1000, 3000],
            ticktext=["10ms", "30ms", "100ms", "300ms", "1s", "3s"],
        ),
        legend=dict(x=0.8, y=0.95),
    )

    fig = base_layout(
        fig,
        "Amortization Curve (W2_SEARCH)",
        "Setup cost impact diminishes over N calls",
    )
    fig = add_footnote(fig, "Formula: (setup + N*call) / N • Log scale Y-axis")
    return fig


# =============================================================================
# 04: LEADERBOARDS
# =============================================================================


def create_leaderboards():
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

        # Filter rankings
        rankings = [
            r
            for r in csv_data
            if r["table"] == "workload_rankings" and r["workload"] == w_id
        ]
        rankings.sort(key=lambda x: int(x["rank"]))
        top_5 = rankings[:5]
        top_5.reverse()

        if not top_5:
            continue

        names = [clean_name(r["server"])[:15] for r in top_5]
        means = [float(r["mean_ms"]) for r in top_5]

        fig.add_trace(
            go.Bar(
                y=names,
                x=means,
                orientation="h",
                marker_color=THEME["accent_blue"],
                text=[format_ms(m) for m in means],
                textposition="auto",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

    fig = base_layout(
        fig, "Per-Workload Leaderboards", "Top 5 Performing MCP Tools (Mean Latency)"
    )
    fig = add_footnote(fig)
    return fig


# =============================================================================
# 05: HEATMAP
# =============================================================================


def create_heatmap():
    mcp_data = load_json(MCP_JSON)
    servers = [clean_name(s["name"]) for s in mcp_data["servers"]]
    workloads = ["W0_UNREAD", "W1_RECENT", "W2_SEARCH", "W3_THREAD"]

    z, text_grid = [], []

    for s in mcp_data["servers"]:
        row_z, row_txt = [], []
        for w_id in workloads:
            w = next((x for x in s["workloads"] if x["workload_id"] == w_id), None)
            if not w:
                row_z.append(0)
                row_txt.append("UNSUP")
                continue
            status = w.get("status")
            if status:
                summary = w.get("summary") or {}
                mean_ms = summary.get("mean_ms")
                validation_counts = (w.get("validation_summary") or {}).get("counts") or {}
                valid_ok = validation_counts.get("ok_valid", 0)
                total = len(w.get("results") or [])
                if status == "unsupported":
                    row_z.append(0)
                    row_txt.append("UNSUP")
                elif status == "ok_valid":
                    row_z.append(3)
                    row_txt.append(f"OK<br>{format_ms(mean_ms) if mean_ms is not None else 'n/a'}")
                elif status == "partial_valid":
                    row_z.append(2)
                    row_txt.append(f"PARTIAL<br>{valid_ok}/{total}")
                elif status == "ok_empty":
                    row_z.append(1)
                    row_txt.append("EMPTY")
                elif status == "fail_timeout":
                    row_z.append(1)
                    row_txt.append("TIMEOUT")
                else:
                    row_z.append(1)
                    row_txt.append("FAIL")
            else:
                if "unsupported" in w.get("notes", []) or w.get("tool_name") is None:
                    row_z.append(0)
                    row_txt.append("UNSUP")
                else:
                    ok = len([r for r in w.get("results") if r.get("ok")])
                    total = len(w.get("results"))
                    if ok == total and total > 0:
                        ms = sum(r["ms"] for r in w["results"] if r.get("ok")) / ok
                        row_z.append(3)
                        row_txt.append(f"OK<br>{format_ms(ms)}")
                    elif ok > 0:
                        row_z.append(2)
                        row_txt.append(f"PARTIAL<br>{ok}/{total}")
                    else:
                        errs = set(r.get("error") for r in w.get("results"))
                        label = "TIMEOUT" if "TIMEOUT" in errs else "FAIL"
                        row_z.append(1)
                        row_txt.append(label)
        z.append(row_z)
        text_grid.append(row_txt)

    colorscale = [
        [0.0, THEME["bg_card"]],
        [0.25, THEME["bg_card"]],
        [0.25, THEME["competitor_slow"]],
        [0.5, THEME["competitor_slow"]],  # Fail
        [0.5, THEME["competitor"]],
        [0.75, THEME["competitor"]],  # Partial
        [0.75, THEME["wolfie"]],
        [1.0, THEME["wolfie"]],  # OK
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=workloads,
            y=servers,
            text=text_grid,
            texttemplate="%{text}",
            colorscale=colorscale,
            showscale=False,
            xgap=2,
            ygap=2,
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig = base_layout(
        fig,
        "Coverage & Reliability Heatmap",
        "Green = 100% Success • Orange = Fail/Timeout",
    )
    return fig


# =============================================================================
# 06: MCP TAX
# =============================================================================


def create_mcp_tax():
    mcp_data = load_json(MCP_JSON)
    data = []
    for s in mcp_data["servers"]:
        data.append(
            {"name": clean_name(s["name"]), "init": s["session_initialize"]["ms"]}
        )
    data.sort(key=lambda x: x["init"], reverse=True)

    names = [d["name"] for d in data]
    vals = [d["init"] for d in data]

    fig = go.Figure(
        go.Bar(
            y=names,
            x=vals,
            orientation="h",
            marker_color=THEME["competitor"],
            text=[format_ms(v) for v in vals],
            textposition="outside",
        )
    )

    # Subtle Tax Band
    fig.add_shape(
        type="rect",
        x0=950,
        x1=1100,
        y0=-1,
        y1=len(names),
        fillcolor="rgba(255,140,0, 0.15)",
        line_width=0,
        layer="below",
    )
    fig.add_annotation(
        x=1100,
        y=len(names),
        text="Typical 1s Handshake",
        xanchor="left",
        yanchor="top",
        showarrow=False,
        font=dict(color=THEME["competitor"]),
    )

    fig = base_layout(
        fig, "MCP Setup Tax", "Session initialization overhead (paid once per session)"
    )
    return fig


# =============================================================================
# 07: LATENCY VS TOKENS (PARETO FRONTIER FOCUS)
# =============================================================================


def create_latency_tokens():
    mcp_data = load_json(MCP_JSON)
    wolf_send = load_json(WOLFIES_SEND)

    fig = go.Figure()

    # Wolfies
    wolf_res = next(t for t in wolf_send["tool_results"] if "Wolfies" in t["name"])
    w_pts = []
    for cmd in wolf_res["commands"]:
        if "minimal" in cmd["label"] and cmd["approx_tokens_mean"] > 0:
            w_pts.append((cmd["mean_ms"], cmd["approx_tokens_mean"], cmd["label"]))

    # MCP
    m_pts = []
    for s in mcp_data["servers"]:
        name = clean_name(s["name"])
        for w in s["workloads"]:
            # Check for OK results
            ok = [r for r in w.get("results", []) if r.get("ok")]
            if ok:
                ms = sum(r["ms"] for r in ok) / len(ok)
                tok_vals = [
                    r.get("payload_tokens_est") if r.get("payload_tokens_est") is not None else r.get("approx_tokens")
                    for r in ok
                ]
                tok_vals = [v for v in tok_vals if v is not None]
                tok = sum(tok_vals) / len(tok_vals) if tok_vals else None
                if tok is not None and tok > 0 and ms < 20000:
                    m_pts.append((ms, tok, f"{name}: {w['workload_id']}"))

    # Plot MCP (Background)
    if m_pts:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in m_pts],
                y=[p[1] for p in m_pts],
                mode="markers",
                marker=dict(size=8, color=THEME["competitor"], opacity=0.4),
                name="MCP Tools",
                hovertext=[p[2] for p in m_pts],
                showlegend=True,
            )
        )

    # Plot Wolfies
    if w_pts:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in w_pts],
                y=[p[1] for p in w_pts],
                mode="markers+text",
                marker=dict(size=12, color=THEME["wolfie"]),
                text=[p[2] for p in w_pts],
                textposition="bottom right",
                name="Wolfies",
                showlegend=True,
            )
        )

    fig.update_layout(
        xaxis_title="Latency (ms) - Lower better",
        yaxis_title="Tokens (Log) - Higher content",
        yaxis_type="log",
        yaxis=dict(range=[0, 4]),  # Log10(1) to Log10(10000)
    )

    fig = base_layout(fig, "Latency vs Token Cost", "Speed vs Content Density")
    return fig


# =============================================================================
# 08: READ VS WRITE
# =============================================================================


def create_read_vs_write():
    wolf_send = load_json(WOLFIES_SEND)
    wolf_res = next(t for t in wolf_send["tool_results"] if "Wolfies" in t["name"])

    targets = ["recent_10_minimal", "unread_minimal", "bundle_minimal", "search_small"]
    # Use search_small if minimal not available or map names

    data = []
    for cmd in wolf_res["commands"]:
        lbl = cmd["label"]
        if lbl in targets or "search" in lbl:
            if cmd["read_only"]:
                data.append({"name": lbl, "ms": cmd["mean_ms"], "type": "read"})
        if lbl == "send_message":
            data.append({"name": "SEND (Write)", "ms": cmd["mean_ms"], "type": "write"})

    # keep only distinct interesting reads
    data = [d for d in data if d["ms"] < 200]
    # Ensure Write is there
    send = next((d for d in data if d["type"] == "write"), None)
    if not send:  # Find it again if filtered out (unlikely)
        for cmd in wolf_res["commands"]:
            if cmd["label"] == "send_message":
                data.append(
                    {"name": "SEND (Write)", "ms": cmd["mean_ms"], "type": "write"}
                )

    data.sort(key=lambda x: x["ms"])

    colors = [
        THEME["wolfie"] if d["type"] == "read" else THEME["competitor"] for d in data
    ]

    fig = go.Figure(
        go.Bar(
            x=[d["name"] for d in data],
            y=[d["ms"] for d in data],
            marker_color=colors,
            text=[format_ms(d["ms"]) for d in data],
            textposition="outside",
        )
    )

    fig.add_annotation(
        x="SEND (Write)",
        y=150,
        text="Requires Automation",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(color=THEME["competitor"]),
    )

    fig = base_layout(
        fig,
        "Read vs Write Latency",
        "Read is instant via Sqlite • Write is slower via AppleScript",
    )
    return fig


# =============================================================================
# 09: ECDF (NEW)
# =============================================================================


def create_ecdf_chart():
    """CDF of Per-Iteration Latency for W2_SEARCH."""
    mcp_data = load_json(MCP_JSON)
    wolf_daemon = load_json(WOLFIES_DAEMON)
    wolf_res = wolf_daemon["results"]

    fig = go.Figure()

    # Wolfies Samples
    def add_ecdf(samples, name, color, dash="solid"):
        if not samples:
            return
        samples = sorted(samples)
        # Empirical CDF
        y = [(i + 1) / len(samples) for i in range(len(samples))]
        fig.add_trace(
            go.Scatter(
                x=samples,
                y=y,
                name=name,
                mode="lines",
                line=dict(color=color, width=3, dash=dash),
            )
        )

    # Wolfies Daemon Samples
    d_search = get_wolfie_bench(wolf_res, "daemon_text_search_http_20")
    if d_search and "times" in d_search:
        # Convert sec to ms
        samples = [t * 1000 for t in d_search["times"]]
        add_ecdf(samples, "Wolfies Daemon", THEME["wolfie"])

    # MCP Samples
    targets = ["cardmagic/messages", "imessage-mcp (deno"]
    colors = [THEME["competitor"], THEME["competitor_alt"]]

    for s in mcp_data["servers"]:
        if any(t in s["name"] for t in targets):
            w2 = next(
                (w for w in s["workloads"] if w["workload_id"] == "W2_SEARCH"), None
            )
            if w2 and w2.get("results"):
                samples = [r["ms"] for r in w2["results"] if r.get("ok")]
                if samples:
                    c = colors.pop(0) if colors else THEME["competitor_slow"]
                    add_ecdf(samples, clean_name(s["name"]), c)

    fig.update_layout(
        xaxis_title="Latency (ms)",
        yaxis_title="Probability (CDF)",
        legend=dict(x=0.05, y=0.95, bgcolor="rgba(0,0,0,0.5)"),
    )
    fig = base_layout(
        fig,
        "Consistency: ECDF (W2_SEARCH)",
        "Steeper curve = More Consistent. Left = Faster.",
    )
    fig = add_footnote(fig, "Wolfies is consistently fast. MCP shows high variance.")
    return fig


# =============================================================================
# 10: PARETO FRONTIER (NEW)
# =============================================================================


def create_pareto_frontier():
    """Scatter with Convex Hull/Frontier line."""
    mcp_data = load_json(MCP_JSON)
    wolf_send = load_json(WOLFIES_SEND)

    points = []  # (ms, tokens, name, type)

    # 1. Wolfies
    wolf_res = next(t for t in wolf_send["tool_results"] if "Wolfies" in t["name"])
    for cmd in wolf_res["commands"]:
        if "minimal" in cmd["label"] and cmd["approx_tokens_mean"] > 0:
            points.append(
                {
                    "x": cmd["mean_ms"],
                    "y": cmd["approx_tokens_mean"],
                    "name": cmd["label"],
                    "type": "wolfie",
                }
            )

    # 2. MCP
    for s in mcp_data["servers"]:
        for w in s["workloads"]:
            ok = [r for r in w.get("results", []) if r.get("ok")]
            if ok:
                ms = sum(r["ms"] for r in ok) / len(ok)
                tok_vals = [
                    r.get("payload_tokens_est") if r.get("payload_tokens_est") is not None else r.get("approx_tokens")
                    for r in ok
                ]
                tok_vals = [v for v in tok_vals if v is not None]
                tok = sum(tok_vals) / len(tok_vals) if tok_vals else None
                if tok is not None and tok > 0 and ms < 10000:
                    points.append(
                        {
                            "x": ms,
                            "y": tok,
                            "name": clean_name(s["name"]),
                            "type": "mcp",
                        }
                    )

    # Calculate Frontier: Sort by Y desc (more value), then keep min X
    # Actually for "Cost vs Value" (Latency vs Tokens), usually
    # we want HIGH tokens and LOW latency.
    # So "Good" is Top-Left.
    # Frontier is the set of points where no other point has (higher tokens AND lower latency).

    points.sort(key=lambda p: p["x"])  # Sort by latency ASC
    frontier = []
    max_y_so_far = -1

    for p in points:
        if p["y"] > max_y_so_far:
            frontier.append(p)
            max_y_so_far = p["y"]

    fig = go.Figure()

    # All Points
    wolf_pts = [p for p in points if p["type"] == "wolfie"]
    mcp_pts = [p for p in points if p["type"] == "mcp"]

    fig.add_trace(
        go.Scatter(
            x=[p["x"] for p in mcp_pts],
            y=[p["y"] for p in mcp_pts],
            mode="markers",
            marker=dict(color=THEME["competitor"], opacity=0.3, size=8),
            name="MCP",
            hovertext=[p["name"] for p in mcp_pts],
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[p["x"] for p in wolf_pts],
            y=[p["y"] for p in wolf_pts],
            mode="markers+text",
            marker=dict(color=THEME["wolfie"], size=10),
            text=[p["name"] for p in wolf_pts],
            textposition="top center",
            name="Wolfies",
        )
    )

    # Frontier Line
    fig.add_trace(
        go.Scatter(
            x=[p["x"] for p in frontier],
            y=[p["y"] for p in frontier],
            mode="lines",
            line=dict(color=THEME["text_muted"], dash="dot", width=1),
            name="Efficiency Frontier",
        )
    )

    fig.update_layout(
        xaxis_title="Latency (ms)",
        yaxis_title="Tokens",
        yaxis_type="log",
        xaxis_type="log",
    )

    fig = base_layout(
        fig,
        "Pareto Frontier: Payload vs Speed",
        "Top-Left is optimal (Fast + High Content)",
    )
    return fig


# =============================================================================
# MAIN
# =============================================================================


def main():
    charts = [
        (create_llm_loop_score, "01_llm_loop_score.png"),
        (create_first_vs_warm, "02_first_vs_warm.png"),
        (create_amortization_curve, "03_amortization.png"),
        (create_leaderboards, "04_workload_leaderboards.png"),
        (create_heatmap, "05_coverage_heatmap.png"),
        (create_mcp_tax, "06_mcp_setup_tax.png"),
        (create_latency_tokens, "07_latency_vs_tokens.png"),
        (create_read_vs_write, "08_read_vs_write.png"),
        (create_ecdf_chart, "09_ecdf_latency.png"),
        (create_pareto_frontier, "10_pareto_frontier.png"),
    ]

    print(f"📊 Generating 10 Story Visualizations v3...")
    for func, fname in charts:
        print(f"  → {fname}")
        try:
            fig = func()
            fig.write_image(OUTPUT_DIR / fname, width=1600, height=900, scale=2)
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
