"""Matplotlib rendering engine — shared style settings."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib import font_manager

# Register Cyrillic-capable font if available
_CYRILLIC_FONTS = ["DejaVu Sans", "Arial", "Liberation Sans", "Segoe UI"]
for fname in _CYRILLIC_FONTS:
    try:
        font_manager.findfont(fname, fallback_to_default=False)
        matplotlib.rcParams["font.family"] = fname
        matplotlib.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue


# MINLITH color palette (Catppuccin-inspired)
COLORS = [
    "#89b4fa", "#f38ba8", "#a6e3a1", "#fab387", "#cba6f7",
    "#f9e2af", "#94e2d5", "#74c7ec", "#eba0ac", "#b4befe",
    "#89dceb", "#f5c2e7", "#f2cdcd", "#585b70", "#cdd6f4",
    "#45475a", "#313244", "#1e1e2e",
]

BG_COLOR = "#1e1e2e"
FG_COLOR = "#cdd6f4"
GRID_COLOR = "#313244"
ACCENT = "#89b4fa"


def create_figure(
    figsize: tuple[int, int] = (8, 6),
    title: str = "",
) -> Figure:
    """Create a styled matplotlib figure."""
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=FG_COLOR)
    ax.xaxis.label.set_color(FG_COLOR)
    ax.yaxis.label.set_color(FG_COLOR)
    if title:
        ax.set_title(title, color=FG_COLOR, fontsize=14, fontweight="bold", pad=12)
    return fig


def create_triangle(title: str = "") -> Figure:
    """Create a figure for ternary (triangle) diagrams."""
    fig = plt.figure(figsize=(8, 7), facecolor=BG_COLOR)
    if title:
        fig.suptitle(title, color=FG_COLOR, fontsize=14, fontweight="bold", y=0.96)
    return fig
