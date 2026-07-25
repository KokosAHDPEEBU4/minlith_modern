"""Plotly rendering engine — interactive HTML charts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Catppuccin Mocha colors for Plotly
COLORS = [
    "#89b4fa", "#f38ba8", "#a6e3a1", "#fab387", "#cba6f7",
    "#f9e2af", "#94e2d5", "#74c7ec", "#eba0ac", "#b4befe",
]


def _get_layout_template() -> dict:
    """Return layout template matching current matplotlib theme."""
    from src.charts.engines.matplotlib_engine import get_bg_color, get_fg_color, get_grid_color

    bg = get_bg_color()
    fg = get_fg_color()
    grid = get_grid_color()

    return dict(
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font=dict(color=fg, size=12),
        xaxis=dict(gridcolor=grid, zerolinecolor=grid),
        yaxis=dict(gridcolor=grid, zerolinecolor=grid),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=fg)),
        margin=dict(l=50, r=30, t=50, b=50),
    )


def save_html(fig: go.Figure, path: str | Path, title: str = "") -> None:
    """Save Plotly figure as standalone HTML."""
    path = Path(path)
    fig.update_layout(**_get_layout_template())
    if title:
        from src.charts.engines.matplotlib_engine import get_fg_color
        fig.update_layout(title=dict(text=title, font=dict(size=16, color=get_fg_color())))
    fig.write_html(str(path), include_plotlyjs="cdn")
