"""Heatmap — mineral composition matrix (samples × minerals)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import BG_COLOR, FG_COLOR, GRID_COLOR, create_figure


class HeatmapChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Heatmap"

    def get_description(self) -> str:
        return "Тепловая карта минерального состава (образцы × минералы)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        names = list(minerals.keys())
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        # Build matrix
        matrix = np.zeros((n_samples, n_minerals))
        for j, mineral in enumerate(names):
            arr = minerals[mineral]
            matrix[: len(arr), j] = arr[:n_samples]

        fig = create_figure(
            figsize=(max(8, n_minerals * 0.6), max(4, n_samples * 0.4)),
            title=kwargs.get("title", "Mineral Composition Heatmap"),
        )
        ax = fig.axes[0]

        # Custom colormap
        import matplotlib.colors as mcolors
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "minlith", ["#1e1e2e", "#313244", "#45475a", "#89b4fa", "#f38ba8"],
        )

        im = ax.imshow(matrix, cmap=cmap, aspect="auto", interpolation="nearest")

        ax.set_xticks(range(n_minerals))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9, color=FG_COLOR)
        ax.set_yticks(range(n_samples))
        ax.set_yticklabels(data.sample_names[:n_samples], fontsize=9, color=FG_COLOR)

        # Annotate cells
        for i in range(n_samples):
            for j in range(n_minerals):
                val = matrix[i, j]
                if val > 0.01:
                    text_color = BG_COLOR if val > matrix.max() * 0.5 else FG_COLOR
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                            fontsize=7, color=text_color)

        cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
        cbar.ax.tick_params(colors=FG_COLOR)
        cbar.set_label("wt%", color=FG_COLOR)

        fig.tight_layout()
        return fig
