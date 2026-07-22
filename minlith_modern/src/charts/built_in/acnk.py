"""A-CN-K — Chemical Index of Alteration ternary (Nesbitt & Young, 1984)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, BG_COLOR, FG_COLOR, GRID_COLOR, ACCENT, create_triangle


def _to_cartesian(a: float, cn: float, k: float) -> tuple[float, float]:
    """A at top, CN at bottom-left, K at bottom-right."""
    total = a + cn + k
    if total < 1e-10:
        return 0.0, 0.0
    x = 0.5 * (2 * k + cn) / total
    y = a / total
    return x, y


# Simplified A-CN-K fields
_FIELD_LINES = [
    # Weathering trend lines (horizontal-ish)
    ((0.5, 0.0), (0.5, 1.0)),  # A-K median
    ((0.0, 0.0), (0.5, 1.0)),  # A-CN line
    ((1.0, 0.0), (0.5, 1.0)),  # A-K line
    # CIA=50, 60, 70, 80, 90 lines (approximate horizontal)
    ((0.0, 0.5), (1.0, 0.5)),  # ~CIA 50
    ((0.0, 0.6), (1.0, 0.6)),  # ~CIA 60
    ((0.0, 0.7), (1.0, 0.7)),  # ~CIA 70
    ((0.0, 0.8), (1.0, 0.8)),  # ~CIA 80
    ((0.0, 0.9), (1.0, 0.9)),  # ~CIA 90
]


class ACNKChart(ChartPlugin):
    def get_name(self) -> str:
        return "A-CN-K"

    def get_description(self) -> str:
        return "A-CN-K — треугольник выветривания (Nesbitt & Young)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        fig = create_triangle(title=kwargs.get("title", "A-CN-K — Weathering Diagram"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_COLOR)

        # Triangle edges
        for x1, y1, x2, y2 in [(0, 0, 1, 0), (0, 0, 0.5, 1), (1, 0, 0.5, 1)]:
            ax.plot([x1, x2], [y1, y2], color=FG_COLOR, linewidth=0.8, alpha=0.4)

        # Field lines
        for (x1, y1), (x2, y2) in _FIELD_LINES:
            ax.plot([x1, x2], [y1, y2], color=FG_COLOR, linewidth=0.3, alpha=0.25, linestyle="--")

        # Plot samples
        al2o3 = data.oxides.get("al2o3", np.array([]))
        cao = data.oxides.get("cao", np.array([]))
        na2o = data.oxides.get("na2o", np.array([]))
        k2o = data.oxides.get("k2o", np.array([]))

        for i, name in enumerate(data.sample_names):
            if i < len(al2o3):
                # Molecular proportions (approximate with oxide wt%)
                a = float(al2o3[i]) / 101.96  # Al2O3
                cn = float(cao[i]) / 56.08 + float(na2o[i]) / 61.98  # CaO + Na2O
                k = float(k2o[i]) / 94.2  # K2O

                x, y = _to_cartesian(a, cn, k)
                color = ACCENT if len(data.sample_names) == 1 else COLORS[i % len(COLORS)]
                ax.plot(x, y, "o", color=color, markersize=8,
                        markeredgecolor=FG_COLOR, markeredgewidth=0.5)
                ax.annotate(name, (x, y), textcoords="offset points",
                            xytext=(5, 5), fontsize=8, color=FG_COLOR, alpha=0.8)

        # Vertex labels
        ax.text(0.5, 1.05, "A (Al₂O₃)", ha="center", va="bottom", fontsize=11, color=FG_COLOR, fontweight="bold")
        ax.text(-0.05, -0.05, "CN (CaO+Na₂O)", ha="center", va="top", fontsize=11, color=FG_COLOR, fontweight="bold")
        ax.text(1.05, -0.05, "K (K₂O)", ha="center", va="top", fontsize=11, color=FG_COLOR, fontweight="bold")

        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.axis("off")
        fig.tight_layout()
        return fig
