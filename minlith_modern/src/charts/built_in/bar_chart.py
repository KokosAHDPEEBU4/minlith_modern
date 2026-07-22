"""Bar chart — mineral weight percent per sample."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, BG_COLOR, FG_COLOR, GRID_COLOR, create_figure


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

    def render(self, data: ChartData, **kwargs) -> Any:
        minerals = data.minerals_wt
        if not minerals:
            fig = create_figure(title="No mineral data")
            return fig

        names = list(minerals.keys())
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        fig = create_figure(
            figsize=(max(8, n_samples * 2), 6),
            title=kwargs.get("title", "Mineral Composition (wt%)"),
        )
        ax = fig.axes[0]

        x = np.arange(n_samples)
        width = 0.8 / max(n_minerals, 1)

        for i, mineral in enumerate(names):
            values = minerals[mineral]
            color = COLORS[i % len(COLORS)]
            offset = (i - n_minerals / 2 + 0.5) * width
            ax.bar(x + offset, values, width, label=mineral, color=color, edgecolor="none")

        ax.set_xticks(x)
        ax.set_xticklabels(data.sample_names, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("wt%")
        ax.legend(fontsize=8, loc="upper right", framealpha=0.3, labelcolor=FG_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
