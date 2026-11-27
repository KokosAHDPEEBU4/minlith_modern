"""Built-in chart plugins (ленивая загрузка).

Плагины и реестр ``BUILTIN_CHARTS`` создаются при первом обращении (PEP 562):
расчётный путь импортирует из этого пакета только ``parameters``, и тянуть
из-за него все диаграммы с matplotlib дорого (~0.7 с на процесс). Порядок
``BUILTIN_CHARTS`` позиционный (индекс = type_id в GUI) — не менять.
"""

from __future__ import annotations

import importlib
from typing import Any

_PLUGINS: dict[str, str] = {
    "ACNKChart": "acnk",
    "BarChart": "bar_chart",
    "BoxPlotChart": "box_plot",
    "DefectChart": "defect_chart",
    "HeatmapChart": "heatmap",
    "PCABiplot": "pca_biplot",
    "PieChart": "pie_chart",
    "RockTypeChart": "rock_type_chart",
}

# Порядок позиционный (индекс = type_id в GUI) — не менять.
_BUILTIN_ORDER: tuple[str, ...] = (
    "BarChart",
    "PieChart",
    "DefectChart",
    "ACNKChart",
    "HeatmapChart",
    "RockTypeChart",
    "BoxPlotChart",
    "PCABiplot",
)


def __getattr__(name: str) -> Any:
    if name in _PLUGINS:
        module = importlib.import_module(f"{__name__}.{_PLUGINS[name]}")
        return getattr(module, name)
    if name == "BUILTIN_CHARTS":
        charts = []
        for cls_name in _BUILTIN_ORDER:
            module = importlib.import_module(f"{__name__}.{_PLUGINS[cls_name]}")
            charts.append(getattr(module, cls_name)())
        globals()["BUILTIN_CHARTS"] = charts  # кэшируем экземпляры
        return charts
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals(), *_PLUGINS, "BUILTIN_CHARTS"])
