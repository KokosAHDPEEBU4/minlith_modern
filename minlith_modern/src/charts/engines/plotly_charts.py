"""Interactive Plotly charts — bar, TAS, Harker, pie (HTML output).

Каждая диаграмма состоит из двух частей:

- ``fig_<type>`` — строит ``go.Figure`` (не записывает файл);
- ``interactive_<type>`` — обёртка: сохраняет фигуру в standalone HTML.

Такой паритет позволяет одному отчёту объединить несколько диаграмм
(см. ``plotly_engine.export_plotly_html`` с ``chart_types: list ``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.charts.base import ChartData
from src.charts.engines.plotly_engine import COLORS, save_html

DEFAULT_TITLES: dict[str, str] = {
    "bar": "Mineral Composition",
    "tas": "TAS Diagram",
    "harker": "Harker Diagrams",
    "pie": "Mineral Pie Charts",
    "qapf": "QAPF Diagram",
    "acnk": "A-CN-K Diagram",
    "afm": "AFM Diagram",
    "heatmap": "Mineral Heatmap",
    "correlation": "Correlation Matrix",
    "kf": "k1-k4 vs Sample",
    "boxplot": "Mineral Box Plot",
    "violin": "Mineral Violin Plot",
    "parallel": "Parallel Coordinates",
    "rock_type": "Rock Type Distribution",
}


def fig_bar(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive grouped bar chart of mineral weight %."""
    fig = go.Figure()
    for i, (mineral, vals) in enumerate(data.minerals_wt.items()):
        if len(vals) == 0:
            continue
        fig.add_trace(go.Bar(
            name=mineral, x=data.sample_names, y=vals,
            marker_color=COLORS[i % len(COLORS)],
            text=[f"{v:.1f}" for v in vals], textposition="outside",
        ))

    fig.update_layout(
        barmode="group",
        xaxis_title="Sample", yaxis_title="Mineral (wt%)",
        legend_title="Minerals",
    )
    return fig


def interactive_bar(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_bar(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["bar"]))


def fig_tas(data: ChartData, **kwargs) -> go.Figure | None:
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
    return fig


def interactive_tas(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_tas(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["tas"]))


def fig_harker(data: ChartData, **kwargs) -> go.Figure | None:
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
            text=data.sample_names, textfont=dict(size=9),
            hovertemplate=(
                f"{label}: %{{y:.2f}}<br>%{{text}}<extra></extra>"),
            showlegend=False,
        ), row=row, col=col)
        fig.update_xaxes(title_text="SiO₂", row=row, col=col, gridcolor="#313244")
        fig.update_yaxes(title_text=label, row=row, col=col, gridcolor="#313244")

    fig.update_layout(height=500, width=1000)
    return fig


def interactive_harker(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_harker(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["harker"]))


