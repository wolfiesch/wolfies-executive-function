#!/usr/bin/env python3
"""
Generate 'Maximalist' Plotly visualizations for benchmarks.
Style: Dark mode, Neon, Cyberpunk/High-Tech.
Output: visualizations/gemini_maximalist/
"""

from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUTPUT_DIR = Path("visualizations/gemini_maximalist")

# --- DATA ---

BENCHMARK_DATA = {
    "Wolfie's iMessage Gateway": {
        "startup": 83.4,
        "recent_messages": 71.9,
        "unread": 109.6,
        "search": 88.5,
        "get_conversation": 73.2,
        "groups": 109.3,
        "semantic_search": 4012.6,
        "analytics": 132.0,
    },
    "Wolfie's iMessage MCP": {
        "startup": 959.3,
        "unread": 965.1,
        "search": 961.1,
        "groups": 1034.8,
        "semantic_search": 947.9,
    },
    "wyattjoh/imessage-mcp": {
        "startup": 241.9,
        "recent_messages": 170.1,
        "search": 266.5,
        "groups": 151.1,
    },
    "marissamarym/imessage": {
        "startup": 163.8,
    },
    "tchbw/mcp-imessage (requires native build)": {
        "startup": 133.3,
    },
    "willccbb/imessage-service (requires external DB)": {
        "startup": 834.6,
        "search": 892.3,
        "get_conversation": 952.1,
        "semantic_search": 986.7,
    },
    "carterlasalle/mac_messages": {
        "startup": 983.4,
        "recent_messages": 978.7,
        "groups": 969.7,
    },
    "hannesrudolph/imessage": {
        "startup": 1409.1,
    },
    "shirhatti/mcp-imessage": {
        "startup": 1120.1,
        "get_conversation": 1294.8,
    },
    "jonmmease/jons-mcp": {
        "startup": 1856.3,
        "recent_messages": 1861.6,
        "search": 1848.9,
        "get_conversation": 1888.2,
        "groups": 1880.9,
        "semantic_search": 1878.5,
    },
}

# --- STYLING (MAXIMALIST) ---

THEME = {
    "font": "JetBrains Mono, SF Mono, Courier New, monospace",
    "bg_color": "#09090b",  # Zinc-950 (Deep Dark)
    "card_bg": "#18181b",  # Zinc-900
    "grid_color": "#27272a",  # Zinc-800
    "text_primary": "#e4e4e7",  # Zinc-200
    "text_secondary": "#a1a1aa",  # Zinc-400
    "colors": {
        "wolfie_gateway": "#00ff9d",  # Neon Green/Mint
        "wolfie_mcp": "#ffb700",  # Neon Orange/Gold
        "competitor_fast": "#00f0ff",  # Cyan
        "competitor_slow": "#ff0055",  # Neon Pink/Red
        "other": "#52525b",  # Zinc-600
        "glow": "rgba(0, 255, 157, 0.2)",
    },
}


def get_color(name):
    if "Wolfie's iMessage Gateway" in name:
        return THEME["colors"]["wolfie_gateway"]
    if "Wolfie's iMessage MCP" in name:
        return THEME["colors"]["wolfie_mcp"]
    if "wyattjoh" in name or "tchbw" in name or "marissa" in name:
        return THEME["colors"]["competitor_fast"]
    return THEME["colors"]["competitor_slow"]


def clean_name(name):
    if "Wolfie's iMessage Gateway" in name:
        return "WOLFIE_GATEWAY_CLI"
    if "Wolfie's iMessage MCP" in name:
        return "WOLFIE_MCP_PROTO"
    if "wyattjoh" in name:
        return "WYATTJOH/IMESSAGE"
    if "requires native build" in name:
        return "TCHBW/NATIVE"
    if "requires external DB" in name:
        return "WILLCCBB/EXT_DB"
    if "marissa" in name:
        return "MARISSAMARYM"
    return name.split("/")[0].upper()


def common_layout(fig, title, subtitle, xaxis_title=None, yaxis_title=None):
    fig.update_layout(
        template="plotly_dark",
        font=dict(family=THEME["font"], color=THEME["text_primary"]),
        title=dict(
            text=f"<span style='font-size: 28px; letter-spacing: 1px; color: {THEME['text_primary']}'><b>{title.upper()}</b></span><br><span style='font-size: 14px; color: {THEME['text_secondary']}; font-family: sans-serif'>// {subtitle}</span>",
            y=0.96,
            x=0.01,
            xanchor="left",
            yanchor="top",
        ),
        margin=dict(t=110, l=80, r=40, b=80),
        xaxis=dict(
            title=dict(
                text=xaxis_title.upper() if xaxis_title else None,
                font=dict(size=12, color=THEME["text_secondary"], weight="bold"),
            ),
            gridcolor=THEME["grid_color"],
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor=THEME["grid_color"],
            linewidth=2,
            tickfont=dict(color=THEME["text_secondary"], size=12),
        ),
        yaxis=dict(
            title=dict(
                text=yaxis_title.upper() if yaxis_title else None,
                font=dict(size=12, color=THEME["text_secondary"], weight="bold"),
            ),
            gridcolor=THEME["grid_color"],
            zeroline=False,
            tickfont=dict(color=THEME["text_primary"], size=12, weight="bold"),
        ),
        plot_bgcolor=THEME["bg_color"],
        paper_bgcolor=THEME["bg_color"],
        showlegend=False,
        bargap=0.3,
    )
    return fig


