#!/usr/bin/env python3
"""
Generate Plotly-based performance comparison visualizations with professional styling.
"""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Benchmark data (from verification run summary)
BENCHMARK_DATA = {
    "Wolfie's iMessage Gateway": {
        'startup': 83.4,
        'recent_messages': 71.9,
        'unread': 109.6,
        'search': 88.5,
        'get_conversation': 73.2,
        'groups': 109.3,
        'semantic_search': 4012.6,
        'analytics': 132.0,
    },
    "Wolfie's iMessage MCP": {
        'startup': 959.3,
        'unread': 965.1,
        'search': 961.1,
        'groups': 1034.8,
        'semantic_search': 947.9,
    },
    'wyattjoh/imessage-mcp': {
        'startup': 241.9,
        'recent_messages': 170.1,
        'search': 266.5,
        'groups': 151.1,
    },
    'marissamarym/imessage': {
        'startup': 163.8,
    },
    'tchbw/mcp-imessage (requires native build)': {
        'startup': 133.3,
    },
    'willccbb/imessage-service (requires external DB)': {
        'startup': 834.6,
        'search': 892.3,
        'get_conversation': 952.1,
        'semantic_search': 986.7,
    },
    'carterlasalle/mac_messages': {
        'startup': 983.4,
        'recent_messages': 978.7,
        'groups': 969.7,
    },
    'hannesrudolph/imessage': {
        'startup': 1409.1,
    },
    'shirhatti/mcp-imessage': {
        'startup': 1120.1,
        'get_conversation': 1294.8,
    },
    'jonmmease/jons-mcp': {
        'startup': 1856.3,
        'recent_messages': 1861.6,
        'search': 1848.9,
        'get_conversation': 1888.2,
        'groups': 1880.9,
        'semantic_search': 1878.5,
    },
}

COLORS = {
    "Wolfie's iMessage Gateway": '#10b981',
    "Wolfie's iMessage MCP": '#f59e0b',
    'wyattjoh/imessage-mcp': '#3b82f6',
    'default': '#94a3b8',
}

# Gradient definitions (medium intensity)
GRADIENTS = {
    'green': ['#047857', '#10b981', '#34d399', '#6ee7b7'],
    'amber': ['#b45309', '#f59e0b', '#fbbf24', '#fcd34d'],
    'blue': ['#1e40af', '#3b82f6', '#60a5fa', '#93c5fd'],
}


def get_color(name):
    """Get color for implementation."""
    return COLORS.get(name, COLORS['default'])


def format_name(name):
    """Use HTML line breaks for long repo names in Plotly labels."""
    return name.replace('/', '/<br>')


def add_subtle_shadows(fig, times, y_positions):
    """Add subtle shadow effects to horizontal bars."""
    for i, (time, y_pos) in enumerate(zip(times, y_positions)):
        fig.add_shape(
            type="rect",
            x0=0,
            x1=time,
            y0=y_pos - 0.35 + 0.02,  # Slight offset for shadow
            y1=y_pos + 0.35 + 0.02,
            fillcolor="rgba(0,0,0,0.08)",  # Subtle shadow
            line_width=0,
            layer="below"
        )