def fig_pie(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive pie charts for each sample."""
    all_minerals = list(data.minerals_wt.keys())
    n = len(data.sample_names)
    fig = make_subplots(rows=1, cols=max(n, 1), specs=[[{"type": "pie"}] * max(n, 1)],
                        subplot_titles=data.sample_names)

    for j, name in enumerate(data.sample_names):
        vals = []
        labels = []
        for m in all_minerals:
            v = data.minerals_wt[m][j] if j < len(data.minerals_wt[m]) else 0.0
            if v > 0.01:
                vals.append(v)
                labels.append(m)
        if not vals:
            vals = [1.0]
            labels = ["(no data)"]
        fig.add_trace(go.Pie(
            labels=labels, values=vals, hole=0.3,
            marker=dict(colors=COLORS[:len(vals)]),
            textinfo="label+percent", textfont_size=9,
        ), row=1, col=j + 1)

    fig.update_layout(height=400, width=300 * n)
    return fig


def interactive_pie(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_pie(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["pie"]))


def fig_qapf(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive QAPF ternary diagram."""
    q = data.minerals_wt.get("q", np.array([]))
    ab = data.minerals_wt.get("ab", np.array([]))
    an = data.minerals_wt.get("an", np.array([]))
    or_ = data.minerals_wt.get("or_", np.array([]))

    if len(q) == 0:
        return None

    total = q + ab + an + or_
    total[total == 0] = 1.0

    # QAP: Q at top, A=Ab+Or at bottom-left, P=An at bottom-right
    q_norm = q / total * 100
    a_norm = (ab + or_) / total * 100
    p_norm = an / total * 100

    fig = go.Figure()
    fig.add_trace(go.Scatterternary(
        a=q_norm, b=a_norm, c=p_norm,
        mode="markers+text",
        marker=dict(size=10, color=COLORS[0]),
        text=data.sample_names, textposition="top center", textfont=dict(size=9),
    ))

    fig.update_layout(
        ternary=dict(
            aaxis=dict(title="Q", min=0, linewidth=2, gridcolor="#313244"),
            baxis=dict(title="A (Ab+Or)", min=0, linewidth=2, gridcolor="#313244"),
            caxis=dict(title="P (An)", min=0, linewidth=2, gridcolor="#313244"),
        ),
        height=600, width=700,
    )
    return fig


def interactive_qapf(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_qapf(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["qapf"]))


def fig_acnk(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive A-CN-K ternary diagram."""
    al2o3 = data.oxides.get("al2o3", np.array([]))
    cao = data.oxides.get("cao", np.array([]))
    na2o = data.oxides.get("na2o", np.array([]))
    k2o = data.oxides.get("k2o", np.array([]))

    if len(al2o3) == 0:
        return None

    # Molecular proportions
    a = al2o3 / 101.96
    cn = cao / 56.08 + na2o / 61.98
    k = k2o / 94.20
    total = a + cn + k
    total[total == 0] = 1.0

    fig = go.Figure()
    fig.add_trace(go.Scatterternary(
        a=a / total * 100, b=cn / total * 100, c=k / total * 100,
        mode="markers+text",
        marker=dict(size=10, color=COLORS[2]),
        text=data.sample_names, textposition="top center", textfont=dict(size=9),
    ))

    fig.update_layout(
        ternary=dict(
            aaxis=dict(title="A (Al₂O₃)", min=0, gridcolor="#313244"),
            baxis=dict(title="CN (CaO+Na₂O)", min=0, gridcolor="#313244"),
            caxis=dict(title="K (K₂O)", min=0, gridcolor="#313244"),
        ),
        height=600, width=700,
    )
    return fig


def interactive_acnk(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_acnk(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["acnk"]))


def fig_afm(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive AFM ternary diagram."""
    feo = data.oxides.get("feo", np.array([]))
    fe2o3 = data.oxides.get("fe2o3", np.zeros(len(feo)))
    mgo = data.oxides.get("mgo", np.array([]))
    na2o = data.oxides.get("na2o", np.zeros(len(feo)))
    k2o = data.oxides.get("k2o", np.zeros(len(feo)))

    if len(feo) == 0:
        return None

    f = feo + 0.8998 * fe2o3
    m = mgo
    a = na2o + k2o
    total = f + m + a
    total[total == 0] = 1.0

    fig = go.Figure()
    fig.add_trace(go.Scatterternary(
        a=f / total * 100, b=m / total * 100, c=a / total * 100,
        mode="markers+text",
        marker=dict(size=10, color=COLORS[1]),
        text=data.sample_names, textposition="top center", textfont=dict(size=9),
    ))

    fig.update_layout(
        ternary=dict(
            aaxis=dict(title="F (FeOᵀ)", min=0, gridcolor="#313244"),
            baxis=dict(title="M (MgO)", min=0, gridcolor="#313244"),
            caxis=dict(title="A (Na₂O+K₂O)", min=0, gridcolor="#313244"),
        ),
        height=600, width=700,
    )
    return fig


def interactive_afm(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_afm(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["afm"]))


def fig_heatmap(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive mineral heatmap."""
    minerals = data.minerals_wt
    if not minerals:
        return None

    names = list(minerals.keys())
    n = len(data.sample_names)
    matrix = np.zeros((len(names), n))
    for i, m in enumerate(names):
        for j in range(n):
            matrix[i, j] = minerals[m][j] if j < len(minerals[m]) else 0.0

    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=data.sample_names, y=names,
        colorscale="YlOrRd", text=np.round(matrix, 1), texttemplate="%{text}",
    ))
    fig.update_layout(height=max(400, len(names) * 25), width=max(600, n * 80))
    return fig


def interactive_heatmap(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_heatmap(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["heatmap"]))


def fig_correlation(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive correlation heatmap."""
    from src.charts.built_in.correlation import CORR_FIELDS

    fields = [f[0] for f in CORR_FIELDS]
    labels = [f[1] for f in CORR_FIELDS]
    n = len(fields)
    n_samples = len(data.sample_names)

    matrix = np.full((n, n), np.nan)
    if n_samples >= 2:
        for i, fi in enumerate(fields):
            for j, fj in enumerate(fields):
                xi = data.oxides.get(fi, np.array([]))
                xj = data.oxides.get(fj, np.array([]))
                if len(xi) < 2 or len(xj) < 2:
                    continue
                if np.std(xi) == 0 or np.std(xj) == 0:
                    continue
                matrix[i, j] = np.corrcoef(xi, xj)[0, 1]

    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=labels, y=labels,
        colorscale="RdBu_r", zmin=-1, zmax=1,
        text=np.round(matrix, 2), texttemplate="%{text}",
    ))
    fig.update_layout(height=600, width=700)
    return fig


def interactive_correlation(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_correlation(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["correlation"]))


def fig_kf(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive k1-k4 vs F line chart."""
    k_values = data.metadata.get("k_values", None)
    f_values = data.F_values

    if k_values is None or not f_values:
        return None

    fig = go.Figure()
    for i, key in enumerate(["k1", "k2", "k3", "k4"]):
        vals = k_values.get(key, [])
        if vals:
            fig.add_trace(go.Scatter(
                x=list(range(len(vals))), y=vals, mode="lines+markers",
                name=key.upper(), line=dict(color=COLORS[i % len(COLORS)], width=2),
                marker=dict(size=6),
            ))

    fig.update_layout(
        xaxis_title="Sample Index", yaxis_title="Coefficient Value",
        legend_title="Coefficients",
    )
    return fig


def interactive_kf(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_kf(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["kf"]))


def fig_boxplot(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive box plot of mineral distribution."""
    minerals = data.minerals_wt
    if not minerals:
        return None

    fig = go.Figure()
    for i, (name, vals) in enumerate(minerals.items()):
        fig.add_trace(go.Box(
            y=vals, name=name, marker_color=COLORS[i % len(COLORS)],
            boxpoints="outliers",
        ))

    fig.update_layout(yaxis_title="wt%", showlegend=False)
    return fig


def interactive_boxplot(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_boxplot(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["boxplot"]))


def fig_violin(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive violin plot of mineral distribution."""
    minerals = data.minerals_wt
    if not minerals:
        return None

    fig = go.Figure()
    for i, (name, vals) in enumerate(minerals.items()):
        fig.add_trace(go.Violin(
            y=vals, name=name, marker_color=COLORS[i % len(COLORS)],
            box_visible=True, meanline_visible=True,
        ))

    fig.update_layout(yaxis_title="wt%", showlegend=False)
    return fig


def interactive_violin(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_violin(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["violin"]))


def fig_parallel(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive parallel coordinates of minerals."""
    minerals = data.minerals_wt
    if not minerals:
        return None

    names = list(minerals.keys())
    n_samples = len(data.sample_names)

    dims = []
    for m in names:
        vals = list(minerals[m])
        dims.append(dict(label=m, values=vals))

    fig = go.Figure(data=go.Parcoords(
        line=dict(color=list(range(n_samples)), colorscale="Viridis"),
        dimensions=dims,
    ))
    return fig


def interactive_parallel(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_parallel(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["parallel"]))


def fig_rock_type(data: ChartData, **kwargs) -> go.Figure | None:
    """Interactive rock type distribution pie."""
    rock_types = data.rock_types
    if not rock_types:
        return None

    type_names = {1: "Type I", 2: "Type II", 3: "Type III", 4: "Type IV", 5: "Type V"}
    counts = {}
    for rt in rock_types:
        label = type_names.get(rt, f"Type {rt}")
        counts[label] = counts.get(label, 0) + 1

    fig = go.Figure(data=go.Pie(
        labels=list(counts.keys()), values=list(counts.values()),
        hole=0.3, marker=dict(colors=COLORS[:len(counts)]),
        textinfo="label+percent",
    ))
    return fig


def interactive_rock_type(data: ChartData, path: Path, **kwargs) -> None:
    fig = fig_rock_type(data, **kwargs)
    if fig is None:
        return
    save_html(fig, path, title=kwargs.get("title", DEFAULT_TITLES["rock_type"]))


# Реестр обёрток «записать standalone HTML» (используется GUI/CLI).
PLOTLY_CHARTS: dict[str, Any] = {
    "bar": interactive_bar,
    "tas": interactive_tas,
    "harker": interactive_harker,
    "pie": interactive_pie,
    "qapf": interactive_qapf,
    "acnk": interactive_acnk,
    "afm": interactive_afm,
    "heatmap": interactive_heatmap,
    "correlation": interactive_correlation,
    "kf": interactive_kf,
    "boxplot": interactive_boxplot,
    "violin": interactive_violin,
    "parallel": interactive_parallel,
    "rock_type": interactive_rock_type,
}

# Реестр билдеров фигур (для объединённого отчёта).
PLOTLY_FIG_BUILDERS: dict[str, Any] = {
    "bar": fig_bar,
    "tas": fig_tas,
    "harker": fig_harker,
    "pie": fig_pie,
    "qapf": fig_qapf,
    "acnk": fig_acnk,
    "afm": fig_afm,
    "heatmap": fig_heatmap,
    "correlation": fig_correlation,
    "kf": fig_kf,
    "boxplot": fig_boxplot,
    "violin": fig_violin,
    "parallel": fig_parallel,
    "rock_type": fig_rock_type,
}