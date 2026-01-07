#!/usr/bin/env python3
"""
Generate 'Gemini-tier' refined Plotly visualizations for benchmarks.
Output: visualizations/gemini_attempt/
"""

from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

OUTPUT_DIR = Path("visualizations/gemini_attempt")

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

# --- STYLING ---

THEME = {
    "font": "SF Pro Display, Inter, system-ui, sans-serif",
    "bg_color": "#ffffff",
    "grid_color": "#f1f5f9",  # Slate-100
    "text_primary": "#0f172a",  # Slate-900
    "text_secondary": "#64748b",  # Slate-500
    "colors": {
        "wolfie_gateway": "#059669",  # Emerald-600
        "wolfie_mcp": "#d97706",  # Amber-600
        "competitor_best": "#3b82f6",  # Blue-500
        "other": "#94a3b8",  # Slate-400
        "slow": "#ef4444",  # Red-500
    },
}


def get_color(name):
    if "Wolfie's iMessage Gateway" in name:
        return THEME["colors"]["wolfie_gateway"]
    if "Wolfie's iMessage MCP" in name:
        return THEME["colors"]["wolfie_mcp"]
    if "wyattjoh" in name:
        return THEME["colors"]["competitor_best"]
    return THEME["colors"]["other"]


def clean_name(name):
    """Shorten names for cleaner labels"""
    if "Wolfie's iMessage Gateway" in name:
        return "Wolfie's Gateway (CLI)"
    if "Wolfie's iMessage MCP" in name:
        return "Wolfie's MCP"
    if "requires native build" in name:
        return "tchbw/mcp-imessage"
    if "requires external DB" in name:
        return "willccbb/imessage-service"
    return name


def common_layout(fig, title, subtitle, xaxis_title=None, yaxis_title=None):
    fig.update_layout(
        template="plotly_white",
        font=dict(family=THEME["font"], color=THEME["text_primary"]),
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size: 14px; color: {THEME['text_secondary']}'>{subtitle}</span>",
            y=0.96,
            x=0.01,
            xanchor="left",
            yanchor="top",
            font=dict(size=24),
        ),
        margin=dict(t=100, l=80, r=40, b=60),
        xaxis=dict(
            title=dict(
                text=xaxis_title, font=dict(size=12, color=THEME["text_secondary"])
            ),
            gridcolor=THEME["grid_color"],
            zeroline=False,
            showline=True,
            linecolor=THEME["grid_color"],
            tickfont=dict(color=THEME["text_secondary"]),
        ),
        yaxis=dict(
            title=dict(
                text=yaxis_title, font=dict(size=12, color=THEME["text_secondary"])
            ),
            gridcolor=THEME["grid_color"],
            zeroline=False,
            tickfont=dict(color=THEME["text_secondary"]),
        ),
        plot_bgcolor=THEME["bg_color"],
        paper_bgcolor=THEME["bg_color"],
        showlegend=False,
        bargap=0.25,
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
                    "full_name": name,
                }
            )

    data.sort(key=lambda x: x["value"])  # Fastest first

    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    opacities = [1.0 if i < 3 else 0.7 for i in range(len(data))]

    fig = go.Figure(
        go.Bar(
            x=names,  # Switched to Vertical
            y=values,  # Switched to Vertical
            marker=dict(
                color=colors,
                opacity=opacities,
                line=dict(width=0),
                cornerradius=4,
            ),
            text=[f"<b>{v:.0f}</b>" for v in values],
            textposition="outside",
            textfont=dict(family=THEME["font"], size=12, color=THEME["text_secondary"]),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>%{y:.1f} ms<extra></extra>",
        )
    )

    # 100ms threshold
    fig.add_hline(
        y=100,
        line_width=1,
        line_dash="dash",
        line_color=THEME["text_secondary"],
        opacity=0.5,
    )
    fig.add_annotation(
        x=0,  # Anchor to left
        y=100,
        text="100ms (Instant)",
        showarrow=False,
        yanchor="bottom",
        xanchor="left",
        font=dict(size=10, color=THEME["text_secondary"]),
    )

    fig = common_layout(
        fig,
        "Startup Latency",
        "Time to first response (lower is better)",
        yaxis_title="Milliseconds",
    )

    # Remove reversed autorange since low is now bottom, which is standard for Y axis
    # But usually latency charts might want low at top? No, standard bar chart: height = latency.
    # User said "flip vertically", so bars grow up.

    fig.update_yaxes(range=[0, max(values) * 1.25])
    fig.update_xaxes(tickangle=-45)

    return fig


