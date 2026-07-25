"""Coefficient heatmap — k1-k4 across samples."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import get_bg_color, get_fg_color


class CoefficientHeatmap(ChartPlugin):
    def get_name(self) -> str:
        return "Coefficient Heatmap"

    def get_description(self) -> str:
        return "Тепловая карта коэффициентов k1-k4 по образцам"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        import matplotlib.pyplot as plt
        from src.charts.engines.matplotlib_engine import get_bg_color, get_fg_color

        bg = get_bg_color()
        fg = get_fg_color()

        k_values = data.metadata.get("k_values", None)
        if k_values is None:
            return self._empty_figure()

        coeffs = ["k1", "k2", "k3", "k4"]
        n_samples = len(data.sample_names)
        n_coeffs = len(coeffs)

        matrix = np.zeros((n_coeffs, n_samples))
        for i, k in enumerate(coeffs):
            vals = k_values.get(k, [])
            for j in range(min(len(vals), n_samples)):
                matrix[i, j] = vals[j]

        fig, ax = plt.subplots(figsize=(max(8, n_samples * 0.8), 3), facecolor=bg)
        ax.set_facecolor(bg)

        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")

        ax.set_xticks(range(n_samples))
        ax.set_xticklabels(data.sample_names, rotation=45, ha="right", fontsize=8, color=fg)
        ax.set_yticks(range(n_coeffs))
        ax.set_yticklabels(coeffs, fontsize=10, color=fg)

        for i in range(n_coeffs):
            for j in range(n_samples):
                val = matrix[i, j]
                color = "white" if val > matrix.max() * 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7, color=color)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.ax.tick_params(colors=fg)
        cbar.set_label("Value", color=fg)

        ax.set_title("Adaptive Coefficients (k1-k4)", fontsize=12, fontweight="bold", color=fg, pad=12)
        fig.tight_layout()
        return fig

    def _empty_figure(self):
        from src.charts.engines.matplotlib_engine import create_figure
        return create_figure(title="No coefficient data (metadata['k_values'])")