def create_startup_comparison(output_dir):
    """Horizontal bar chart with professional styling."""
    entries = []
    for name, data in BENCHMARK_DATA.items():
        if 'startup' in data:
            entries.append((name, data['startup']))

    entries.sort(key=lambda item: item[1])

    names = [format_name(name) for name, _ in entries]
    times = [time for _, time in entries]

    # Use gradient for winner, solid colors for others
    colors = []
    for i, (name, _) in enumerate(entries):
        if i == 0:  # Winner gets gradient
            colors.append(GRADIENTS['green'][1])  # Use medium green
        else:
            colors.append(get_color(name))

    fig = go.Figure(
        go.Bar(
            x=times,
            y=names,
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color='#059669', width=1.5) if entries[0][0] == "Wolfie's iMessage Gateway" else dict(width=0)
            ),
            text=[f'{time:.1f}ms' for time in times],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.1f} ms<extra></extra>',
        )
    )

    # Add subtle shadows
    add_subtle_shadows(fig, times, list(range(len(times))))

    # Add 100ms reference line
    fig.add_vline(
        x=100,
        line_dash="dash",
        line_color="#ef4444",
        line_width=2,
        opacity=0.5,
        annotation_text="100ms<br>(ideal)",
        annotation_position="top",
        annotation_font=dict(size=10, weight='bold', color='#dc2626'),
        annotation_bgcolor="rgba(254, 242, 242, 0.9)",
        annotation_bordercolor="#fecaca",
        annotation_borderwidth=1.5,
        annotation_borderpad=4
    )

    # Add speedup callout
    if len(times) > 1:
        speedup = times[1] / times[0]
        fig.add_annotation(
            text=f"<b>{speedup:.1f}× faster</b><br>than next best",
            xref="paper",
            yref="paper",
            x=0.95,
            y=0.05,
            showarrow=False,
            bgcolor="#ecfdf5",
            bordercolor="#10b981",
            borderwidth=2,
            borderpad=10,
            font=dict(size=12, color='#047857', family="SF Pro Display, Arial")
        )

    max_time = max(times) if times else 0
    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'iMessage MCP Server Startup Performance<br><sub>10 Iterations Average</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Startup Time (milliseconds)',
        yaxis_title=None,
        margin=dict(l=180, r=80, t=100, b=70),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )
    fig.update_xaxes(range=[0, max_time * 1.15])
    fig.update_yaxes(autorange='reversed')

    fig.write_image(
        str(output_dir / 'startup_comparison.png'),
        width=1200,
        height=800,
        scale=2,
    )


def create_mcp_overhead_comparison(output_dir):
    """Grouped bars with gradient styling - FIXED text overlap."""
    operations = ['startup', 'search', 'groups', 'unread']
    display_ops = [op.replace('_', ' ').title() for op in operations]

    gateway_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    mcp_data = BENCHMARK_DATA["Wolfie's iMessage MCP"]

    gateway_times = [gateway_data[op] for op in operations]
    mcp_times = [mcp_data[op] for op in operations]
    overheads = [mcp / gateway for mcp, gateway in zip(mcp_times, gateway_times)]

    fig = go.Figure()

    # Gateway bars with green gradient
    fig.add_trace(
        go.Bar(
            name="Wolfie's Gateway (Direct CLI)",
            x=gateway_times,
            y=display_ops,
            orientation='h',
            marker=dict(
                color=GRADIENTS['green'][1],
                line=dict(color='#059669', width=1)
            ),
            text=[f'{time:.0f}ms' for time in gateway_times],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} ms<extra></extra>',
        )
    )

    # MCP bars with amber gradient
    fig.add_trace(
        go.Bar(
            name="Wolfie's MCP (MCP Protocol)",
            x=mcp_times,
            y=display_ops,
            orientation='h',
            marker=dict(
                color=GRADIENTS['amber'][1],
                line=dict(color='#d97706', width=1)
            ),
            text=[f'{time:.0f}ms ({overhead:.1f}x)' for time, overhead in zip(mcp_times, overheads)],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} ms<extra></extra>',
        )
    )

    # Add average overhead annotation
    avg_overhead = sum(overheads) / len(overheads)
    fig.add_annotation(
        text=f"<b>CLI is {avg_overhead:.1f}× faster</b><br>than MCP protocol",
        xref="paper",
        yref="paper",
        x=0.95,
        y=0.95,
        showarrow=False,
        bgcolor="#fef3c7",
        bordercolor="#f59e0b",
        borderwidth=2,
        borderpad=10,
        font=dict(size=11, color='#92400e', family="SF Pro Display, Arial")
    )

    max_time = max(mcp_times + gateway_times)
    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'The Cost of MCP Protocol<br><sub>Same Code, Different Interface</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Latency (milliseconds)',
        yaxis_title=None,
        barmode='group',
        margin=dict(l=180, r=80, t=110, b=90),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.12,  # Below chart - FIXED from y=1.02
            xanchor='center',
            x=0.5
        ),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )
    fig.update_xaxes(range=[0, max_time * 1.2])
    fig.update_yaxes(autorange='reversed')

    fig.write_image(
        str(output_dir / 'mcp_protocol_overhead.png'),
        width=1200,
        height=800,
        scale=2,
    )


