"""Interactive Plotly charts — bar, pie, A-CN-K, heatmap, correlations.

Sedimentary-rock set: igneous TAS/QAPF/Harker/AFM/SiO2-K2O charts were
removed with their matplotlib counterparts.

Каждая диаграмма состоит из двух частей:

- ``fig_<type>`` — строит ``go.Figure`` (не записывает файл);
- ``interactive_<type>`` — обёртка: сохраняет фигуру в standalone HTML.

Такой паритет позволяет одному отчёту объединить несколько диаграмм
(см. ``plotly_engine.export_plotly_html`` с ``chart_types: list``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.charts.base import ChartData
from src.charts.classification import ACNK_MINERALS, ACNK_WEATHERING
from src.charts.data_builder import (
    mineral_label,
    mineral_series,
    visible_mineral_fields,
)
from src.charts.engines.plotly_engine import COLORS, save_html

DEFAULT_TITLES: dict[str, str] = {
    "bar": "Mineral Composition",
    "pie": "Mineral Pie Charts",
    "acnk": "A-CN-K Diagram",
    "heatmap": "Mineral Heatmap",
    "boxplot": "Mineral Box Plot",
    "rock_type": "Rock Type Distribution",
}


def fig_bar(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive grouped bar chart of mineral weight %."""
    fields = visible_mineral_fields(data)
    n = len(data.sample_names)
    if not fields or n == 0:
        return None

    fig = go.Figure()
    for i, field in enumerate(fields):
        vals = mineral_series(data, field, n)
        fig.add_trace(go.Bar(
            name=mineral_label(field), x=data.sample_names, y=vals,
            marker_color=COLORS[i % len(COLORS)],
            text=[f"{v:.1f}" for v in vals], textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        xaxis_title="Sample", yaxis_title="Mineral (wt%)",
        legend_title="Minerals",
    )
    return fig


def interactive_bar(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_bar(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["bar"]))


def fig_pie(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive pie charts for each sample."""
    fields = visible_mineral_fields(data)
    n = len(data.sample_names)
    if not fields or n == 0:
        return None

    fig = make_subplots(rows=1, cols=n, specs=[[{"type": "pie"}] * n],
                        subplot_titles=data.sample_names)

    for j, _name in enumerate(data.sample_names):
        vals = []
        labels = []
        for field in fields:
            arr = data.minerals_wt[field]
            v = float(arr[j]) if j < len(arr) else 0.0
            if v > 0.01:
                vals.append(v)
                labels.append(mineral_label(field))
        if not vals:
            vals = [1.0]
            labels = ["(no data)"]
        fig.add_trace(go.Pie(
            labels=labels, values=vals, hole=0.3,
            marker=dict(colors=[COLORS[i % len(COLORS)] for i in range(len(vals))]),
            textinfo="label+percent", textfont_size=9,
        ), row=1, col=j + 1)

    fig.update_layout(height=400, width=300 * n)
    return fig


def interactive_pie(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_pie(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["pie"]))


def fig_acnk(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive A-CN-K ternary diagram."""
    from src.charts.built_in.acnk import acnk_components

    if len(data.oxides.get("al2o3", np.array([]))) == 0:
        return None

    a_vals = []
    cn_vals = []
    k_vals = []
    names = []
    for i, name in enumerate(data.sample_names):
        a, cn, k = acnk_components(data.oxides, i)
        total = a + cn + k
        if total <= 0:
            continue
        a_vals.append(a / total * 100)
        cn_vals.append(cn / total * 100)
        k_vals.append(k / total * 100)
        names.append(name)

    fig = go.Figure()
    fig.add_trace(go.Scatterternary(
        a=a_vals, b=cn_vals, c=k_vals,
        mode="markers+text",
        marker=dict(size=10, color=COLORS[2]),
        text=names, textposition="top center", textfont=dict(size=9),
        name="Samples",
    ))

    # Ideal mineral endmembers and the weathering direction.
    min_a, min_cn, min_k, min_labels = [], [], [], []
    for label, a, cn, k in ACNK_MINERALS:
        total = a + cn + k
        if total <= 0:
            continue
        min_a.append(a / total * 100)
        min_cn.append(cn / total * 100)
        min_k.append(k / total * 100)
        min_labels.append(label)
    fig.add_trace(go.Scatterternary(
        a=min_a, b=min_cn, c=min_k, mode="markers+text",
        marker=dict(size=8, symbol="square", color=COLORS[4]),
        text=min_labels, textposition="top center", textfont=dict(size=8),
        name="Минералы-ориентиры",
    ))
    (a0, cn0, k0), (a1, cn1, k1) = ACNK_WEATHERING
    t0, t1 = a0 + cn0 + k0, a1 + cn1 + k1
    fig.add_trace(go.Scatterternary(
        a=[a0 / t0 * 100, a1 / t1 * 100],
        b=[cn0 / t0 * 100, cn1 / t1 * 100],
        c=[k0 / t0 * 100, k1 / t1 * 100],
        mode="lines", line=dict(color=COLORS[4], width=1.2, dash="dash"),
        name="Выветривание", hoverinfo="skip",
    ))

    fig.update_layout(
        ternary=dict(
            sum=100,
            aaxis=dict(title="A (Al₂O₃)", min=0, gridcolor="#313244"),
            baxis=dict(title="CN (CaO*+Na₂O)", min=0, gridcolor="#313244"),
            caxis=dict(title="K (K₂O)", min=0, gridcolor="#313244"),
        ),
        height=600, width=700,
    )
    return fig


def interactive_acnk(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_acnk(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["acnk"]))


def fig_heatmap(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive mineral heatmap."""
    fields = visible_mineral_fields(data)
    n = len(data.sample_names)
    if not fields or n == 0:
        return None

    names = [mineral_label(field) for field in fields]
    matrix = np.vstack([mineral_series(data, field, n) for field in fields])

    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=data.sample_names, y=names,
        colorscale="YlOrRd", text=np.round(matrix, 1), texttemplate="%{text}",
    ))
    fig.update_layout(height=max(400, len(names) * 25), width=max(600, n * 80))
    return fig


def interactive_heatmap(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_heatmap(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["heatmap"]))


def fig_boxplot(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive box plot of mineral distribution."""
    fields = visible_mineral_fields(data)
    n = len(data.sample_names)
    if not fields or n == 0:
        return None

    fig = go.Figure()
    for i, field in enumerate(fields):
        fig.add_trace(go.Box(
            y=mineral_series(data, field, n), name=mineral_label(field),
            marker_color=COLORS[i % len(COLORS)], boxpoints="outliers",
        ))

    fig.update_layout(yaxis_title="wt%", showlegend=False)
    return fig


def interactive_boxplot(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_boxplot(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["boxplot"]))


def fig_rock_type(data: ChartData, **kwargs: Any) -> go.Figure | None:
    """Interactive rock type distribution pie."""
    rock_types = data.rock_types
    if not rock_types:
        return None

    type_names = {1: "Тип 1", 2: "Тип 2", 3: "Тип 3", 4: "Тип 4", 5: "Тип 5"}
    counts: dict[str, int] = {}
    for rt in rock_types:
        label = type_names.get(rt, f"Type {rt}")
        counts[label] = counts.get(label, 0) + 1

    fig = go.Figure(data=go.Pie(
        labels=list(counts.keys()), values=list(counts.values()),
        hole=0.3, marker=dict(colors=COLORS[:len(counts)]),
        textinfo="label+percent",
    ))
    return fig


def interactive_rock_type(data: ChartData, path: Path, **kwargs: Any) -> None:
    fig = fig_rock_type(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["rock_type"]))


# Реестр обёрток «записать standalone HTML» (используется GUI/CLI).
PLOTLY_CHARTS: dict[str, Any] = {
    "bar": interactive_bar,
    "pie": interactive_pie,
    "acnk": interactive_acnk,
    "heatmap": interactive_heatmap,
    "boxplot": interactive_boxplot,
    "rock_type": interactive_rock_type,
}

# Реестр билдеров фигур (для объединённого отчёта).
PLOTLY_FIG_BUILDERS: dict[str, Any] = {
    "bar": fig_bar,
    "pie": fig_pie,
    "acnk": fig_acnk,
    "heatmap": fig_heatmap,
    "boxplot": fig_boxplot,
    "rock_type": fig_rock_type,
}
