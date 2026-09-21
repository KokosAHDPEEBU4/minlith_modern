"""Box plot — mineral distribution across all samples."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)


class BoxPlotChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Box Plot"

    def get_description(self) -> str:
        return "Распределение минералов по всей выборке (медиана, квартили, выбросы)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        names = list(minerals.keys())
        n = len(names)

        fig = create_figure(
            figsize=(max(8, n * 0.8), 6),
            title=kwargs.get("title", "Mineral Distribution (wt%)"),
        )
        ax = fig.axes[0]

        box_data = [np.array(minerals[m], dtype=float) for m in names]
        colors = [COLORS[i % len(COLORS)] for i in range(n)]

        bp = ax.boxplot(box_data, patch_artist=True, widths=0.6,
                        medianprops=dict(color=fg, linewidth=1.5),
                        whiskerprops=dict(color=fg, linewidth=0.8),
                        capprops=dict(color=fg, linewidth=0.8),
                        flierprops=dict(marker="o", markerfacecolor=COLORS[1],
                                        markersize=4, alpha=0.6))

        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
            patch.set_edgecolor(fg)

        ax.set_xticks(range(1, n + 1))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("wt%")
        ax.grid(axis="y", color=grid, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
