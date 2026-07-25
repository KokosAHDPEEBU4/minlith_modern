"""SiO₂ vs K₂O diagram — Peccerillo & Taylor (1976) rock series classification."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    create_figure, COLORS, ACCENT, get_fg_color, get_grid_color,
)


class SiO2K2OPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "sio2_k2o"

    def get_description(self) -> str:
        return "SiO₂–K₂O — Peccerillo & Taylor (1976)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(figsize=(8, 7),
                            title=kwargs.get("title", "SiO₂–K₂O (Peccerillo & Taylor, 1976)"))
        ax = fig.axes[0]

        sio2 = data.oxides.get("sio2", np.array([]))
        k2o = data.oxides.get("k2o", np.zeros(len(sio2)))

        ax.scatter(sio2, k2o, c=ACCENT, s=50, alpha=0.8,
                   edgecolors=fg, linewidth=0.5, zorder=5)

        # Boundary lines (simplified)
        x = np.linspace(45, 80, 100)
        ax.plot(x, 0.07 * (x - 45) + 0.5, "--", color=COLORS[3], linewidth=1.2, label="Tholeiitic / Calc-Alkaline")
        ax.plot(x, 0.07 * (x - 45) + 1.5, "--", color=COLORS[2], linewidth=1.2, label="Calc-Alkaline / High-K")
        ax.plot(x, 0.07 * (x - 45) + 3.0, "--", color=COLORS[4], linewidth=1.2, label="High-K / Shoshonite")

        ax.text(50, 0.3, "Tholeiitic", fontsize=9, alpha=0.5, fontstyle="italic", color=fg)
        ax.text(55, 1.8, "Calc-Alkaline", fontsize=9, alpha=0.5, fontstyle="italic", color=fg)
        ax.text(60, 3.5, "High-K", fontsize=9, alpha=0.5, fontstyle="italic", color=fg)
        ax.text(65, 5.5, "Shoshonite", fontsize=9, alpha=0.5, fontstyle="italic", color=fg)

        ax.set_xlabel("SiO₂ (wt%)")
        ax.set_ylabel("K₂O (wt%)")
        ax.legend(loc="upper left", fontsize=9, framealpha=0.3, labelcolor=fg)
        ax.set_xlim(45, 80)
        ax.set_ylim(0, max(k2o) * 1.3 if len(k2o) and max(k2o) > 0 else 7)
        ax.grid(True, color=grid, alpha=0.3)
        fig.tight_layout()
        return fig