def create_head_to_head():
    ops = ["startup", "recent_messages", "search", "groups"]
    ops_labels = [o.replace("_", " ").title() for o in ops]

    wolfie = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    y_wolfie = [wolfie.get(op, 0) for op in ops]

    comp = BENCHMARK_DATA["wyattjoh/imessage-mcp"]
    y_comp = [comp.get(op, 0) for op in ops]

    # Calculation of speedup
    speedups = [c / w for w, c in zip(y_wolfie, y_comp)]

    fig = go.Figure()

    # Grouped Bar
    fig.add_trace(
        go.Bar(
            name="Wolfie's Gateway",
            x=y_wolfie,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_gateway"],
            text=[f"{v:.0f}ms" for v in y_wolfie],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Best Competitor (wyattjoh)",
            x=y_comp,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["competitor_best"],
            text=[f"{v:.0f}ms" for v in y_comp],
            textposition="auto",
        )
    )

    fig = common_layout(
        fig,
        "Head-to-Head Architecture",
        "Direct CLI Gateway vs Best-in-Class MCP Implementation",
        xaxis_title="Latency (ms)",
    )

    fig.update_layout(
        barmode="group",
        legend=dict(orientation="h", y=-0.15, x=0),
        margin=dict(l=150),  # Added padding
    )
    fig.update_yaxes(autorange="reversed")

    # Add badges for speedup
    for i, speedup in enumerate(speedups):
        max_val = max(y_wolfie[i], y_comp[i])
        fig.add_annotation(
            x=max_val + (max(y_comp) * 0.02),
            y=i,
            text=f"<span style='color:{THEME['colors']['wolfie_gateway']}'><b>{speedup:.1f}x Faster</b></span>",
            showarrow=False,
            xanchor="left",
            font=dict(size=12),
        )

    fig.update_xaxes(range=[0, max(y_comp) * 1.3])

    return fig


def create_mcp_overhead():
    ops = ["startup", "search", "groups", "unread"]
    ops_labels = [o.replace("_", " ").title() for o in ops]

    gateway = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    mcp = BENCHMARK_DATA["Wolfie's iMessage MCP"]

    y_gw = [gateway.get(op, 0) for op in ops]
    y_mcp = [mcp.get(op, 0) for op in ops]
    overheads = [m / g for m, g in zip(y_mcp, y_gw)]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Direct Gateway (CLI)",
            x=y_gw,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_gateway"],
            text=[f"{v:.0f}ms" for v in y_gw],
            textposition="inside",
            textfont=dict(color="white"),
        )
    )

    fig.add_trace(
        go.Bar(
            name="MCP Protocol Wrapper",
            x=y_mcp,
            y=ops_labels,
            orientation="h",
            marker_color=THEME["colors"]["wolfie_mcp"],
            text=[
                f"{m:.0f}ms (+{((m - g) / g) * 100:.0f}%)" for m, g in zip(y_mcp, y_gw)
            ],
            textposition="outside",
            textfont=dict(color=THEME["colors"]["wolfie_mcp"]),
        )
    )

    fig = common_layout(
        fig,
        "The Cost of Protocol Abstraction",
        "Performance penalty introduced by the MCP specification layer",
        xaxis_title="Latency (ms)",
    )

    fig.update_layout(
        barmode="group", showlegend=True, legend=dict(orientation="h", y=-0.15, x=0)
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[0, max(y_mcp) * 1.25])

    return fig