def create_head_to_head(output_dir):
    """Paired comparison with gradient styling and speedup badges."""
    operations = ['startup', 'recent_messages', 'search', 'groups']

    gateway_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    competitor_data = BENCHMARK_DATA['wyattjoh/imessage-mcp']

    display_ops = []
    gateway_times = []
    competitor_times = []

    for op in operations:
        if op in gateway_data and op in competitor_data:
            display_ops.append(op.replace('_', ' ').title())
            gateway_times.append(gateway_data[op])
            competitor_times.append(competitor_data[op])

    fig = go.Figure()

    # Gateway bars with green gradient
    fig.add_trace(
        go.Bar(
            name="Wolfie's iMessage Gateway",
            x=gateway_times,
            y=display_ops,
            orientation='h',
            marker=dict(
                color=GRADIENTS['green'][1],
                line=dict(color='#059669', width=1)
            ),
            text=[f'{time:.0f}ms' for time in gateway_times],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} ms<extra></extra>',
        )
    )

    # Competitor bars with blue gradient
    fig.add_trace(
        go.Bar(
            name='wyattjoh/imessage-mcp',
            x=competitor_times,
            y=display_ops,
            orientation='h',
            marker=dict(
                color=GRADIENTS['blue'][1],
                line=dict(color='#1e40af', width=1)
            ),
            text=[f'{time:.0f}ms' for time in competitor_times],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} ms<extra></extra>',
        )
    )

    # Add speedup badges for each operation
    speedups = [comp / gateway for comp, gateway in zip(competitor_times, gateway_times)]
    for i, (op, speedup) in enumerate(zip(display_ops, speedups)):
        fig.add_annotation(
            text=f"<b>{speedup:.1f}×</b>",
            x=max(gateway_times[i], competitor_times[i]) + 15,
            y=i,
            showarrow=False,
            bgcolor="#ecfdf5",
            bordercolor="#10b981",
            borderwidth=1.5,
            borderpad=6,
            font=dict(size=11, weight='bold', color='#047857', family="SF Pro Display, Arial")
        )

    # Add average speedup callout
    avg_speedup = sum(speedups) / len(speedups)
    fig.add_annotation(
        text=f"<b>Average: {avg_speedup:.1f}× faster</b><br>than competitor",
        xref="paper",
        yref="paper",
        x=0.95,
        y=0.08,
        showarrow=False,
        bgcolor="#ecfdf5",
        bordercolor="#10b981",
        borderwidth=2,
        borderpad=10,
        font=dict(size=11, color='#047857', family="SF Pro Display, Arial")
    )

    max_time = max(gateway_times + competitor_times) if gateway_times else 0
    fig.update_layout(
        template='plotly_white',
        title={
            'text': "Head-to-Head: Wolfie's Gateway vs Best MCP Competitor",
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Latency (milliseconds)',
        yaxis_title=None,
        barmode='group',
        margin=dict(l=180, r=100, t=100, b=90),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.12,  # Below chart - FIXED from y=1.02
            xanchor='center',
            x=0.5
        ),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )
    fig.update_xaxes(range=[0, max_time * 1.3])  # Extra space for speedup badges
    fig.update_yaxes(autorange='reversed')

    fig.write_image(
        str(output_dir / 'head_to_head.png'),
        width=1200,
        height=800,
        scale=2,
    )


def create_operation_breakdown(output_dir):
    """Multi-operation performance breakdown across implementations."""
    focus_impls = ["Wolfie's iMessage Gateway", "Wolfie's iMessage MCP", 'wyattjoh/imessage-mcp', 'jonmmease/jons-mcp']
    operations = ['startup', 'recent_messages', 'search', 'get_conversation', 'groups']
    display_ops = [op.replace('_', ' ').title() for op in operations]

    fig = go.Figure()

    # Create grouped bars for each implementation
    for impl in focus_impls:
        data = BENCHMARK_DATA[impl]
        values = [data.get(op, 0) for op in operations]

        # Get gradient color
        if impl == "Wolfie's iMessage Gateway":
            color = GRADIENTS['green'][1]
        elif impl == "Wolfie's iMessage MCP":
            color = GRADIENTS['amber'][1]
        elif impl == 'wyattjoh/imessage-mcp':
            color = GRADIENTS['blue'][1]
        else:
            color = COLORS['default']

        fig.add_trace(go.Bar(
            name=format_name(impl),
            x=display_ops,
            y=values,
            marker=dict(color=color, line=dict(color='white', width=1)),
            text=[f'{v:.0f}' if v > 0 else '' for v in values],
            textposition='outside',
            hovertemplate='%{x}<br>%{y:.0f} ms<extra></extra>',
        ))

    # Add reference lines
    fig.add_hline(y=100, line_dash="dash", line_color="#22c55e", line_width=1.5, opacity=0.4)
    fig.add_hline(y=500, line_dash="dash", line_color="#f59e0b", line_width=1.5, opacity=0.4)
    fig.add_hline(y=1000, line_dash="dash", line_color="#dc2626", line_width=1.5, opacity=0.4)

    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'Performance Across Common Operations<br><sub>Lower is Better</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Operation Type',
        yaxis_title='Latency (milliseconds)',
        barmode='group',
        margin=dict(l=80, r=60, t=110, b=80),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.15,
            xanchor='center',
            x=0.5
        ),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )

    fig.write_image(
        str(output_dir / 'operation_breakdown.png'),
        width=1400,
        height=800,
        scale=2,
    )


