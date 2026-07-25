"""TAS — Total Alkali-Silica diagram (Le Maitre et al., 2005)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, ACCENT, create_figure, get_fg_color, get_grid_color


# Simplified TAS field boundaries (SiO2 vs Na2O+K2O)
# Each field: (name, [(si_min, alk_max), ...])
_TAS_FIELDS = [
    ("Picrobasalt", [(35, 0), (45, 0), (45, 1.5), (41, 1.5)]),
    ("Basalt", [(45, 0), (52, 0), (52, 3.5), (45, 3.5)]),
    ("Basaltic Andesite", [(52, 0), (57, 0), (57, 5.5), (52, 5.5)]),
    ("Andesite", [(57, 0), (63, 0), (63, 7), (57, 7)]),
    ("Dacite", [(63, 0), (70, 0), (70, 7), (63, 7)]),
    ("Rhyolite", [(70, 0), (80, 0), (80, 10), (70, 10)]),
    ("Trachybasalt", [(45, 3.5), (52, 3.5), (52, 5), (45, 5)]),
    ("Basaltic Trachyandesite", [(52, 5), (57, 7), (57, 9), (52, 9)]),
    ("Trachyandesite", [(57, 7), (63, 9), (63, 11), (57, 11)]),
    ("Trachyte / Trachydacite", [(63, 9), (70, 10), (70, 12), (63, 12)]),
    ("Phonolite", [(57, 11), (63, 12), (63, 16), (57, 16)]),
    ("Tephrite / Basanite", [(41, 1.5), (45, 5), (45, 7), (41, 7)]),
    ("Foidite", [(35, 0), (41, 7), (41, 14), (35, 14)]),
]

# Alkali-subalkali dividing line (Irvine & Baragar, 1971)
_ALKALI_LINE_X = np.array([35, 40, 45, 50, 55, 60, 65, 70, 75, 80])
_ALKALI_LINE_Y = np.array([0.5, 1.5, 3.0, 4.5, 6.0, 7.5, 8.8, 9.5, 9.8, 10.0])


class TASChart(ChartPlugin):
    def get_name(self) -> str:
        return "TAS"

    def get_description(self) -> str:
        return "TAS — Total Alkali-Silica (классификация вулканитов)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(figsize=(10, 7), title=kwargs.get("title", "TAS — Total Alkali-Silica"))
        ax = fig.axes[0]

        # Draw field boundaries (simplified)
        for name, pts in _TAS_FIELDS:
            xs = [p[0] for p in pts] + [pts[0][0]]
            ys = [p[1] for p in pts] + [pts[0][1]]
            ax.plot(xs, ys, color=fg, linewidth=0.3, alpha=0.25)

        # Alkali-subalkali line
        ax.plot(_ALKALI_LINE_X, _ALKALI_LINE_Y, "--", color="#f38ba8", linewidth=1.0, alpha=0.6, label="Alkali / Subalkali")

        # Plot samples
        sio2 = data.oxides.get("sio2", np.array([]))
        na2o = data.oxides.get("na2o", np.zeros(len(sio2)))
        k2o = data.oxides.get("k2o", np.zeros(len(sio2)))
        total_alk = na2o + k2o

        for i, name in enumerate(data.sample_names):
            if i < len(sio2):
                color = ACCENT if len(data.sample_names) == 1 else COLORS[i % len(COLORS)]
                ax.plot(sio2[i], total_alk[i], "o", color=color, markersize=8,
                        markeredgecolor=fg, markeredgewidth=0.5)
                ax.annotate(name, (sio2[i], total_alk[i]), textcoords="offset points",
                            xytext=(5, 5), fontsize=8, color=fg, alpha=0.8)

        ax.set_xlabel("SiO₂ (wt%)")
        ax.set_ylabel("Na₂O + K₂O (wt%)")
        ax.set_xlim(35, 80)
        ax.set_ylim(0, 16)
        ax.grid(True, color=grid, alpha=0.3)
        ax.legend(fontsize=9, loc="upper left", framealpha=0.3, labelcolor=fg)
        fig.tight_layout()
        return fig
