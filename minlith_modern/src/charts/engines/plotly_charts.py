"""Interactive Plotly charts — bar, TAS, Harker, pie (HTML output)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.charts.base import ChartData
from src.charts.engines.plotly_engine import COLORS, save_html


def interactive_bar(data: ChartData, path: Path, **kwargs) -> None:
    """Interactive grouped bar chart of mineral weight %."""
    minerals = ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb"]
    labels = ["Ab", "An", "Or", "Q", "Ill", "Chl", "Kn", "Mm", "Gb"]

    fig = go.Figure()
    for i, (mineral, label) in enumerate(zip(minerals, labels)):
        vals = data.minerals_wt.get(mineral, np.array([]))
        if len(vals) == 0:
            continue
        fig.add_trace(go.Bar(
            name=label, x=data.sample_names, y=vals,
            marker_color=COLORS[i % len(COLORS)],
            text=[f"{v:.1f}" for v in vals], textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        xaxis_title="Sample", yaxis_title="Mineral (wt%)",
        legend_title="Minerals",
    )
    save_html(fig, path, title=kwargs.get("title", "Mineral Composition"))


def interactive_tas(data: ChartData, path: Path, **kwargs) -> None:
    """Interactive TAS diagram."""
    sio2 = data.oxides.get("sio2", np.array([]))
    na2o = data.oxides.get("na2o", np.zeros(len(sio2)))
    k2o = data.oxides.get("k2o", np.zeros(len(sio2)))
    total_alk = na2o + k2o

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sio2, y=total_alk, mode="markers+text",
        marker=dict(size=10, color=COLORS[0], line=dict(width=1, color="#cdd6f4")),
        text=data.sample_names, textposition="top center", textfont=dict(size=9),
        hovertemplate="SiO₂: %{x:.1f}%<br>Na₂O+K₂O: %{y:.1f}%<br>%{text}<extra></extra>",
    ))

    fig.update_layout(
        xaxis_title="SiO₂ (wt%)", yaxis_title="Na₂O + K₂O (wt%)",
        xaxis_range=[35, 80], yaxis_range=[0, 16],
    )
    save_html(fig, path, title=kwargs.get("title", "TAS Diagram"))


def interactive_harker(data: ChartData, path: Path, **kwargs) -> None:
    """Interactive Harker subplots."""
    oxides = [
        ("tio2", "TiO₂"), ("al2o3", "Al₂O₃"), ("fe2o3", "Fe₂O₃"),
        ("feo", "FeO"), ("mgo", "MgO"), ("cao", "CaO"),
        ("na2o", "Na₂O"), ("k2o", "K₂O"),
    ]
    sio2 = data.oxides.get("sio2", np.array([]))

    fig = make_subplots(rows=2, cols=4, subplot_titles=[o[1] for o in oxides])
    for i, (field, label) in enumerate(oxides):
        row = i // 4 + 1
        col = i % 4 + 1
        y = data.oxides.get(field, np.zeros(len(sio2)))
        fig.add_trace(go.Scatter(
            x=sio2, y=y, mode="markers",
            marker=dict(size=7, color=COLORS[i % len(COLORS)]),
            text=data.sample_names, hovertemplate=f"{label}: %{{y:.2f}}<br>%{{text}}<extra></extra>",
            showlegend=False,
        ), row=row, col=col)
        fig.update_xaxes(title_text="SiO₂", row=row, col=col, gridcolor="#313244")
        fig.update_yaxes(title_text=label, row=row, col=col, gridcolor="#313244")

    fig.update_layout(height=500, width=1000)
    save_html(fig, path, title=kwargs.get("title", "Harker Diagrams"))


def interactive_pie(data: ChartData, path: Path, **kwargs) -> None:
    """Interactive pie charts for each sample."""
    minerals = ["ab", "an", "or_", "q", "ill", "chl", "kn"]
    labels = ["Ab", "An", "Or", "Q", "Ill", "Chl", "Kn"]

    n = len(data.sample_names)
    fig = make_subplots(rows=1, cols=max(n, 1), specs=[[{"type": "pie"}] * max(n, 1)],
                        subplot_titles=data.sample_names)

    for j, name in enumerate(data.sample_names):
        vals = [data.minerals_wt.get(m, np.array([0.0]))[j] if j < len(data.minerals_wt.get(m, [])) else 0
                for m in minerals]
        fig.add_trace(go.Pie(
            labels=labels, values=vals, hole=0.3,
            marker=dict(colors=COLORS[:len(minerals)]),
            textinfo="label+percent", textfont_size=9,
        ), row=1, col=j + 1)

    fig.update_layout(height=400, width=300 * n)
    save_html(fig, path, title=kwargs.get("title", "Mineral Pie Charts"))


# Registry
PLOTLY_CHARTS = {
    "bar": interactive_bar,
    "tas": interactive_tas,
    "harker": interactive_harker,
    "pie": interactive_pie,
}