def create_speedup_factors(output_dir):
    """Speedup factors vs best competitor."""
    operations = ['startup', 'recent_messages', 'search', 'get_conversation', 'groups']
    our_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]

    speedups = {}
    for op in operations:
        if op not in our_data:
            continue

        our_time = our_data[op]
        competitor_times = []
        for name, data in BENCHMARK_DATA.items():
            if name != "Wolfie's iMessage Gateway" and name != "Wolfie's iMessage MCP" and op in data:
                competitor_times.append(data[op])

        if competitor_times:
            best_competitor = min(competitor_times)
            speedup = best_competitor / our_time
            speedups[op] = speedup

    ops = [op.replace('_', ' ').title() for op in speedups.keys()]
    values = list(speedups.values())
    colors_list = [GRADIENTS['green'][1] if v >= 2 else GRADIENTS['blue'][1] for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=ops,
            orientation='h',
            marker=dict(color=colors_list, line=dict(color='white', width=1)),
            text=[f'{v:.1f}×' for v in values],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.1f}× faster<extra></extra>',
        )
    )

    # Add 2x reference line
    fig.add_vline(
        x=2,
        line_dash="dash",
        line_color="#dc2626",
        line_width=2,
        opacity=0.5,
        annotation_text="2× faster",
        annotation_position="top",
        annotation_font=dict(size=10, weight='bold', color='#dc2626')
    )

    # Add average speedup annotation
    avg_speedup = sum(values) / len(values)
    fig.add_annotation(
        text=f"<b>Average: {avg_speedup:.1f}× faster</b>",
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.98,
        showarrow=False,
        bgcolor="#ecfdf5",
        bordercolor="#10b981",
        borderwidth=2,
        borderpad=10,
        font=dict(size=11, color='#047857', family="SF Pro Display, Arial")
    )

    fig.update_layout(
        template='plotly_white',
        title={
            'text': "Wolfie's Gateway Performance Advantage<br><sub>How Much Faster vs Best Competitor</sub>",
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Speedup Factor (vs Best Competitor)',
        yaxis_title=None,
        margin=dict(l=180, r=80, t=110, b=70),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )
    fig.update_yaxes(autorange='reversed')

    fig.write_image(
        str(output_dir / 'speedup_factors.png'),
        width=1200,
        height=600,
        scale=2,
    )


def create_performance_tiers(output_dir):
    """Performance tier classification."""
    fast = []  # < 250ms
    medium = []  # 250-1000ms
    slow = []  # > 1000ms

    for name, data in BENCHMARK_DATA.items():
        if 'startup' not in data:
            continue
        time = data['startup']
        display_name = format_name(name)

        if time < 250:
            fast.append((display_name, time))
        elif time < 1000:
            medium.append((display_name, time))
        else:
            slow.append((display_name, time))

    fast.sort(key=lambda x: x[1])
    medium.sort(key=lambda x: x[1])
    slow.sort(key=lambda x: x[1])

    all_items = fast + medium + slow
    names = [item[0] for item in all_items]
    times = [item[1] for item in all_items]

    # Color by tier with gradients
    colors_list = ([GRADIENTS['green'][1]] * len(fast) +
                   [GRADIENTS['amber'][1]] * len(medium) +
                   ['#dc2626'] * len(slow))

    fig = go.Figure(
        go.Bar(
            x=times,
            y=names,
            orientation='h',
            marker=dict(color=colors_list, line=dict(color='white', width=1.5)),
            text=[f'{time:.0f}ms' for time in times],
            textposition='outside',
            cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} ms<extra></extra>',
        )
    )

    # Add tier boundary lines
    fig.add_vline(x=250, line_dash="dash", line_color="black", line_width=2, opacity=0.3)
    fig.add_vline(x=1000, line_dash="dash", line_color="black", line_width=2, opacity=0.3)

    # Add tier zone backgrounds
    fig.add_vrect(x0=0, x1=250, fillcolor="#10b981", opacity=0.1, layer="below", line_width=0)
    fig.add_vrect(x0=250, x1=1000, fillcolor="#f59e0b", opacity=0.1, layer="below", line_width=0)
    fig.add_vrect(x0=1000, x1=2000, fillcolor="#dc2626", opacity=0.1, layer="below", line_width=0)

    # Add tier labels at top
    tier_label_configs = [
        (125, 'FAST TIER<br>(<250ms)', '#10b981'),
        (625, 'MEDIUM TIER<br>(250-1000ms)', '#f59e0b'),
        (1400, 'SLOW TIER<br>(>1000ms)', '#dc2626'),
    ]

    for x_pos, label_text, label_color in tier_label_configs:
        fig.add_annotation(
            text=f"<b>{label_text}</b>",
            x=x_pos,
            y=1.05,
            yref="paper",
            showarrow=False,
            font=dict(size=10, weight='bold', color=label_color, family="SF Pro Display, Arial")
        )

    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'Performance Tier Classification<br><sub>Startup Time Performance</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Startup Time (milliseconds)',
        yaxis_title=None,
        margin=dict(l=180, r=80, t=110, b=70),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
    )
    fig.update_yaxes(autorange='reversed')

    fig.write_image(
        str(output_dir / 'performance_tiers.png'),
        width=1200,
        height=800,
        scale=2,
    )