def create_performance_tiers():
    # Helper to categorize
    def get_tier(ms):
        if ms < 250:
            return "Fast (<250ms)", 0, THEME["colors"]["wolfie_gateway"]
        if ms < 1000:
            return "Acceptable (<1s)", 1, THEME["colors"]["wolfie_mcp"]
        return "Sluggish (>1s)", 2, THEME["colors"]["slow"]

    data = []
    for name, metrics in BENCHMARK_DATA.items():
        if "startup" in metrics:
            val = metrics["startup"]
            tier, rank, color = get_tier(val)
            data.append(
                {
                    "name": clean_name(name),
                    "value": val,
                    "tier": tier,
                    "rank": rank,
                    "color": color,
                }
            )

    data.sort(key=lambda x: (x["rank"], x["value"]))

    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    fig = go.Figure(
        go.Bar(
            x=names,
            y=values,
            marker_color=colors,
            text=[f"{v:.0f}ms" for v in values],
            textposition="auto",
        )
    )

    # Add shapes/regions for tiers
    fig.add_hline(
        y=250, line_dash="dot", line_color=THEME["text_secondary"], opacity=0.3
    )
    fig.add_hline(
        y=1000, line_dash="dot", line_color=THEME["text_secondary"], opacity=0.3
    )

    fig.add_annotation(
        x=0,
        y=250,
        text="Fast Threshold",
        xanchor="left",
        yanchor="bottom",
        showarrow=False,
        font=dict(size=10, color=THEME["text_secondary"]),
    )

    fig = common_layout(
        fig,
        "Response Tiers",
        "Categorizing implementations by user perception metrics",
        yaxis_title="Startup Time (ms)",
    )

    return fig


def create_operation_breakdown():
    ops = ["startup", "recent_messages", "search", "get_conversation", "groups"]
    ops_labels = [o.replace("_", " ").title() for o in ops]

    # Focus implementations
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
                text=[f"{v:.0f}" if v > 0 else "" for v in y_vals],
                textposition="auto",
            )
        )

    fig = common_layout(
        fig,
        "Operation Breakdown",
        "Latency across different operation types (logarithmic scale recommended for large variances)",
        yaxis_title="Latency (ms)",
    )

    fig.update_layout(
        barmode="group", legend=dict(orientation="h", y=-0.2, x=0), showlegend=True
    )

    # Add simple grid lines reference
    fig.add_hline(y=100, line_dash="dot", opacity=0.3)
    fig.add_hline(y=1000, line_dash="dot", opacity=0.3)

    return fig


def create_speedup_factors():
    ops = ["startup", "recent_messages", "search", "get_conversation", "groups"]

    our_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]

    speedups = {}
    for op in ops:
        if op not in our_data:
            continue

        our_time = our_data[op]
        # Find best competitor time
        comp_times = []
        for name, data in BENCHMARK_DATA.items():
            if name.startswith("Wolfie"):
                continue
            if op in data:
                comp_times.append(data[op])

        if comp_times:
            best = min(comp_times)
            speedups[op] = best / our_time

    # Sort
    sorted_ops = sorted(speedups.keys(), key=lambda k: speedups[k])

    x_labels = [o.replace("_", " ").title() for o in sorted_ops]
    y_vals = [speedups[o] for o in sorted_ops]
    colors = [
        THEME["colors"]["wolfie_gateway"]
        if v >= 2
        else THEME["colors"]["competitor_best"]
        for v in y_vals
    ]

    fig = go.Figure(
        go.Bar(
            x=y_vals,
            y=x_labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}x" for v in y_vals],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig.add_vline(
        x=1, line_dash="solid", line_color=THEME["text_primary"], line_width=1
    )

    fig = common_layout(
        fig,
        "Competitive Advantage",
        "Speedup factor vs. nearest competitor (1.0x = Parity)",
        xaxis_title="Speedup Factor (x)",
    )

    return fig


