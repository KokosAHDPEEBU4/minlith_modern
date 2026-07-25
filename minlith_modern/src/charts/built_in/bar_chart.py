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

        stacked = kwargs.get("stacked", False)
        normalized = kwargs.get("normalized", False)

        names = list(minerals.keys())
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        fig = create_figure(
            figsize=(max(8, n_samples * 2), 6),
            title=kwargs.get("title", "Mineral Composition (wt%)"),
        )
        ax = fig.axes[0]

        x = np.arange(n_samples)

        if stacked:
            bottom = np.zeros(n_samples)
            for i, mineral in enumerate(names):
                values = np.array(minerals[mineral], dtype=float)
                if normalized:
                    row_sums = np.array([sum(minerals[m][s] for m in minerals) for s in range(n_samples)])
                    row_sums[row_sums == 0] = 1
                    values = values / row_sums * 100
                color = COLORS[i % len(COLORS)]
                ax.bar(x, values, bottom=bottom, label=mineral, color=color, edgecolor="none", width=0.7)
                bottom += values
            if normalized:
                ax.set_ylabel("Normalized %")
            else:
                ax.set_ylabel("wt%")
        else:
            width = 0.8 / max(n_minerals, 1)
            for i, mineral in enumerate(names):
                values = np.array(minerals[mineral], dtype=float)
                if normalized:
                    row_sums = np.array([sum(minerals[m][s] for m in minerals) for s in range(n_samples)])
                    row_sums[row_sums == 0] = 1
                    values = values / row_sums * 100
                color = COLORS[i % len(COLORS)]
                offset = (i - n_minerals / 2 + 0.5) * width
                ax.bar(x + offset, values, width, label=mineral, color=color, edgecolor="none")
            if normalized:
                ax.set_ylabel("Normalized %")
            else:
                ax.set_ylabel("wt%")

        ax.set_xticks(x)
        ax.set_xticklabels(data.sample_names, rotation=45, ha="right", fontsize=9)
        ax.legend(fontsize=8, loc="upper right", framealpha=0.3, labelcolor=FG_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
