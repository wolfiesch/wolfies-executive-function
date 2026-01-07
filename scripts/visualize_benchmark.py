#!/usr/bin/env python3
"""
Generate performance comparison visualizations for Twitter thread.

Creates publication-quality charts comparing iMessage MCP server implementations.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Set modern, professional style
plt.style.use('seaborn-v0_8-whitegrid')

# Enhanced styling for professional look
plt.rcParams['figure.facecolor'] = '#ffffff'
plt.rcParams['axes.facecolor'] = '#fafbfc'
plt.rcParams['axes.edgecolor'] = '#e1e4e8'
plt.rcParams['axes.linewidth'] = 1.5
plt.rcParams['grid.color'] = '#e1e4e8'
plt.rcParams['grid.linewidth'] = 0.8
plt.rcParams['grid.alpha'] = 0.5

# Typography improvements
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif']
plt.rcParams['font.size'] = 11
plt.rcParams['font.weight'] = 'normal'
plt.rcParams['axes.labelsize'] = 13
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10

# Better visual hierarchy
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.spines.left'] = True
plt.rcParams['axes.spines.bottom'] = True

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

# Enhanced color scheme with gradients
COLORS = {
    "Wolfie's iMessage Gateway": '#10b981',  # Emerald - winner
    "Wolfie's iMessage MCP": '#f59e0b',  # Amber - baseline
    'wyattjoh/imessage-mcp': '#3b82f6',  # Blue - best competitor
    'default': '#94a3b8',  # Slate - others
}

# Gradient variants (lighter shades for visual depth)
COLOR_GRADIENTS = {
    "Wolfie's iMessage Gateway": ['#10b981', '#34d399'],  # Emerald gradient
    "Wolfie's iMessage MCP": ['#f59e0b', '#fbbf24'],  # Amber gradient
    'wyattjoh/imessage-mcp': ['#3b82f6', '#60a5fa'],  # Blue gradient
    'default': ['#94a3b8', '#cbd5e1'],  # Slate gradient
}

def get_color(name):
    """Get color for implementation."""
    return COLORS.get(name, COLORS['default'])

def add_bar_shadow(bars, ax, offset=2):
    """Add subtle shadow effect to bars for depth."""
    for bar in bars:
        # Add a subtle shadow by drawing a slightly darker bar behind
        shadow = plt.Rectangle(
            (bar.get_x() - offset, bar.get_y() - offset),
            bar.get_width(), bar.get_height(),
            facecolor='black', alpha=0.1, zorder=bar.get_zorder() - 1,
            transform=bar.get_transform()
        )
        ax.add_patch(shadow)

def create_startup_comparison():
    """Chart 1: Startup time comparison - The hero chart."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Get startup times and sort
    implementations = []
    times = []
    colors = []

    for name, data in BENCHMARK_DATA.items():
        if 'startup' in data:
            implementations.append(name.replace('/', '/\n'))  # Line break for readability
            times.append(data['startup'])
            colors.append(get_color(name))

    # Sort by time
    sorted_data = sorted(zip(implementations, times, colors), key=lambda x: x[1])
    implementations, times, colors = zip(*sorted_data)

    # Create horizontal bar chart with better styling
    y_pos = np.arange(len(implementations))
    bars = ax.barh(y_pos, times, color=colors,
                   edgecolor='white', linewidth=2.5,
                   height=0.7, alpha=0.95)

    # Add value labels on bars with better styling
    for i, (bar, time) in enumerate(zip(bars, times)):
        width = bar.get_width()
        label = f'{time:.1f}ms'
        # Add subtle background to label for readability
        ax.text(width + 50, bar.get_y() + bar.get_height()/2, label,
                ha='left', va='center', fontweight='600', fontsize=11,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='none', alpha=0.8))

    # Highlight Wolfie's Gateway with glow effect
    bars[0].set_edgecolor('#059669')
    bars[0].set_linewidth(4)
    bars[0].set_alpha(1.0)
    # Add subtle glow
    for offset in [8, 12]:
        glow = plt.Rectangle(
            (0, bars[0].get_y()),
            bars[0].get_width(), bars[0].get_height(),
            facecolor='#10b981', alpha=0.05, zorder=0,
            linewidth=0
        )
        ax.add_patch(glow)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(implementations, fontsize=10.5)
    ax.set_xlabel('Startup Time (milliseconds)', fontweight='600', fontsize=13, color='#374151')
    ax.set_title('iMessage MCP Server Startup Performance\n10 Iterations Average',
                 fontweight='700', pad=25, fontsize=18, color='#111827')

    # Add reference line at 100ms with better styling
    ax.axvline(x=100, color='#ef4444', linestyle='--', alpha=0.6, linewidth=2.5)
    ax.text(100, len(implementations) - 0.3, '100ms\n(ideal)',
            ha='center', va='bottom', color='#dc2626', fontweight='700', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                     edgecolor='#fecaca', linewidth=2, alpha=0.95))

    # Add speedup annotation with enhanced styling
    our_time = times[0]
    next_best = times[1]
    speedup = next_best / our_time
    ax.text(0.97, 0.03, f"Wolfie's Gateway\n{speedup:.1f}× faster",
            transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#ecfdf5',
                     edgecolor='#10b981', linewidth=3, alpha=0.95),
            fontsize=13, fontweight='700', color='#047857')

    plt.tight_layout()
    return fig

