#!/usr/bin/env python3
"""
Generate enhanced performance comparison visualizations for social sharing.
"""

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib import transforms

# Copy BENCHMARK_DATA and COLORS from visualize_benchmark.py
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
    "Wolfie's iMessage Gateway": '#10b981',  # Emerald - winner
    "Wolfie's iMessage MCP": '#f59e0b',  # Amber - baseline
    'wyattjoh/imessage-mcp': '#3b82f6',  # Blue - best competitor
    'default': '#94a3b8',  # Slate - others
}

# Enhanced styling configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.facecolor'] = '#ffffff'
plt.rcParams['axes.facecolor'] = '#ffffff'
plt.rcParams['axes.edgecolor'] = '#e1e4e8'
plt.rcParams['axes.linewidth'] = 1.5
plt.rcParams['grid.color'] = '#e1e4e8'
plt.rcParams['grid.alpha'] = 0.5
plt.rcParams['grid.linewidth'] = 0.8
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SF Pro Display', 'Segoe UI', 'Helvetica Neue', 'Arial']
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['axes.titleweight'] = 700
plt.rcParams['axes.titlecolor'] = '#111827'
plt.rcParams['axes.labelsize'] = 13
plt.rcParams['axes.labelweight'] = 600
plt.rcParams['axes.labelcolor'] = '#374151'
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['xtick.color'] = '#374151'
plt.rcParams['ytick.color'] = '#374151'

DPI = 300
FIGSIZE = (1200 / DPI, 800 / DPI)


def get_color(name):
    """Get color for implementation."""
    return COLORS.get(name, COLORS['default'])


def _mix(color, target, amount):
    base = np.array(to_rgb(color))
    target = np.array(to_rgb(target))
    return tuple(base * (1 - amount) + target * amount)


def lighten(color, amount=0.25):
    return _mix(color, '#ffffff', amount)


def darken(color, amount=0.15):
    return _mix(color, '#000000', amount)


def is_wolfie(name):
    return name.startswith("Wolfie's")


def add_bar_shadows(ax, bars, fig, offset_px=2, alpha=0.15):
    """Add subtle drop shadow to bars with pixel-based offset."""
    dx = offset_px / fig.dpi
    dy = -offset_px / fig.dpi
    shadow_transform = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    for bar in bars:
        shadow = plt.Rectangle(
            (bar.get_x(), bar.get_y()),
            bar.get_width(),
            bar.get_height(),
            transform=bar.get_transform() + shadow_transform,
            facecolor='black',
            edgecolor='none',
            alpha=alpha,
            zorder=bar.get_zorder() - 1,
        )
        ax.add_patch(shadow)


def apply_vertical_gradient(ax, bar, base_color):
    """Apply a light-to-dark vertical gradient within a bar."""
    x0, y0 = bar.get_x(), bar.get_y()
    x1, y1 = x0 + bar.get_width(), y0 + bar.get_height()
    top = lighten(base_color, 0.25)
    bottom = darken(base_color, 0.15)
    gradient = np.linspace(0, 1, 256).reshape(-1, 1)
    rgba = np.zeros((256, 1, 4))
    top_rgba = np.array((*top, 1.0))
    bottom_rgba = np.array((*bottom, 1.0))
    rgba[:, 0, :] = top_rgba * (1 - gradient) + bottom_rgba * gradient
    ax.imshow(
        rgba,
        extent=(x0, x1, y0, y1),
        origin='lower',
        aspect='auto',
        zorder=bar.get_zorder() + 1,
        clip_path=bar,
        clip_on=True,
    )


def annotation_box(color):
    """Shared annotation box styling."""
    return dict(
        boxstyle='round,pad=0.45',
        facecolor='white',
        edgecolor=color,
        linewidth=1.5,
        alpha=0.95,
    )


def style_axes(ax):
    ax.grid(axis='x', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)