# --- CHARTS ---


def create_startup_comparison():
    data = []
    for name, metrics in BENCHMARK_DATA.items():
        if "startup" in metrics:
            data.append(
                {
                    "name": clean_name(name),
                    "value": metrics["startup"],
                    "color": get_color(name),
                }
            )

    data.sort(key=lambda x: x["value"])  # Fastest first

    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    fig = go.Figure(
        go.Bar(
            x=names,  # Switched to Vertical
            y=values,  # Switched to Vertical
            marker=dict(
                color=colors,
                line=dict(width=0),
            ),
            text=[f"<b>{v:.0f}</b>" for v in values],
            textposition="outside",
            texttemplate="%{text}<span style='font-size:10px; color:#52525b'> ms</span>",
            textfont=dict(family=THEME["font"], size=14, color=THEME["text_primary"]),
            cliponaxis=False,
        )
    )

    # "WIN" Tag
    fig.add_annotation(
        x=0,  # Anchor key
        y=values[0],
        text="WINNER",
        showarrow=True,
        arrowcolor=THEME["colors"]["wolfie_gateway"],
        arrowhead=2,
        ax=0,
        ay=-40,  # Point down
        bgcolor=THEME["colors"]["wolfie_gateway"],
        bordercolor=THEME["colors"]["wolfie_gateway"],
        font=dict(color="black", size=11, weight="bold"),
    )

    # 100ms threshold
    fig.add_hline(
        y=100, line_width=2, line_dash="dash", line_color=THEME["text_secondary"]
    )
    fig.add_annotation(
        x=0,
        y=100,
        text="INSTANT_THRESHOLD <100ms",
        showarrow=False,
        yanchor="bottom",
        xanchor="left",
        font=dict(size=10, color=THEME["text_secondary"]),
    )

    fig = common_layout(
        fig,
        "System Init Velocity",
        "TIME TO FIRST TOKEN (MS) // LOWER IS BETTER",
        yaxis_title="LATENCY (MS)",
    )

    fig.update_yaxes(range=[0, max(values) * 1.3])
    fig.update_xaxes(tickangle=-45)

    return fig


def create_head_to_head():
    ops = ["startup", "recent_messages", "search", "groups"]
    ops_labels = [o.upper() for o in ops]

    wolfie = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    y_wolfie = [wolfie.get(op, 0) for op in ops]

    comp = BENCHMARK_DATA["wyattjoh/imessage-mcp"]
    y_comp = [comp.get(op, 0) for op in ops]

    speedups = [c / w for w, c in zip(y_wolfie, y_comp)]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="WOLFIE",
            x=y_wolfie,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_gateway"],
            text=[f"{v:.0f}" for v in y_wolfie],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="COMPETITOR",
            x=y_comp,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["competitor_fast"],
            text=[f"{v:.0f}" for v in y_comp],
            textposition="auto",
        )
    )

    fig = common_layout(
        fig,
        "Head-to-Head",
        "WOLFIE GATEWAY VS NEAREST RIVAL",
        xaxis_title="LATENCY (MS)",
    )

    fig.update_layout(
        barmode="group",
        legend=dict(orientation="h", y=-0.15, x=0),
        showlegend=True,
        legend_font_size=12,
        margin=dict(l=150),  # Added padding
    )
    fig.update_yaxes(autorange="reversed")

    for i, speedup in enumerate(speedups):
        max_val = max(y_wolfie[i], y_comp[i])
        fig.add_annotation(
            x=max_val + 50,
            y=i,
            text=f"<span style='color:{THEME['colors']['wolfie_gateway']}; font-size: 16px'><b>{speedup:.1f}x</b></span>",
            showarrow=False,
            xanchor="left",
            bgcolor=THEME["card_bg"],
            bordercolor=THEME["colors"]["wolfie_gateway"],
            borderwidth=1,
            borderpad=4,
        )

    fig.update_xaxes(range=[0, max(y_comp) * 1.4])

    return fig


