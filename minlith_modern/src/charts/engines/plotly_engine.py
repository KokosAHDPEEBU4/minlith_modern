"""Plotly rendering engine — interactive HTML charts."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

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


PLOTLY_LABELS: dict[str, str] = {
    "bar": "Столбчатая (минералы)",
    "pie": "Круговая (минералы)",
    "tas": "TAS-диаграмма",
    "qapf": "QAPF",
    "acnk": "A-CN-K",
    "afm": "AFM",
    "harker": "Харкер (Harker)",
    "heatmap": "Тепловая карта минералов",
    "correlation": "Корреляция",
    "kf": "Коэффициенты хлорита vs F",
    "boxplot": "Ящики (box plot)",
    "violin": "Скрипки (violin)",
    "parallel": "Параллельные координаты",
    "rock_type": "Распределение типов пород",
}


def _write_combined_html(
    figs: list[go.Figure],
    path: Path,
    title: str,
    chart_names: list[str],
    data=None,
) -> None:
    """Write one standalone HTML report with several figures and a summary."""
    import html as html_mod
    from datetime import datetime

    from src.charts.data_builder import MINERAL_LABELS

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    minerals_used: list[str] = []
    sample_names: list[str] = []
    if data is not None:
        sample_names = list(data.sample_names)
        for fld, vals in data.minerals_wt.items():
            if len(vals) > 0 and max(float(v) for v in vals) > 0:
                minerals_used.append(MINERAL_LABELS.get(fld, fld))

    esc = html_mod.escape

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"ru\">")
    parts.append("<head>")
    parts.append("<meta charset=\"utf-8\">")
    parts.append(f"<title>{esc(title)}</title>")
    parts.append("""
<style>
  body { background:#1e1e2e; color:#cdd6f4; font-family:'Segoe UI', sans-serif;
         margin:0; padding:24px 32px; }
  h1 { color:#89b4fa; font-size:24px; margin:0; }
  h2 { color:#cba6f7; font-size:18px; margin:24px 0 4px; }
  .summary { background:#181825; border:1px solid #313244; border-radius:8px;
             padding:12px 18px; font-size:14px; line-height:1.7; margin:14px 0; }
  .summary b { color:#a6e3a1; }
  .chart { margin:0 0 8px; }
  hr { border:none; border-top:1px solid #313244; margin:6px 0 0; }
</style>""")
    parts.append("</head><body>")
    parts.append(f"<header><h1>{esc(title)}</h1></header>")
    parts.append("<div class=\"summary\">")
    parts.append(f"<div><b>Дата и время генерации:</b> {esc(ts)}</div>")
    parts.append(f"<div><b>Анализируемых образцов:</b> {len(sample_names)}</div>")
    if sample_names:
        parts.append("<div><b>Образцы:</b> " + esc(", ".join(sample_names)) + "</div>")
    minerals_text = ", ".join(minerals_used) if minerals_used else "—"
    parts.append(f"<div><b>Использованные минералы:</b> {esc(minerals_text)}</div>")
    parts.append("</div>")

    for i, (fig, name) in enumerate(zip(figs, chart_names)):
        fig.update_layout(**_get_layout_template())
        parts.append(f"<h2>{esc(name)}</h2>")
        embed = fig.to_html(
            full_html=False,
            include_plotlyjs="cdn" if i == 0 else False,
        )
        parts.append(f"<div class=\"chart\">{embed}</div>")
        parts.append("<hr>")

    parts.append("</body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")


def export_plotly_html(
    chart_type: str | list[str],
    results,
    path: str | Path,
    title: str = "",
) -> bool:
    """Render interactive Plotly HTML from calculation results.

    ``chart_type`` может быть как строкой (одна диаграмма), так и списком —
    тогда диаграммы объединяются в один HTML-отчёт со сводкой.

    Returns ``False`` when any ``chart_type`` is not in ``PLOTLY_CHARTS``.
    """
    from src.charts.data_builder import build_chart_data
    from src.charts.engines.plotly_charts import PLOTLY_CHARTS, PLOTLY_FIG_BUILDERS

    types = [chart_type] if isinstance(chart_type, str) else list(chart_type)
    if not types or any(t not in PLOTLY_CHARTS for t in types):
        return False

    data = build_chart_data(results)
    figs: list[go.Figure] = []
    names: list[str] = []
    for t in types:
        fig = PLOTLY_FIG_BUILDERS[t](data)
        if fig is None:
            continue
        figs.append(fig)
        names.append(PLOTLY_LABELS.get(t, t))
    if not figs:
        return False

    _write_combined_html(
        figs,
        Path(path),
        title=title or "Интерактивные диаграммы",
        chart_names=names,
        data=data,
    )
    return True