def create_startup_comparison():
    """Enhanced horizontal bar chart of startup times."""
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

    implementations = []
    names = []
    times = []
    colors = []

    for name, data in BENCHMARK_DATA.items():
        if 'startup' in data:
            implementations.append(name.replace('/', '/\n'))
            names.append(name)
            times.append(data['startup'])
            colors.append(get_color(name))

    sorted_data = sorted(zip(implementations, names, times, colors), key=lambda x: x[2])
    implementations, names, times, colors = zip(*sorted_data)

    y_pos = np.arange(len(implementations))
    bars = ax.barh(
        y_pos,
        times,
        color=colors,
        edgecolor='white',
        linewidth=2.0,
        height=0.7,
        alpha=0.98,
    )

    add_bar_shadows(ax, bars, fig)

    for bar, name, time in zip(bars, names, times):
        if is_wolfie(name):
            apply_vertical_gradient(ax, bar, get_color(name))
        ax.text(
            bar.get_width() + 45,
            bar.get_y() + bar.get_height() / 2,
            f'{time:.1f}ms',
            ha='left',
            va='center',
            fontsize=11,
            fontweight=600,
            color='#111827',
            bbox=annotation_box(get_color(name)),
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(implementations)
    ax.set_xlabel('Startup Time (milliseconds)')
    ax.set_title('iMessage MCP Server Startup Performance\n10 Iterations Average')
    style_axes(ax)

    ax.axvline(x=100, color='#ef4444', linestyle='--', alpha=0.6, linewidth=2)
    ax.text(
        100,
        len(implementations) - 0.35,
        '100ms\n(ideal)',
        ha='center',
        va='bottom',
        fontsize=10,
        fontweight=600,
        color='#b91c1c',
        bbox=annotation_box('#ef4444'),
    )

    max_time = max(times)
    ax.set_xlim(0, max_time * 1.35)

    plt.tight_layout()
    return fig


def create_mcp_overhead_comparison():
    """Enhanced grouped bars - CLI vs MCP."""
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

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

    bars_cli = ax.barh(
        y_pos - height / 2,
        cli_times,
        height,
        label="Wolfie's Gateway (Direct CLI)",
        color=get_color("Wolfie's iMessage Gateway"),
        edgecolor='white',
        linewidth=2,
    )
    bars_mcp = ax.barh(
        y_pos + height / 2,
        mcp_times,
        height,
        label="Wolfie's MCP (MCP Protocol)",
        color=get_color("Wolfie's iMessage MCP"),
        edgecolor='white',
        linewidth=2,
    )

    add_bar_shadows(ax, list(bars_cli) + list(bars_mcp), fig)
    for bar in bars_cli:
        apply_vertical_gradient(ax, bar, get_color("Wolfie's iMessage Gateway"))
    for bar in bars_mcp:
        apply_vertical_gradient(ax, bar, get_color("Wolfie's iMessage MCP"))

    for bar, time in zip(bars_cli, cli_times):
        ax.text(
            bar.get_width() + 25,
            bar.get_y() + bar.get_height() / 2,
            f'{time:.0f}ms',
            ha='left',
            va='center',
            fontsize=10,
            fontweight=600,
            color='#111827',
            bbox=annotation_box(get_color("Wolfie's iMessage Gateway")),
        )

    for bar, time, overhead in zip(bars_mcp, mcp_times, overheads):
        ax.text(
            bar.get_width() + 25,
            bar.get_y() + bar.get_height() / 2,
            f'{time:.0f}ms ({overhead:.1f}x)',
            ha='left',
            va='center',
            fontsize=10,
            fontweight=600,
            color='#92400e',
            bbox=annotation_box(get_color("Wolfie's iMessage MCP")),
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels([op.replace('_', ' ').title() for op in operations])
    ax.set_xlabel('Latency (milliseconds)')
    ax.set_title('The Cost of MCP Protocol\nSame Code, Different Interface')
    ax.legend(loc='lower right', framealpha=0.95)
    style_axes(ax)

    avg_overhead = np.mean(overheads)
    ax.text(
        0.98,
        0.02,
        f'Average overhead: {avg_overhead:.1f}x slower\nwith MCP protocol',
        transform=ax.transAxes,
        ha='right',
        va='bottom',
        fontsize=11,
        fontweight=600,
        color='#92400e',
        bbox=annotation_box(get_color("Wolfie's iMessage MCP")),
    )

    max_time = max(mcp_times + cli_times)
    ax.set_xlim(0, max_time * 1.3)

    plt.tight_layout()
    return fig


def create_head_to_head():
    """Enhanced paired comparison - Gateway vs wyattjoh."""
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

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

    bars_cli = ax.barh(
        y_pos - height / 2,
        cli_times,
        height,
        label="Wolfie's iMessage Gateway",
        color=get_color("Wolfie's iMessage Gateway"),
        edgecolor='white',
        linewidth=2,
    )
    bars_comp = ax.barh(
        y_pos + height / 2,
        competitor_times,
        height,
        label='wyattjoh/imessage-mcp',
        color=get_color('wyattjoh/imessage-mcp'),
        edgecolor='white',
        linewidth=2,
    )

    add_bar_shadows(ax, list(bars_cli) + list(bars_comp), fig)
    for bar in bars_cli:
        apply_vertical_gradient(ax, bar, get_color("Wolfie's iMessage Gateway"))

    for idx, (bar_cli, bar_comp, cli_t, comp_t, speedup) in enumerate(
        zip(bars_cli, bars_comp, cli_times, competitor_times, speedups)
    ):
        ax.text(
            bar_cli.get_width() + 15,
            bar_cli.get_y() + bar_cli.get_height() / 2,
            f'{cli_t:.0f}ms',
            ha='left',
            va='center',
            fontsize=10,
            fontweight=600,
            color='#111827',
            bbox=annotation_box(get_color("Wolfie's iMessage Gateway")),
        )
        ax.text(
            bar_comp.get_width() + 15,
            bar_comp.get_y() + bar_comp.get_height() / 2,
            f'{comp_t:.0f}ms',
            ha='left',
            va='center',
            fontsize=10,
            fontweight=600,
            color='#1e40af',
            bbox=annotation_box(get_color('wyattjoh/imessage-mcp')),
        )
        ax.text(
            max(cli_times + competitor_times) * 1.05,
            y_pos[idx],
            f'{speedup:.1f}x',
            ha='center',
            va='center',
            fontsize=11,
            fontweight=700,
            color='#047857',
            bbox=annotation_box(get_color("Wolfie's iMessage Gateway")),
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels([op.replace('_', '\n').title() for op in operations])
    ax.set_xlabel('Latency (milliseconds)')
    ax.set_title("Head-to-Head: Wolfie's Gateway vs Best MCP Competitor\nWe Win Every Category")
    ax.legend(loc='upper right', framealpha=0.95)
    style_axes(ax)

    avg_speedup = np.mean(speedups)
    ax.text(
        0.98,
        0.02,
        f'Average: {avg_speedup:.1f}x faster',
        transform=ax.transAxes,
        ha='right',
        va='bottom',
        fontsize=11,
        fontweight=600,
        color='#047857',
        bbox=annotation_box(get_color("Wolfie's iMessage Gateway")),
    )

    max_time = max(cli_times + competitor_times)
    ax.set_xlim(0, max_time * 1.35)

    plt.tight_layout()
    return fig


if __name__ == '__main__':
    OUTPUT_DIR = Path('visualizations/enhanced')
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    fig1 = create_startup_comparison()
    fig1.savefig(OUTPUT_DIR / 'startup_comparison.png', dpi=DPI)
    plt.close(fig1)

    fig2 = create_mcp_overhead_comparison()
    fig2.savefig(OUTPUT_DIR / 'mcp_protocol_overhead.png', dpi=DPI)
    plt.close(fig2)

    fig3 = create_head_to_head()
    fig3.savefig(OUTPUT_DIR / 'head_to_head.png', dpi=DPI)
    plt.close(fig3)