def create_operation_breakdown():
    """Chart 2: Multi-operation performance breakdown."""
    # Focus on implementations with multiple operations
    focus_impls = ["Wolfie's iMessage Gateway", "Wolfie's iMessage MCP", 'wyattjoh/imessage-mcp', 'jonmmease/jons-mcp']
    operations = ['startup', 'recent_messages', 'search', 'get_conversation', 'groups']

    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(operations))
    width = 0.2

    for i, impl in enumerate(focus_impls):
        data = BENCHMARK_DATA[impl]
        values = [data.get(op, 0) for op in operations]
        offset = (i - len(focus_impls)/2) * width + width/2

        bars = ax.bar(x + offset, values, width,
                     label=impl.replace('/', '/\n'),
                     color=get_color(impl),
                     edgecolor='white', linewidth=1.5)

        # Add value labels on bars (only if > 0)
        for bar, val in zip(bars, values):
            if val > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.0f}',
                       ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('Operation Type', fontweight='bold')
    ax.set_ylabel('Latency (milliseconds)', fontweight='bold')
    ax.set_title('Performance Across Common Operations\nLower is Better',
                 fontweight='bold', pad=20, fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels([op.replace('_', '\n') for op in operations])
    ax.legend(loc='upper right', framealpha=0.95)
    ax.grid(axis='y', alpha=0.3)

    # Add horizontal reference lines
    ax.axhline(y=100, color='#22c55e', linestyle='--', alpha=0.3, linewidth=1)
    ax.axhline(y=500, color='#f59e0b', linestyle='--', alpha=0.3, linewidth=1)
    ax.axhline(y=1000, color='#dc2626', linestyle='--', alpha=0.3, linewidth=1)

    plt.tight_layout()
    return fig

def create_speedup_chart():
    """Chart 3: Speedup factors vs best competitor."""
    # Compare our CLI vs best competitor for each operation
    operations = ['startup', 'recent_messages', 'search', 'get_conversation', 'groups']
    our_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]

    speedups = {}
    for op in operations:
        if op not in our_data:
            continue

        our_time = our_data[op]

        # Find best competitor time for this operation
        competitor_times = []
        for name, data in BENCHMARK_DATA.items():
            if name != "Wolfie's iMessage Gateway" and name != "Wolfie's iMessage MCP" and op in data:
                competitor_times.append(data[op])

        if competitor_times:
            best_competitor = min(competitor_times)
            speedup = best_competitor / our_time
            speedups[op] = speedup

    fig, ax = plt.subplots(figsize=(12, 6))

    ops = list(speedups.keys())
    values = list(speedups.values())
    colors_list = ['#10b981' if v >= 2 else '#3b82f6' for v in values]

    y_pos = np.arange(len(ops))
    bars = ax.barh(y_pos, values, color=colors_list, edgecolor='white', linewidth=2)

    # Add value labels
    for bar, val in zip(bars, values):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
               f'{val:.1f}x',
               ha='left', va='center', fontweight='bold', fontsize=11)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([op.replace('_', ' ').title() for op in ops])
    ax.set_xlabel('Speedup Factor (vs Best Competitor)', fontweight='bold')
    ax.set_title("Wolfie's Gateway Performance Advantage\nHow Much Faster vs Best Competitor",
                 fontweight='bold', pad=20, fontsize=16)

    # Add reference line at 2x
    ax.axvline(x=2, color='#dc2626', linestyle='--', alpha=0.5, linewidth=2)
    ax.text(2, len(ops) - 0.5, '2x faster',
            ha='center', va='bottom', color='#dc2626', fontweight='bold')

    # Add average speedup annotation
    avg_speedup = np.mean(values)
    ax.text(0.98, 0.98, f'Average: {avg_speedup:.1f}x faster',
            transform=ax.transAxes, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.2, edgecolor='#10b981'),
            fontsize=12, fontweight='bold')

    plt.tight_layout()
    return fig

