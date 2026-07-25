"""Correlation matrix — heatmap of oxide pairwise correlations."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import BG_COLOR, FG_COLOR

CORR_FIELDS = [
    ("sio2", "SiO₂"), ("al2o3", "Al₂O₃"), ("fe2o3", "Fe₂O₃"), ("feo", "FeO"),
    ("mgo", "MgO"), ("cao", "CaO"), ("na2o", "Na₂O"), ("k2o", "K₂O"),
    ("p2o5", "P₂O₅"), ("mno", "MnO"),
]


class CorrelationPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "correlation"

    def get_description(self) -> str:
        return "Pearson correlation heatmap of oxides"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        import matplotlib.pyplot as plt

        fields = [f[0] for f in CORR_FIELDS]
        labels = [f[1] for f in CORR_FIELDS]
        n = len(fields)
        n_samples = len(data.sample_names)

        matrix = np.full((n, n), np.nan)
        if n_samples < 2:
            # Not enough samples for correlation
            fig, ax = plt.subplots(figsize=(9, 8), facecolor=BG_COLOR)
            ax.set_facecolor(BG_COLOR)
            ax.text(0.5, 0.5, f"Need ≥2 samples for correlation (have {n_samples})",
                    ha="center", va="center", fontsize=12, transform=ax.transAxes, color=FG_COLOR)
            return fig

        for i, fi in enumerate(fields):
            for j, fj in enumerate(fields):
                xi = data.oxides.get(fi, np.array([]))
                xj = data.oxides.get(fj, np.array([]))
                if len(xi) < 2 or len(xj) < 2:
                    continue
                if np.std(xi) == 0 or np.std(xj) == 0:
                    continue
                matrix[i, j] = np.corrcoef(xi, xj)[0, 1]

        fig, ax = plt.subplots(figsize=(9, 8), facecolor=BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9, color=FG_COLOR)
        ax.set_yticklabels(labels, fontsize=9, color=FG_COLOR)

        for i in range(n):
            for j in range(n):
                val = matrix[i, j]
                if np.isnan(val):
                    ax.text(j, i, "—", ha="center", va="center", fontsize=8, color=FG_COLOR)
                else:
                    color = "white" if abs(val) > 0.6 else "black"
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color=color)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.ax.yaxis.label.set_color(FG_COLOR)
        cbar.ax.tick_params(colors=FG_COLOR)
        cbar.set_label("Pearson r", color=FG_COLOR)

        ax.set_title("Correlation Matrix", fontsize=12, fontweight="bold", color=FG_COLOR, pad=12)
        fig.tight_layout()
        return fig
