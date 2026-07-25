"""Parallel coordinates — each mineral is an axis, each sample is a line."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, create_figure, get_fg_color, get_grid_color


class ParallelCoordinates(ChartPlugin):
    def get_name(self) -> str:
        return "Parallel Coordinates"

    def get_description(self) -> str:
        return "Параллельные оси: каждый минерал — ось, каждый образец — линия"

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
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        fig = create_figure(
            figsize=(max(10, n_minerals * 1.2), 6),
            title=kwargs.get("title", "Parallel Coordinates — Minerals"),
        )
        ax = fig.axes[0]

        for i in range(n_samples):
            values = [float(minerals[m][i]) if i < len(minerals[m]) else 0.0 for m in names]
            color = COLORS[i % len(COLORS)]
            ax.plot(range(n_minerals), values, color=color, linewidth=1.5, alpha=0.7,
                    label=data.sample_names[i] if n_samples <= 20 else None)

        ax.set_xticks(range(n_minerals))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("wt%")
        ax.grid(axis="y", color=grid, alpha=0.3)
        ax.set_axisbelow(True)

        if n_samples <= 20:
            ax.legend(fontsize=7, loc="upper right", framealpha=0.3, labelcolor=fg)

        fig.tight_layout()
        return fig
