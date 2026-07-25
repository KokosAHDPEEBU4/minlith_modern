"""Defect accumulation — stacked bar of oxide residuals per sample."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, create_figure, get_fg_color, get_grid_color


class DefectAccumulation(ChartPlugin):
    def get_name(self) -> str:
        return "Defect Accumulation"

    def get_description(self) -> str:
        return "Стековый bar: дефект по оксидам накопительно"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        defect = data.defect
        if not defect:
            return create_figure(title="No defect data")

        n_samples = len(data.sample_names)
        oxides = list(defect.keys())

        fig = create_figure(
            figsize=(max(8, n_samples * 1.5), 6),
            title=kwargs.get("title", "Defect Accumulation by Oxide"),
        )
        ax = fig.axes[0]

        x = np.arange(n_samples)
        bottom = np.zeros(n_samples)

        for i, oxide in enumerate(oxides):
            values = np.array(defect[oxide], dtype=float)
            color = COLORS[i % len(COLORS)]
            ax.bar(x, values, bottom=bottom, label=oxide, color=color, edgecolor="none", width=0.7)
            bottom += values

        ax.set_xticks(x)
        ax.set_xticklabels(data.sample_names, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("Cumulative Δ")
        ax.axhline(y=0, color=fg, linewidth=0.5, alpha=0.5)
        ax.legend(fontsize=7, loc="upper right", framealpha=0.3, labelcolor=fg, ncol=2)
        ax.grid(axis="y", color=grid, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