def create_mcp_overhead():
    ops = ["startup", "search", "groups", "unread"]
    ops_labels = [o.upper() for o in ops]

    gateway = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    mcp = BENCHMARK_DATA["Wolfie's iMessage MCP"]

    y_gw = [gateway.get(op, 0) for op in ops]
    y_mcp = [mcp.get(op, 0) for op in ops]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="CLI METAL",
            x=y_gw,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_gateway"],
            text=[f"{v:.0f}" for v in y_gw],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="MCP PROTOCOL (OVERHEAD)",
            x=y_mcp,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_mcp"],
            text=[f"{v:.0f}" for v in y_mcp],
            textposition="auto",
        )
    )

    fig = common_layout(
        fig,
        "Protocol Tax",
        "COST OF ABSTRACTION LAYER (MCP)",
        xaxis_title="LATENCY (MS)",
    )

    fig.update_layout(
        barmode="overlay", showlegend=True, legend=dict(orientation="h", y=-0.15, x=0)
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[0, max(y_mcp) * 1.2])

    return fig


def create_performance_tiers():
    data = []
    for name, metrics in BENCHMARK_DATA.items():
        if "startup" in metrics:
            val = metrics["startup"]
            color = (
                THEME["colors"]["wolfie_gateway"]
                if val < 250
                else (
                    THEME["colors"]["wolfie_mcp"]
                    if val < 1000
                    else THEME["colors"]["competitor_slow"]
                )
            )
            data.append({"name": clean_name(name), "value": val, "color": color})

    data.sort(key=lambda x: x["value"])
    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    fig = go.Figure(
        go.Scatter(
            x=values,
            y=names,
            mode="markers",
            marker=dict(size=12, color=colors, symbol="square"),
        )
    )

    # Add connecting lines or stems
    for n, v, c in zip(names, values, colors):
        fig.add_shape(type="line", x0=0, y0=n, x1=v, y1=n, line=dict(color=c, width=2))

    # Zones
    fig.add_vrect(
        x0=0,
        x1=250,
        fillcolor=THEME["colors"]["wolfie_gateway"],
        opacity=0.08,
        layer="below",
        annotation_text="S-TIER",
        annotation_position="top left",
    )
    fig.add_vrect(
        x0=250,
        x1=1000,
        fillcolor=THEME["colors"]["wolfie_mcp"],
        opacity=0.08,
        layer="below",
        annotation_text="A-TIER",
        annotation_position="top left",
    )

    fig = common_layout(
        fig, "Tier List", "RANKING BY RESPONSE CLASS", xaxis_title="STARTUP (MS)"
    )
    fig.update_yaxes(autorange="reversed")

    return fig


def create_operation_breakdown():
    ops = ["startup", "recent_messages", "search", "get_conversation", "groups"]
    ops_labels = [o.upper() for o in ops]
    impls = [
        "Wolfie's iMessage Gateway",
        "Wolfie's iMessage MCP",
        "wyattjoh/imessage-mcp",
        "jonmmease/jons-mcp",
    ]

    fig = go.Figure()

    for impl in impls:
        data = BENCHMARK_DATA.get(impl, {})
        y_vals = [data.get(op, 0) for op in ops]

        fig.add_trace(
            go.Bar(
                name=clean_name(impl),
                x=ops_labels,
                y=y_vals,
                marker_color=get_color(impl),
                textposition="none",
            )
        )

    fig = common_layout(
        fig,
        "Full Spectrum Ops",
        "CROSS-FUNCTIONAL PERFORMANCE ANALYSIS",
        yaxis_title="LATENCY (MS)",
    )
    fig.update_layout(
        barmode="group", legend=dict(orientation="h", y=-0.2), showlegend=True
    )
    return fig


def create_speedup_factors():
    ops = ["startup", "recent_messages", "search", "get_conversation", "groups"]
    our_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    speedups = {}
    for op in ops:
        if op not in our_data:
            continue
        our_time = our_data[op]
        comp_times = [
            data[op]
            for name, data in BENCHMARK_DATA.items()
            if not name.startswith("Wolfie") and op in data
        ]
        if comp_times:
            speedups[op] = min(comp_times) / our_time

    sorted_ops = sorted(speedups.keys(), key=lambda k: speedups[k])
    x_labels = [o.upper() for o in sorted_ops]
    y_vals = [speedups[o] for o in sorted_ops]

    fig = go.Figure(
        go.Scatter(
            x=y_vals,
            y=x_labels,
            mode="markers+text",
            marker=dict(
                color=THEME["colors"]["wolfie_gateway"], size=20, symbol="diamond"
            ),
            text=[f"{v:.1f}x" for v in y_vals],
            textposition="top right",
            textfont=dict(
                color=THEME["colors"]["wolfie_gateway"], size=14, weight="bold"
            ),
        )
    )

    for y, x in zip(x_labels, y_vals):
        fig.add_shape(
            type="line",
            x0=1,
            y0=y,
            x1=x,
            y1=y,
            line=dict(color=THEME["text_secondary"], width=1, dash="dot"),
        )

    fig.add_vline(x=1, line_color=THEME["text_primary"], line_width=2)

    fig = common_layout(
        fig,
        "Dominance Factor",
        "MULTIPLIER VS STRONGEST COMPETITOR",
        xaxis_title="FACTOR (X)",
    )
    return fig


