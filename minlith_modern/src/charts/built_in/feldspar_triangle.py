"""Feldspar Triangle — Ab-An-Or (Streckeisen, 1976)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, ACCENT, create_triangle, get_bg_color, get_fg_color


def _to_cartesian(ab: float, an: float, or_: float) -> tuple[float, float]:
    """Ab at bottom-left, An at bottom-right, Or at top."""
    total = ab + an + or_
    if total < 1e-10:
        return 0.0, 0.0
    x = 0.5 * (2 * an + ab) / total
    y = or_ / total
    return x, y


# Simplified feldspar classification boundaries
_FSP_LINES = [
    # Or=90% line (top)
    ((0.1, 0.9), (0.9, 0.9)),
    # Or=60% line
    ((0.2, 0.6), (0.8, 0.6)),
    # Or=35% line
    ((0.1, 0.35), (0.9, 0.35)),
    # An=Ab median (vertical at x=0.5)
    ((0.5, 0.0), (0.5, 0.35)),
]

_FSP_LABELS = [
    ("Albite", 0.15, 0.1),
    ("Oligoclase", 0.35, 0.1),
    ("Andesine", 0.5, 0.1),
    ("Labradorite", 0.65, 0.1),
    ("Bytownite", 0.8, 0.1),
    ("Anorthite", 0.9, 0.1),
    ("Sanidine", 0.5, 0.75),
    ("Orthoclase", 0.35, 0.85),
    ("Microcline", 0.65, 0.85),
]


class FeldsparTriangle(ChartPlugin):
    def get_name(self) -> str:
        return "Feldspar Triangle"

    def get_description(self) -> str:
        return "Треугольник полевых шпатов Ab-An-Or (Streckeisen)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "Feldspar Triangle — Ab-An-Or"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        # Triangle edges
        for x1, y1, x2, y2 in [(0, 0, 1, 0), (0, 0, 0.5, 1), (1, 0, 0.5, 1)]:
            ax.plot([x1, x2], [y1, y2], color=fg, linewidth=0.8, alpha=0.4)

        # Internal lines
        for (x1, y1), (x2, y2) in _FSP_LINES:
            ax.plot([x1, x2], [y1, y2], color=fg, linewidth=0.3, alpha=0.25, linestyle="--")

        # Field labels
        for label, x, y in _FSP_LABELS:
            ax.text(x, y, label, ha="center", va="center", fontsize=7, color=fg, alpha=0.4)

        # Plot samples
        minerals = data.minerals_wt
        for i, name in enumerate(data.sample_names):
            ab = minerals.get("ab", np.zeros(len(data.sample_names)))[i]
            an = minerals.get("an", np.zeros(len(data.sample_names)))[i]
            or_ = minerals.get("or_", np.zeros(len(data.sample_names)))[i]

            total = ab + an + or_
            if total < 0.01:
                continue

            x, y = _to_cartesian(ab, an, or_)
            color = ACCENT if len(data.sample_names) == 1 else COLORS[i % len(COLORS)]
            ax.plot(x, y, "o", color=color, markersize=8,
                    markeredgecolor=fg, markeredgewidth=0.5)
            ax.annotate(name, (x, y), textcoords="offset points",
                        xytext=(5, 5), fontsize=8, color=fg, alpha=0.8)

        # Vertex labels
        ax.text(0.5, 1.05, "Or", ha="center", va="bottom", fontsize=14, color=fg, fontweight="bold")
        ax.text(-0.05, -0.05, "Ab", ha="center", va="top", fontsize=14, color=fg, fontweight="bold")
        ax.text(1.05, -0.05, "An", ha="center", va="top", fontsize=14, color=fg, fontweight="bold")

        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.axis("off")
        fig.tight_layout()
        return fig
