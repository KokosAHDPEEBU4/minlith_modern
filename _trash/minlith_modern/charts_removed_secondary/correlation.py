"""Correlation matrix — heatmap of oxide pairwise correlations."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import get_bg_color, get_fg_color

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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        import matplotlib.pyplot as plt

        bg = get_bg_color()
        fg = get_fg_color()

        n_samples = len(data.sample_names)
        if n_samples < 2:
            fig, ax = plt.subplots(figsize=(9, 8), facecolor=bg)
            ax.set_facecolor(bg)
            ax.text(0.5, 0.5, f"Need ≥2 samples for correlation (have {n_samples})",
                    ha="center", va="center", fontsize=12, transform=ax.transAxes, color=fg)
            return fig

        # Constant oxides (e.g. FeO = 0 in a fully oxidised dataset) carry no
        # correlation information and used to add a useless row of dashes.
        pairs = [
            (field, label) for field, label in CORR_FIELDS
            if len(data.oxides.get(field, np.array([]))) >= 2
            and float(np.std(data.oxides[field])) > 0
        ]
        if len(pairs) < 2:
            fig, ax = plt.subplots(figsize=(9, 8), facecolor=bg)
            ax.set_facecolor(bg)
            ax.text(0.5, 0.5,
                    "Need ≥2 non-constant oxides for correlation",
                    ha="center", va="center", fontsize=12,
                    transform=ax.transAxes, color=fg)
            return fig

        fields = [p[0] for p in pairs]
        labels = [p[1] for p in pairs]
        n = len(fields)
        matrix = np.zeros((n, n))
        for i, fi in enumerate(fields):
            for j, fj in enumerate(fields):
                matrix[i, j] = np.corrcoef(data.oxides[fi], data.oxides[fj])[0, 1]

        fig, ax = plt.subplots(figsize=(max(8, n * 0.9), max(7, n * 0.8)),
                               facecolor=bg)
        ax.set_facecolor(bg)
        im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9, color=fg)
        ax.set_yticklabels(labels, fontsize=9, color=fg)

        for i in range(n):
            for j in range(n):
                val = matrix[i, j]
                # RdBu_r is white in the centre and dark at ±1: pick the text
                # colour from the cell brightness, not from the theme.
                color = "white" if abs(val) > 0.55 else "#1e1e2e"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=8, color=color)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.ax.yaxis.label.set_color(fg)
        cbar.ax.tick_params(colors=fg)
        cbar.set_label("Pearson r", color=fg)

        ax.set_title("Correlation Matrix", fontsize=12, fontweight="bold",
                     color=fg, pad=12)
        fig.tight_layout()
        return fig
