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


# ── Color palettes ──

# Plot colors (same for both themes)
COLORS = [
    "#89b4fa", "#f38ba8", "#a6e3a1", "#fab387", "#cba6f7",
    "#f9e2af", "#94e2d5", "#74c7ec", "#eba0ac", "#b4befe",
    "#89dceb", "#f5c2e7", "#f2cdcd", "#585b70", "#cdd6f4",
    "#45475a", "#313244", "#1e1e2e",
]

# Dark theme (Catppuccin Mocha)
DARK_BG = "#1e1e2e"
DARK_FG = "#cdd6f4"
DARK_GRID = "#313244"
DARK_ACCENT = "#89b4fa"

# Light theme
LIGHT_BG = "#ffffff"
LIGHT_FG = "#1e1e2e"
LIGHT_GRID = "#e0e0e0"
LIGHT_ACCENT = "#2563eb"

# Active theme (default: dark)
BG_COLOR = DARK_BG
FG_COLOR = DARK_FG
GRID_COLOR = DARK_GRID
ACCENT = DARK_ACCENT


def set_chart_theme(theme: str) -> None:
    """Switch between 'dark' and 'light' chart themes."""
    global BG_COLOR, FG_COLOR, GRID_COLOR, ACCENT
    if theme == "light":
        BG_COLOR = LIGHT_BG
        FG_COLOR = LIGHT_FG
        GRID_COLOR = LIGHT_GRID
        ACCENT = LIGHT_ACCENT
    else:
        BG_COLOR = DARK_BG
        FG_COLOR = DARK_FG
        GRID_COLOR = DARK_GRID
        ACCENT = DARK_ACCENT


def get_chart_theme() -> str:
    """Return current theme name."""
    return "light" if BG_COLOR == LIGHT_BG else "dark"


def create_figure(
    figsize: tuple[int, int] = (8, 6),
    title: str = "",
    theme: str | None = None,
) -> Figure:
    """Create a styled matplotlib figure."""
    bg = DARK_BG if theme == "dark" else LIGHT_BG if theme == "light" else BG_COLOR
    fg = DARK_FG if theme == "dark" else LIGHT_FG if theme == "light" else FG_COLOR

    fig, ax = plt.subplots(figsize=figsize, facecolor=bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg)
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)
    if title:
        ax.set_title(title, color=fg, fontsize=14, fontweight="bold", pad=12)
    return fig


def create_triangle(title: str = "", theme: str | None = None) -> Figure:
    """Create a figure for ternary (triangle) diagrams."""
    bg = DARK_BG if theme == "dark" else LIGHT_BG if theme == "light" else BG_COLOR
    fg = DARK_FG if theme == "dark" else LIGHT_FG if theme == "light" else FG_COLOR

    fig = plt.figure(figsize=(8, 7), facecolor=bg)
    if title:
        fig.suptitle(title, color=fg, fontsize=14, fontweight="bold", y=0.96)
    return fig