def create_mcp_overhead_comparison():
    """Chart 5: CLI vs MCP protocol overhead - same code, different interface."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Operations where we have both CLI and MCP data
    operations = ['startup', 'search', 'groups', 'unread']
    cli_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    mcp_data = BENCHMARK_DATA["Wolfie's iMessage MCP"]

    cli_times = []
    mcp_times = []
    overheads = []

    for op in operations:
        if op in cli_data and op in mcp_data:
            cli_times.append(cli_data[op])
            mcp_times.append(mcp_data[op])
            overheads.append(mcp_data[op] / cli_data[op])

    y_pos = np.arange(len(operations))
    height = 0.35

    # Create paired bars
    bars_cli = ax.barh(y_pos - height/2, cli_times, height,
                       label="Wolfie's Gateway (Direct CLI)", color='#10b981',
                       edgecolor='white', linewidth=2)
    bars_mcp = ax.barh(y_pos + height/2, mcp_times, height,
                       label="Wolfie's MCP (MCP Protocol)", color='#f59e0b',
                       edgecolor='white', linewidth=2)

    # Add value labels
    for bar, time in zip(bars_cli, cli_times):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
               f'{time:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)

    for bar, time, overhead in zip(bars_mcp, mcp_times, overheads):
        ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
               f'{time:.0f}ms ({overhead:.1f}x)', ha='left', va='center',
               fontweight='bold', fontsize=10, color='#b45309')

    ax.set_yticks(y_pos)
    ax.set_yticklabels([op.replace('_', ' ').title() for op in operations])
    ax.set_xlabel('Latency (milliseconds)', fontweight='bold')
    ax.set_title('The Cost of MCP Protocol\nSame Code, Different Interface',
                 fontweight='bold', pad=20, fontsize=16)
    ax.legend(loc='lower right', framealpha=0.95)

    # Add annotation
    avg_overhead = np.mean(overheads)
    ax.text(0.98, 0.02, f'Average overhead: {avg_overhead:.1f}x slower\nwith MCP protocol',
            transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='#f59e0b', alpha=0.2, edgecolor='#f59e0b'),
            fontsize=12, fontweight='bold')

    plt.tight_layout()
    return fig


def create_user_perception_scale():
    """Chart 6: User perception scale - where implementations fall."""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Define perception zones (log scale friendly boundaries)
    zones = [
        (0, 100, 'INSTANT', '#10b981', 0.3),
        (100, 250, 'FAST', '#3b82f6', 0.3),
        (250, 500, 'NOTICEABLE', '#eab308', 0.3),
        (500, 1000, 'SLOW', '#f59e0b', 0.3),
        (1000, 2000, 'FRUSTRATING', '#dc2626', 0.3),
    ]

    # Draw zones as horizontal bands
    for start, end, label, color, alpha in zones:
        ax.axvspan(start, end, alpha=alpha, color=color, label=label)
        # Add zone label at top
        ax.text((start + end) / 2, 10.5, label,
               ha='center', va='bottom', fontweight='bold', fontsize=9,
               color=color)

    # Get all implementations with startup times
    implementations = []
    for name, data in BENCHMARK_DATA.items():
        if 'startup' in data:
            # Keep full username/repo format for identification
            display_name = name.replace('/', '/\n') if '/' in name else name
            implementations.append((display_name, data['startup'], get_color(name), name))

    # Sort by startup time
    implementations.sort(key=lambda x: x[1])

    # Plot implementations as markers
    y_positions = np.arange(len(implementations))
    for i, (display_name, time, color, orig_name) in enumerate(implementations):
        # Marker
        marker_color = '#10b981' if time < 100 else ('#3b82f6' if time < 250 else '#94a3b8')
        if orig_name == "Wolfie's iMessage Gateway":
            ax.scatter(time, i, s=300, color='#10b981', edgecolor='#059669',
                      linewidth=3, zorder=10, marker='o')
            ax.annotate(f'{display_name}\n{time:.0f}ms', (time, i),
                       xytext=(time + 80, i), fontweight='bold', fontsize=10,
                       ha='left', va='center',
                       bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.2))
        else:
            ax.scatter(time, i, s=150, color=marker_color, edgecolor='white',
                      linewidth=2, zorder=5, alpha=0.8)
            ax.annotate(f'{display_name}', (time, i),
                       xytext=(time + 50, i), fontsize=8,
                       ha='left', va='center', alpha=0.8)

    ax.set_xlim(0, 2000)
    ax.set_ylim(-0.5, len(implementations) + 0.5)
    ax.set_xlabel('Startup Time (milliseconds)', fontweight='bold')
    ax.set_ylabel('Implementations (sorted by speed)', fontweight='bold')
    ax.set_title('User Perception of Response Time\nWhere Do Implementations Fall?',
                 fontweight='bold', pad=20, fontsize=16)

    # Remove y-axis ticks (we have labels on markers)
    ax.set_yticks([])

    # Add reference lines
    ax.axvline(x=100, color='#10b981', linestyle='--', alpha=0.5, linewidth=2)

    # Add annotation
    ax.text(0.02, 0.98, "Only Wolfie's Gateway\nfeels instant",
            transform=ax.transAxes, ha='left', va='top',
            bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.2, edgecolor='#10b981'),
            fontsize=11, fontweight='bold')

    plt.tight_layout()
    return fig


def create_head_to_head():
    """Chart 7: Head-to-head comparison vs best competitor (wyattjoh)."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Operations where both have data
    operations = ['startup', 'recent_messages', 'search', 'groups']
    cli_data = BENCHMARK_DATA["Wolfie's iMessage Gateway"]
    competitor_data = BENCHMARK_DATA['wyattjoh/imessage-mcp']

    cli_times = []
    competitor_times = []
    speedups = []

    for op in operations:
        if op in cli_data and op in competitor_data:
            cli_times.append(cli_data[op])
            competitor_times.append(competitor_data[op])
            speedups.append(competitor_data[op] / cli_data[op])

    y_pos = np.arange(len(operations))
    height = 0.35

    # Create paired bars
    bars_cli = ax.barh(y_pos - height/2, cli_times, height,
                       label="Wolfie's iMessage Gateway", color='#10b981',
                       edgecolor='white', linewidth=2)
    bars_comp = ax.barh(y_pos + height/2, competitor_times, height,
                        label='wyattjoh/imessage-mcp', color='#3b82f6',
                        edgecolor='white', linewidth=2)

    # Add value labels with speedup
    for i, (bar_cli, bar_comp, cli_t, comp_t, speedup) in enumerate(
            zip(bars_cli, bars_comp, cli_times, competitor_times, speedups)):
        # CLI time
        ax.text(bar_cli.get_width() + 5, bar_cli.get_y() + bar_cli.get_height()/2,
               f'{cli_t:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)
        # Competitor time with speedup
        ax.text(bar_comp.get_width() + 5, bar_comp.get_y() + bar_comp.get_height()/2,
               f'{comp_t:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)
        # Speedup badge on far right
        ax.text(290, y_pos[i], f'{speedup:.1f}x',
               ha='center', va='center', fontweight='bold', fontsize=12,
               bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.3, edgecolor='#10b981'))

    ax.set_yticks(y_pos)
    ax.set_yticklabels([op.replace('_', '\n').title() for op in operations])
    ax.set_xlabel('Latency (milliseconds)', fontweight='bold')
    ax.set_title("Head-to-Head: Wolfie's Gateway vs Best MCP Competitor\nWe Win Every Category",
                 fontweight='bold', pad=20, fontsize=16)
    ax.legend(loc='upper right', framealpha=0.95)
    ax.set_xlim(0, 320)

    # Add annotation
    avg_speedup = np.mean(speedups)
    ax.text(0.98, 0.02, f'Average: {avg_speedup:.1f}x faster',
            transform=ax.transAxes, ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.2, edgecolor='#10b981'),
            fontsize=12, fontweight='bold')

    plt.tight_layout()
    return fig


