"""Harker diagrams — SiO₂ vs major oxides (classic variation diagrams)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    COLORS,
    get_accent,
    get_bg_color,
    get_fg_color,
    get_grid_color,
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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()
        grid = get_grid_color()
        accent = get_accent()

        n_plots = len(OXIDES_TO_PLOT)
        cols = 3
        rows = (n_plots + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(12, rows * 3.4),
                                 facecolor=bg)
        if rows == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        sio2 = data.oxides.get("sio2", np.array([]))

        for i, (field, label) in enumerate(OXIDES_TO_PLOT):
            ax = axes[i]
            y = data.oxides.get(field, np.zeros(len(sio2)))
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=11)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)

            ax.scatter(sio2, y, c=accent, s=62, alpha=0.85,
                       edgecolors=fg, linewidth=0.8, zorder=5)

            # Trend line only when both axes vary; a constant FeO column used
            # to draw a meaningless horizontal "trend".
            r2: float | None = None
            if len(sio2) >= 2 and np.std(sio2) > 0 and np.std(y) > 0:
                coeffs = np.polyfit(sio2, y, 1)
                x_line = np.linspace(min(sio2), max(sio2), 100)
                ax.plot(x_line, np.polyval(coeffs, x_line), "--",
                        color=COLORS[2], alpha=0.7, linewidth=1.6)
                r2 = float(np.corrcoef(sio2, y)[0, 1] ** 2)

            ax.set_xlabel("SiO₂ (wt%)", fontsize=12)
            ax.set_ylabel(label, fontsize=12)
            title = f"{label}  ·  R² = {r2:.2f}" if r2 is not None else label
            ax.set_title(title, fontsize=13, fontweight="bold", color=fg)
            ax.grid(True, color=grid, alpha=0.35)

        for j in range(len(OXIDES_TO_PLOT), len(axes)):
            axes[j].set_visible(False)

        fig.suptitle("Harker Variation Diagrams", fontsize=16,
                      fontweight="bold", color=fg, y=1.02)
        fig.tight_layout(pad=1.2)
        return fig
