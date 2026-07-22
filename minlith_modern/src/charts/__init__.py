"""Charts package — plugin system for data visualization."""

from src.charts.base import ChartData, ChartPlugin
from src.charts.built_in import BUILTIN_CHARTS

__all__ = ["ChartData", "ChartPlugin", "BUILTIN_CHARTS"]
