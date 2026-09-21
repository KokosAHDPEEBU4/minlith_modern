"""Dendrogram — hierarchical clustering of samples by mineral composition."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import create_figure, get_fg_color, get_grid_color


class DendrogramChart(ChartPlugin):
    def get_name(self) -> str:
        return "Dendrogram"

    def get_description(self) -> str:
        return "Иерархическая кластеризация образцов по минералам"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        from scipy.cluster.hierarchy import dendrogram, linkage

        fg = get_fg_color()
        grid = get_grid_color()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        names = list(minerals.keys())
        n_samples = len(data.sample_names)

        if n_samples < 2:
            fig = create_figure(title="Need ≥2 samples for clustering")
            return fig

        matrix = np.zeros((n_samples, len(names)))
        for j, m in enumerate(names):
            for i in range(n_samples):
                matrix[i, j] = minerals[m][i] if i < len(minerals[m]) else 0.0

        z = linkage(matrix, method="ward")

        fig = create_figure(
            figsize=(max(8, n_samples * 0.8), 6),
            title=kwargs.get("title", "Hierarchical Clustering (Ward)"),
        )
        ax = fig.axes[0]

        dendrogram(z, labels=data.sample_names, ax=ax,
                   leaf_rotation=45, leaf_font_size=9,
                   color_threshold=0, above_threshold_color=fg)

        ax.set_ylabel("Distance", color=fg)
        ax.grid(axis="y", color=grid, alpha=0.3)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
