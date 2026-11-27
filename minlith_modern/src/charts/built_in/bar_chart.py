"""Bar chart — mineral weight percent per sample."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.data_builder import (
    mineral_label,
    mineral_series,
    visible_mineral_fields,
)
from src.charts.engines.matplotlib_engine import (
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)


class BarChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Bar Chart"

    def get_description(self) -> str:
        return "Столбчатая диаграмма минерального состава (вес.%)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fields = visible_mineral_fields(data)
        n_samples = len(data.sample_names)
        if not fields or n_samples == 0:
            return create_figure(title="No mineral data")

        stacked = kwargs.get("stacked", False)
        normalized = kwargs.get("normalized", False)

        values = {field: mineral_series(data, field, n_samples) for field in fields}
        row_sums = np.sum(np.vstack(list(values.values())), axis=0)
        row_sums[row_sums == 0] = 1.0

        fig = create_figure(
            figsize=(max(8, n_samples * 2), 6),
            title=kwargs.get("title", "Mineral Composition (wt%)"),
        )
        ax = fig.axes[0]

        x = np.arange(n_samples)
        width = 0.8 / max(len(fields), 1)

        if stacked:
            bottom = np.zeros(n_samples)
            for i, field in enumerate(fields):
                series = values[field]
                if normalized:
                    series = series / row_sums * 100
                ax.bar(x, series, bottom=bottom, label=mineral_label(field),
                       color=COLORS[i % len(COLORS)], edgecolor="none", width=0.7)
                bottom += series
        else:
            for i, field in enumerate(fields):
                series = values[field]
                if normalized:
                    series = series / row_sums * 100
                offset = (i - len(fields) / 2 + 0.5) * width
                ax.bar(x + offset, series, width, label=mineral_label(field),
                       color=COLORS[i % len(COLORS)], edgecolor="none")

        ax.set_ylabel("Normalized %" if normalized else "wt%")
        ax.set_xticks(x)
        ax.set_xticklabels(data.sample_names, rotation=45, ha="right", fontsize=9)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.3, labelcolor=fg)
        ax.grid(axis="y", color=grid, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