def create_user_perception_scale():
    # Dot plot on a log-like scale (or linear with tiers)

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

    data.sort(key=lambda x: x["value"], reverse=True)  # Slow to Fast

    names = [d["name"] for d in data]
    values = [d["value"] for d in data]
    colors = [d["color"] for d in data]

    fig = go.Figure()

    # Plot points
    fig.add_trace(
        go.Scatter(
            x=values,
            y=names,
            mode="markers+text",
            marker=dict(
                color=colors,
                size=[16 if "Wolfie" in n else 10 for n in names],
                line=dict(color="white", width=1),
            ),
            text=[f"  {v:.0f}ms" for v in values],
            textposition="middle right",
        )
    )

    # Zones vertically
    fig.add_vrect(
        x0=0,
        x1=100,
        fillcolor=THEME["colors"]["wolfie_gateway"],
        opacity=0.1,
        layer="below",
        annotation_text="Instant",
    )
    fig.add_vrect(
        x0=100,
        x1=500,
        fillcolor=THEME["colors"]["competitor_best"],
        opacity=0.05,
        layer="below",
        annotation_text="Fast",
    )
    fig.add_vrect(
        x0=1000,
        x1=3000,
        fillcolor=THEME["colors"]["slow"],
        opacity=0.05,
        layer="below",
        annotation_text="Slow",
    )

    fig = common_layout(
        fig,
        "User Perception Scale",
        "Where implementations fall on the UX timeline",
        xaxis_title="Startup Response (ms)",
    )

    fig.update_xaxes(range=[0, 2000])  # Cap at 2s to show detail

    return fig


def create_feature_coverage_heatmap():
    # Heatmap of capabilities (dummy data based on metrics presence)
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

    z_data = []
    text_data = []

    for impl in impls:
        row = []
        text_row = []
        data = BENCHMARK_DATA.get(impl, {})
        for op in ops:
            if op in data:
                row.append(1)
                text_row.append("✓")
            else:
                row.append(0)
                text_row.append("")
        z_data.append(row)
        text_data.append(text_row)

    z_data = z_data[::-1]  # Reverse for plotting bottom-up if needed, or matched to y
    text_data = text_data[::-1]
    impls_rev = [clean_name(i) for i in impls][::-1]

    fig = go.Figure(
        go.Heatmap(
            z=z_data,
            x=[o.replace("_", " ").title() for o in ops],
            y=impls_rev,
            colorscale=[[0, "#f1f5f9"], [1, THEME["colors"]["wolfie_gateway"]]],
            text=text_data,
            texttemplate="%{text}",
            showscale=False,
            xgap=2,
            ygap=2,
        )
    )

    fig = common_layout(
        fig,
        "Feature Coverage",
        "Supported operations across implementations",
    )

    return fig


def create_github_stars():
    # Data manually gathered
    repo_data = [
        ("carterlasalle/mac_messages", 207),
        ("hannesrudolph/imessage", 72),
        ("marissamarym/imessage", 21),
        ("wyattjoh/imessage-mcp", 18),
        ("willccbb/imessage-service", 14),
        ("tchbw/mcp-imessage", 6),
        ("shirhatti/mcp-imessage", 2),  # Estimated <5
        ("jonmmease/jons-mcp", 1),  # Estimated <5
        ("Wolfie's Gateway", 1),
    ]

    repo_data.sort(key=lambda x: x[1])

    names = [r[0] for r in repo_data]
    values = [r[1] for r in repo_data]
    colors = [
        THEME["colors"]["wolfie_gateway"]
        if "Wolfie" in n
        else THEME["colors"]["competitor_best"]
        if "carter" in n
        else THEME["colors"]["other"]
        for n in names
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{v}" for v in values],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig = common_layout(
        fig,
        "Community Adoption (GitHub Stars)",
        "Popularity of public implementations",
        xaxis_title="Stars",
    )

    fig.update_xaxes(range=[0, max(values) * 1.15])

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
        (create_feature_coverage_heatmap, "feature_coverage.png"),
        (create_github_stars, "github_stars.png"),
    ]

    print(f"Generating optimized visualizations in {OUTPUT_DIR}...")

    for func, filename in charts:
        print(f"  Rendering {filename}...")
        fig = func()
        fig.write_image(
            OUTPUT_DIR / filename,
            width=1200,
            height=800,
            scale=2,  # Retina quality
            engine="kaleido",
        )

    print("Done.")


if __name__ == "__main__":
    main()