def create_user_perception_scale():
    data = []
    for name, metrics in BENCHMARK_DATA.items():
        if "startup" in metrics:
            data.append(
                {
                    "name": clean_name(name),
                    "value": metrics["startup"],
                    "color": get_color(name),
                }
            )
    data.sort(key=lambda x: x["value"], reverse=True)

    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=values,
            y=names,
            mode="markers",
            marker=dict(color=colors, size=14, line=dict(width=2, color="black")),
        )
    )

    fig = common_layout(
        fig,
        "Perception Horizon",
        "INTERACTION LATENCY TIMELINE",
        xaxis_title="TIME (MS)",
    )
    # Log scale for drama
    fig.update_xaxes(type="log", title="TIME (MS) // LOG SCALE")

    return fig


def create_feature_coverage():
    ops = [
        "startup",
        "recent_messages",
        "search",
        "get_conversation",
        "groups",
        "semantic_search",
        "analytics",
    ]
    impls = [
        "Wolfie's iMessage Gateway",
        "Wolfie's iMessage MCP",
        "wyattjoh/imessage-mcp",
        "jonmmease/jons-mcp",
    ]

    z = []
    for impl in impls:
        row = []
        data = BENCHMARK_DATA.get(impl, {})
        for op in ops:
            row.append(1 if op in data else 0)
        z.append(row)

    z = z[::-1]
    impls_rev = [clean_name(i) for i in impls][::-1]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[o.upper() for o in ops],
            y=impls_rev,
            colorscale=[[0, "#18181b"], [1, THEME["colors"]["wolfie_gateway"]]],
            showscale=False,
            xgap=3,
            ygap=3,
        )
    )

    fig = common_layout(fig, "Matrix Coverage", "CAPABILITY SIGNATURES")
    return fig


def create_github_stars():
    repo_data = [
        ("carterlasalle/mac_messages", 207),
        ("hannesrudolph/imessage", 72),
        ("marissamarym/imessage", 21),
        ("wyattjoh/imessage-mcp", 18),
        ("willccbb/imessage-service", 14),
        ("tchbw/mcp-imessage", 6),
        ("shirhatti/mcp-imessage", 2),
        ("jonmmease/jons-mcp", 1),
        ("Wolfie's Gateway", 1),
    ]
    repo_data.sort(key=lambda x: x[1])
    names = [r[0].upper() for r in repo_data]
    values = [r[1] for r in repo_data]

    # Color logic maximalist
    colors = []
    for n in names:
        if "WOLFIE" in n:
            colors.append(THEME["colors"]["wolfie_gateway"])
        elif "CARTER" in n:
            colors.append(THEME["colors"]["competitor_fast"])
        else:
            colors.append(THEME["colors"]["other"])

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v}" for v in values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                family=THEME["font"],
                size=14,
                color=THEME["text_primary"],
                weight="bold",
            ),
        )
    )

    fig = common_layout(
        fig,
        "Repo Gravity",
        "GITHUB STAR COUNT // ADOPTION METRICS",
        xaxis_title="STARS",
    )
    fig.update_xaxes(range=[0, max(values) * 1.2])
    return fig


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    charts = [
        (create_startup_comparison, "startup_comparison.png"),
        (create_head_to_head, "head_to_head.png"),
        (create_mcp_overhead, "mcp_protocol_overhead.png"),
        (create_performance_tiers, "performance_tiers.png"),
        (create_operation_breakdown, "operation_breakdown.png"),
        (create_speedup_factors, "speedup_factors.png"),
        (create_user_perception_scale, "user_perception_scale.png"),
        (create_feature_coverage, "feature_coverage.png"),
        (create_github_stars, "github_stars.png"),
    ]

    print(f"Generating MAXIMALIST visuals in {OUTPUT_DIR}...")
    for func, fname in charts:
        print(f"  Rendering {fname}...")
        try:
            fig = func()
            fig.write_image(
                OUTPUT_DIR / fname, width=1200, height=800, scale=2, engine="kaleido"
            )
        except Exception as e:
            print(f"  Error rendering {fname}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