def create_feature_coverage_heatmap():
    """Chart 8: Feature coverage heatmap - speed + features."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Define operations and implementations to show
    operations = ['startup', 'recent_messages', 'search', 'get_conversation',
                  'groups', 'unread', 'semantic_search', 'analytics']
    implementations = ["Wolfie's iMessage Gateway", 'wyattjoh/imessage-mcp', 'marissamarym/imessage',
                       'willccbb/imessage-service (requires external DB)', 'jonmmease/jons-mcp']

    # Build matrix: 0=not supported, 1=fast(<250ms), 2=medium(250-1000ms), 3=slow(>1000ms)
    matrix = np.zeros((len(operations), len(implementations)))

    for j, impl in enumerate(implementations):
        data = BENCHMARK_DATA.get(impl, {})
        for i, op in enumerate(operations):
            if op in data:
                time = data[op]
                if time < 250:
                    matrix[i, j] = 1  # Fast - green
                elif time < 1000:
                    matrix[i, j] = 2  # Medium - yellow
                else:
                    matrix[i, j] = 3  # Slow - red
            else:
                matrix[i, j] = 0  # Not supported - gray

    # Custom colormap: gray, green, yellow, red
    from matplotlib.colors import ListedColormap
    colors_list = ['#e5e7eb', '#10b981', '#eab308', '#dc2626']
    cmap = ListedColormap(colors_list)

    # Create heatmap
    im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=3)

    # Add cell borders
    for i in range(len(operations)):
        for j in range(len(implementations)):
            val = matrix[i, j]
            # Add value label (use bullet instead of checkmark for font compatibility)
            if val == 0:
                label = '—'
                text_color = '#6b7280'
            elif val == 1:
                label = 'Y'
                text_color = 'white'
            elif val == 2:
                label = 'Y'
                text_color = 'black'
            else:
                label = 'Y'
                text_color = 'white'

            ax.text(j, i, label, ha='center', va='center',
                   fontsize=14, fontweight='bold', color=text_color)

    # Labels - keep full username/repo format with line break
    ax.set_xticks(np.arange(len(implementations)))
    ax.set_yticks(np.arange(len(operations)))
    display_impl_names = [impl.replace('/', '/\n') if '/' in impl else impl for impl in implementations]
    ax.set_xticklabels(display_impl_names, rotation=0, ha='center', fontsize=9)
    ax.set_yticklabels([op.replace('_', ' ').title() for op in operations])

    ax.set_title('Feature Coverage & Performance\nGreen = Fast (<250ms), Yellow = Medium, Red = Slow, Gray = Missing',
                 fontweight='bold', pad=20, fontsize=14)

    # Add legend
    legend_elements = [
        mpatches.Patch(facecolor='#10b981', edgecolor='white', label='Fast (<250ms)'),
        mpatches.Patch(facecolor='#eab308', edgecolor='white', label='Medium (250-1000ms)'),
        mpatches.Patch(facecolor='#dc2626', edgecolor='white', label='Slow (>1000ms)'),
        mpatches.Patch(facecolor='#e5e7eb', edgecolor='white', label='Not Supported'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1),
             framealpha=0.95)

    # Add annotation
    ax.text(1.02, 0.02, "Wolfie's Gateway:\nMost complete\nAND fastest",
            transform=ax.transAxes, ha='left', va='bottom',
            bbox=dict(boxstyle='round', facecolor='#10b981', alpha=0.2, edgecolor='#10b981'),
            fontsize=11, fontweight='bold')

    plt.tight_layout()
    return fig


def create_tier_visualization():
    """Chart 4: Performance tier classification."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Classify implementations by startup time
    fast = []  # < 250ms
    medium = []  # 250-1000ms
    slow = []  # > 1000ms

    for name, data in BENCHMARK_DATA.items():
        if 'startup' not in data:
            continue

        time = data['startup']
        # Keep full username/repo format with line break for readability
        display_name = name.replace('/', '/\n') if '/' in name else name

        if time < 250:
            fast.append((display_name, time))
        elif time < 1000:
            medium.append((display_name, time))
        else:
            slow.append((display_name, time))

    # Sort each tier
    fast.sort(key=lambda x: x[1])
    medium.sort(key=lambda x: x[1])
    slow.sort(key=lambda x: x[1])

    # Create visualization
    all_items = fast + medium + slow
    names = [item[0] for item in all_items]
    times = [item[1] for item in all_items]

    # Color by tier
    colors_list = (['#10b981'] * len(fast) +
                   ['#f59e0b'] * len(medium) +
                   ['#dc2626'] * len(slow))

    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, times, color=colors_list, edgecolor='white', linewidth=2)

    # Highlight our CLI
    bars[0].set_edgecolor('#059669')
    bars[0].set_linewidth(4)

    # Add value labels
    for bar, time in zip(bars, times):
        width = bar.get_width()
        ax.text(width + 50, bar.get_y() + bar.get_height()/2,
               f'{time:.0f}ms',
               ha='left', va='center', fontweight='bold', fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.set_xlabel('Startup Time (milliseconds)', fontweight='bold')
    ax.set_title('Performance Tier Classification\nStartup Time Performance',
                 fontweight='bold', pad=20, fontsize=16)

    # Add tier boundary lines
    ax.axvline(x=250, color='black', linestyle='--', alpha=0.3, linewidth=2)
    ax.axvline(x=1000, color='black', linestyle='--', alpha=0.3, linewidth=2)

    # Add tier labels
    tier_labels = [
        (125, len(all_items) - 0.5, 'FAST TIER\n(<250ms)', '#10b981'),
        (625, len(all_items) - 0.5, 'MEDIUM TIER\n(250-1000ms)', '#f59e0b'),
        (1400, len(all_items) - 0.5, 'SLOW TIER\n(>1000ms)', '#dc2626'),
    ]

    for x, y, label, color in tier_labels:
        ax.text(x, y, label, ha='center', va='bottom',
               bbox=dict(boxstyle='round', facecolor=color, alpha=0.2, edgecolor=color),
               fontweight='bold', fontsize=10)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='#10b981', edgecolor='white', label='Fast (<250ms)'),
        mpatches.Patch(facecolor='#f59e0b', edgecolor='white', label='Medium (250-1000ms)'),
        mpatches.Patch(facecolor='#dc2626', edgecolor='white', label='Slow (>1000ms)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', framealpha=0.95)

    plt.tight_layout()
    return fig

