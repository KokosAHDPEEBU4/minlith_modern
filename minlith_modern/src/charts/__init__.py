"""Charts package — plugin system for data visualization."""

from typing import Any

from src.charts.base import ChartData, ChartPlugin

__all__ = ["ChartData", "ChartPlugin", "BUILTIN_CHARTS"]


def __getattr__(name: str) -> Any:
    # BUILTIN_CHARTS ленивый: импорт пакета не должен тянуть matplotlib
    # (расчётный путь использует только charts.built_in.parameters).
    if name == "BUILTIN_CHARTS":
        from src.charts.built_in import BUILTIN_CHARTS

        return BUILTIN_CHARTS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
