"""AFM diagram — Irvine & Baragar (1971) tholeiitic vs calc-alkaline."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)


class AFMPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "afm"

    def get_description(self) -> str:
        return "AFM — Irvine & Baragar (1971)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(
            figsize=(8, 7),
            title=kwargs.get("title", "AFM Diagram (Irvine & Baragar, 1971)"),
        )
        ax = fig.axes[0]

        a_vals, fm_vals = [], []
        for i, name in enumerate(data.sample_names):
            feot = data.oxides.get("feo", np.zeros(len(data.sample_names)))[i]
            fe2o3 = data.oxides.get("fe2o3", np.zeros(len(data.sample_names)))[i]
            feot += 0.8998 * fe2o3
            alk = data.oxides.get("na2o", np.zeros(len(data.sample_names)))[i] + \
                  data.oxides.get("k2o", np.zeros(len(data.sample_names)))[i]
            mg = data.oxides.get("mgo", np.zeros(len(data.sample_names)))[i]
            total = feot + alk + mg
            if total == 0:
                continue
            a_vals.append(alk / total * 100)
            fm_vals.append((feot + mg) / total * 100)

        if not a_vals:
            return fig

        ax.scatter(a_vals, fm_vals, c=ACCENT, s=50, alpha=0.8,
                   edgecolors=fg, linewidth=0.5, zorder=5)

        # Irvine & Baragar (1971) boundary line
        x_boundary = np.linspace(0, 90, 100)
        y_boundary = 100 - x_boundary - 20 * np.exp(-0.05 * x_boundary)
        ax.plot(x_boundary, y_boundary, "--", color=COLORS[2], linewidth=1.5,
                label="Irvine & Baragar (1971)")

        ax.text(10, 70, "Tholeiitic", fontsize=11, fontweight="bold", alpha=0.4,
                fontstyle="italic", color=fg)
        ax.text(40, 20, "Calc-Alkaline", fontsize=11, fontweight="bold", alpha=0.4,
                fontstyle="italic", color=fg)

        ax.set_xlabel("A = Na₂O + K₂O")
        ax.set_ylabel("F + M = FeOᵀ + MgO")
        ax.legend(loc="upper right", fontsize=9, framealpha=0.3, labelcolor=fg)
        ax.set_xlim(0, max(a_vals) * 1.2 if a_vals else 100)
        ax.set_ylim(0, 100)
        ax.grid(True, color=grid, alpha=0.3)
        fig.tight_layout()
        return fig
