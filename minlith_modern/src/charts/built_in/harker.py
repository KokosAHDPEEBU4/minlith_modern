"""Harker diagrams — SiO₂ vs major oxides (classic variation diagrams)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    create_figure, COLORS, BG_COLOR, FG_COLOR, GRID_COLOR, ACCENT,
)

OXIDES_TO_PLOT = [
    ("tio2", "TiO₂"),
    ("al2o3", "Al₂O₃"),
    ("fe2o3", "Fe₂O₃"),
    ("feo", "FeO"),
    ("mgo", "MgO"),
    ("cao", "CaO"),
    ("na2o", "Na₂O"),
    ("k2o", "K₂O"),
    ("p2o5", "P₂O₅"),
    ("mno", "MnO"),
]


class HarkerPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "harker"

    def get_description(self) -> str:
        return "Harker variation diagrams (SiO₂ vs оксиды)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        n_plots = len(OXIDES_TO_PLOT)
        cols = 3
        rows = (n_plots + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(14, rows * 3.5),
                                 facecolor=BG_COLOR)
        if rows == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        sio2 = data.oxides.get("sio2", np.array([]))
        labels = data.sample_names

        for i, (field, label) in enumerate(OXIDES_TO_PLOT):
            ax = axes[i]
            y = data.oxides.get(field, np.zeros(len(sio2)))
            ax.set_facecolor(BG_COLOR)
            ax.tick_params(colors=FG_COLOR, labelsize=8)
            ax.xaxis.label.set_color(FG_COLOR)
            ax.yaxis.label.set_color(FG_COLOR)

            ax.scatter(sio2, y, c=ACCENT, s=40, alpha=0.8,
                       edgecolors=FG_COLOR, linewidth=0.5, zorder=5)

            # Trend line
            if len(sio2) >= 2:
                coeffs = np.polyfit(sio2, y, 1)
                x_line = np.linspace(min(sio2), max(sio2), 100)
                ax.plot(x_line, np.polyval(coeffs, x_line), "--",
                        color=COLORS[2], alpha=0.5, linewidth=1)

            ax.set_xlabel("SiO₂ (wt%)", fontsize=9)
            ax.set_ylabel(label, fontsize=9)
            ax.set_title(label, fontsize=10, fontweight="bold", color=FG_COLOR)
            ax.grid(True, color=GRID_COLOR, alpha=0.3)

        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        fig.suptitle("Harker Variation Diagrams", fontsize=14,
                      fontweight="bold", color=FG_COLOR, y=1.01)
        fig.tight_layout()
        return fig
