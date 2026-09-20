"""Unified chart data + rendering for report generators.

Единая точка построения ``ChartData`` из результатов и рендера диаграммы в PNG
(base64). Используется HTML/Word/PDF генераторами и превью в GUI, чтобы исключить
расхождения между превью и экспортом.
"""

from __future__ import annotations

import base64
import io
import logging

from src.charts.data_builder import MINERAL_FIELDS, OXIDE_FIELDS, build_chart_data  # noqa: F401
from src.core.models import CalculationResult

logger = logging.getLogger(__name__)

# Ключ диаграммы в шаблоне отчёта -> имя плагина из BUILTIN_CHARTS.
CHART_ALIASES: dict[str, str] = {
    "bar": "Mineral Bar Chart",
    "pie": "Mineral Pie Chart",
    "defect": "Defect Chart",
    "boxplot": "Mineral Box Plot",
    "heatmap": "Mineral Heatmap",
    "correlation": "correlation",
    "harker": "harker",
    "qapf": "QAPF",
    "tas": "TAS",
    "acnk": "A-CN-K",
    "radar": "Mineral Radar",
    "kf": "Коэффициенты хлорита vs F",
    "rock_type": "Rock Type Distribution",
    "feldspar": "Feldspar Triangle",
    "sio2_k2o": "sio2_k2o",
    "afm": "afm",
    "coefficient_heatmap": "Coefficient Heatmap",
    "defect_accumulation": "Defect Accumulation",
    "pca_biplot": "PCA Biplot",
    "dendrogram": "Dendrogram",
    "parallel_coordinates": "Parallel Coordinates",
    "mg_fe_al": "Mg-Fe-Al Ternary",
    "bland_altman": "bland_altman",
}

# Типы, для которых рендер выполняется по одному образцу.
_SINGLE_SAMPLE_TYPES = ("pie", "defect", "radar", "kf")


def find_chart_plugin(chart_type: str):
    """Return the chart plugin by template key (or direct name), else None."""
    from src.charts.built_in import BUILTIN_CHARTS

    target = CHART_ALIASES.get(chart_type, chart_type)
    target_low = target.lower()
    for plugin in BUILTIN_CHARTS:
        if plugin.get_name().lower() == target_low:
            return plugin
    return None


def render_chart_png(
    chart_type: str,
    results: list[CalculationResult],
    sample_idx: int = 0,
    dpi: int = 150,
) -> bytes | None:
    """Render a chart to PNG bytes, or None on failure."""
    try:
        plugin = find_chart_plugin(chart_type)
        if plugin is None:
            logger.warning("Chart type %r not found in BUILTIN_CHARTS", chart_type)
            return None

        data = build_chart_data(results)
        kwargs: dict = {}
        if chart_type == "bar":
            kwargs = {"stacked": True, "normalized": True}
        if chart_type in _SINGLE_SAMPLE_TYPES:
            kwargs["sample_idx"] = sample_idx

        fig = plugin.render(data, **kwargs)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        import matplotlib.pyplot as plt
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Chart render failed (%s): %s", chart_type, exc)
        return None


def render_chart_base64(
    chart_type: str,
    results: list[CalculationResult],
    sample_idx: int = 0,
    dpi: int = 100,
) -> str | None:
    """Render a chart to a data-URI PNG for HTML embedding, or None."""
    png = render_chart_png(chart_type, results, sample_idx=sample_idx, dpi=dpi)
    if png is None:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