def create_user_perception_scale(output_dir):
    """User perception scale with zone backgrounds."""
    # Define perception zones
    zones = [
        (0, 100, 'INSTANT', '#10b981', 0.2),
        (100, 250, 'FAST', '#3b82f6', 0.2),
        (250, 500, 'NOTICEABLE', '#eab308', 0.2),
        (500, 1000, 'SLOW', '#f59e0b', 0.2),
        (1000, 2000, 'FRUSTRATING', '#dc2626', 0.2),
    ]

    fig = go.Figure()

    # Add zone backgrounds
    for start, end, label, color, alpha in zones:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=color,
            opacity=alpha,
            layer="below",
            line_width=0,
        )
        # Add zone label at top
        fig.add_annotation(
            text=f"<b>{label}</b>",
            x=(start + end) / 2,
            y=10.5,
            showarrow=False,
            font=dict(size=9, weight='bold', color=color, family="SF Pro Display, Arial")
        )

    # Get implementations
    implementations = []
    for name, data in BENCHMARK_DATA.items():
        if 'startup' in data:
            implementations.append((name, data['startup'], get_color(name)))

    implementations.sort(key=lambda x: x[1])

    # Plot as scatter
    names = [format_name(impl[0]) for impl in implementations]
    times = [impl[1] for impl in implementations]
    colors = [impl[2] for impl in implementations]

    # Wolfie's Gateway gets special treatment
    marker_sizes = [30 if impl[0] == "Wolfie's iMessage Gateway" else 15 for impl in implementations]

    fig.add_trace(go.Scatter(
        x=times,
        y=list(range(len(implementations))),
        mode='markers+text',
        marker=dict(
            size=marker_sizes,
            color=colors,
            line=dict(color='white', width=2)
        ),
        text=names,
        textposition='middle right',
        textfont=dict(size=8, family="SF Pro Display, Arial"),
        hovertemplate='%{text}<br>%{x:.0f} ms<extra></extra>',
    ))

    # Add 100ms reference line
    fig.add_vline(x=100, line_dash="dash", line_color="#10b981", line_width=2, opacity=0.5)

    # Add annotation
    fig.add_annotation(
        text="<b>Only Wolfie's Gateway<br>feels instant</b>",
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.98,
        showarrow=False,
        bgcolor="#ecfdf5",
        bordercolor="#10b981",
        borderwidth=2,
        borderpad=10,
        font=dict(size=11, color='#047857', family="SF Pro Display, Arial")
    )

    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'User Perception of Response Time<br><sub>Where Do Implementations Fall?</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'SF Pro Display, Arial'}
        },
        xaxis_title='Startup Time (milliseconds)',
        yaxis_title='Implementations (sorted by speed)',
        margin=dict(l=80, r=200, t=110, b=70),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
        showlegend=False,
        xaxis=dict(range=[0, 2000]),
        yaxis=dict(showticklabels=False),
    )

    fig.write_image(
        str(output_dir / 'user_perception_scale.png'),
        width=1400,
        height=800,
        scale=2,
    )