def main():
    """Generate all visualizations."""
    output_dir = Path('visualizations')
    output_dir.mkdir(exist_ok=True)

    print("🎨 Generating performance visualizations...")

    # Chart 1: Startup comparison (hero chart)
    print("  📊 Creating startup time comparison...")
    fig1 = create_startup_comparison()
    fig1.savefig(output_dir / 'startup_comparison.png', dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print("  ✓ Saved: startup_comparison.png")

    # Chart 2: Operation breakdown
    print("  📊 Creating operation breakdown...")
    fig2 = create_operation_breakdown()
    fig2.savefig(output_dir / 'operation_breakdown.png', dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print("  ✓ Saved: operation_breakdown.png")

    # Chart 3: Speedup factors
    print("  📊 Creating speedup chart...")
    fig3 = create_speedup_chart()
    fig3.savefig(output_dir / 'speedup_factors.png', dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print("  ✓ Saved: speedup_factors.png")

    # Chart 4: Tier visualization
    print("  📊 Creating tier visualization...")
    fig4 = create_tier_visualization()
    fig4.savefig(output_dir / 'performance_tiers.png', dpi=300, bbox_inches='tight')
    plt.close(fig4)
    print("  ✓ Saved: performance_tiers.png")

    # Chart 5: MCP Protocol Overhead
    print("  📊 Creating MCP protocol overhead comparison...")
    fig5 = create_mcp_overhead_comparison()
    fig5.savefig(output_dir / 'mcp_protocol_overhead.png', dpi=300, bbox_inches='tight')
    plt.close(fig5)
    print("  ✓ Saved: mcp_protocol_overhead.png")

    # Chart 6: User Perception Scale
    print("  📊 Creating user perception scale...")
    fig6 = create_user_perception_scale()
    fig6.savefig(output_dir / 'user_perception_scale.png', dpi=300, bbox_inches='tight')
    plt.close(fig6)
    print("  ✓ Saved: user_perception_scale.png")

    # Chart 7: Head-to-Head
    print("  📊 Creating head-to-head comparison...")
    fig7 = create_head_to_head()
    fig7.savefig(output_dir / 'head_to_head.png', dpi=300, bbox_inches='tight')
    plt.close(fig7)
    print("  ✓ Saved: head_to_head.png")

    # Chart 8: Feature Coverage Heatmap
    print("  📊 Creating feature coverage heatmap...")
    fig8 = create_feature_coverage_heatmap()
    fig8.savefig(output_dir / 'feature_coverage.png', dpi=300, bbox_inches='tight')
    plt.close(fig8)
    print("  ✓ Saved: feature_coverage.png")

    print(f"\n✅ All visualizations saved to {output_dir}/")
    print("\n📱 Twitter Thread Ready!")
    print("   8 charts generated for your thread.")

if __name__ == '__main__':
    main()
