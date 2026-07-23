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

LAYOUT_TEMPLATE = dict(
    paper_bgcolor="#1e1e2e",
    plot_bgcolor="#1e1e2e",
    font=dict(color="#cdd6f4", size=12),
    xaxis=dict(gridcolor="#313244", zerolinecolor="#313244"),
    yaxis=dict(gridcolor="#313244", zerolinecolor="#313244"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#cdd6f4")),
    margin=dict(l=50, r=30, t=50, b=50),
)


def save_html(fig: go.Figure, path: str | Path, title: str = "") -> None:
    """Save Plotly figure as standalone HTML."""
    path = Path(path)
    fig.update_layout(**LAYOUT_TEMPLATE)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=16, color="#cdd6f4")))
    fig.write_html(str(path), include_plotlyjs="cdn")