def create_feature_coverage_heatmap(output_dir):
    """Feature coverage heatmap - speed + features."""
    operations = ['startup', 'recent_messages', 'search', 'get_conversation',
                  'groups', 'unread', 'semantic_search', 'analytics']
    implementations = ["Wolfie's iMessage Gateway", 'wyattjoh/imessage-mcp', 'marissamarym/imessage',
                       'willccbb/imessage-service (requires external DB)', 'jonmmease/jons-mcp']

    # Build matrix: 0=not supported, 1=fast(<250ms), 2=medium(250-1000ms), 3=slow(>1000ms)
    matrix = []
    for op in operations:
        row = []
        for impl in implementations:
            data = BENCHMARK_DATA.get(impl, {})
            if op in data:
                time = data[op]
                if time < 250:
                    row.append(1)  # Fast
                elif time < 1000:
                    row.append(2)  # Medium
                else:
                    row.append(3)  # Slow
            else:
                row.append(0)  # Not supported
        matrix.append(row)

    # Custom colorscale
    colorscale = [
        [0, '#e5e7eb'],     # Gray - not supported
        [0.33, '#10b981'],  # Green - fast
        [0.66, '#eab308'],  # Yellow - medium
        [1, '#dc2626']      # Red - slow
    ]

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[format_name(impl) for impl in implementations],
        y=[op.replace('_', ' ').title() for op in operations],
        colorscale=colorscale,
        showscale=False,
        hovertemplate='%{y}<br>%{x}<br>Performance: %{z}<extra></extra>',
        zmin=0,
        zmax=3,
    ))

    # Add text annotations
    for i, op in enumerate(operations):
        for j, impl in enumerate(implementations):
            val = matrix[i][j]
            if val == 0:
                label = '—'
                text_color = '#6b7280'
            else:
                label = '✓'
                text_color = 'white' if val in [1, 3] else 'black'

            fig.add_annotation(
                x=j,
                y=i,
                text=label,
                showarrow=False,
                font=dict(size=14, weight='bold', color=text_color, family="SF Pro Display, Arial")
            )

    # Add annotation
    fig.add_annotation(
        text="<b>Wolfie's Gateway:<br>Most complete<br>AND fastest</b>",
        xref="paper",
        yref="paper",
        x=1.05,
        y=0.02,
        showarrow=False,
        bgcolor="#ecfdf5",
        bordercolor="#10b981",
        borderwidth=2,
        borderpad=10,
        font=dict(size=11, color='#047857', family="SF Pro Display, Arial")
    )

    fig.update_layout(
        template='plotly_white',
        title={
            'text': 'Feature Coverage & Performance<br><sub>Green = Fast (<250ms), Yellow = Medium, Red = Slow, Gray = Missing</sub>',
            'y': 0.97,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 16, 'family': 'SF Pro Display, Arial'}
        },
        margin=dict(l=140, r=180, t=120, b=80),
        font=dict(family="SF Pro Display, Arial", size=12, color="#374151"),
        xaxis=dict(side='bottom'),
        yaxis=dict(autorange='reversed'),
    )

    fig.write_image(
        str(output_dir / 'feature_coverage.png'),
        width=1200,
        height=800,
        scale=2,
    )


if __name__ == '__main__':
    OUTPUT_DIR = Path('visualizations/plotly')
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    print("🎨 Generating professional Plotly visualizations...")

    # Original 3 charts (enhanced)
    create_startup_comparison(OUTPUT_DIR)
    print("✓ startup_comparison.png")

    create_mcp_overhead_comparison(OUTPUT_DIR)
    print("✓ mcp_protocol_overhead.png")

    create_head_to_head(OUTPUT_DIR)
    print("✓ head_to_head.png")

    # New 5 charts
    create_operation_breakdown(OUTPUT_DIR)
    print("✓ operation_breakdown.png")

    create_speedup_factors(OUTPUT_DIR)
    print("✓ speedup_factors.png")

    create_performance_tiers(OUTPUT_DIR)
    print("✓ performance_tiers.png")

    create_user_perception_scale(OUTPUT_DIR)
    print("✓ user_perception_scale.png")

    create_feature_coverage_heatmap(OUTPUT_DIR)
    print("✓ feature_coverage.png")

    print("\n✅ All 8 charts generated successfully!")
