"""QAPF — IUGS classification of plutonic rocks (Streckeisen, 1976)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import ACCENT, create_triangle, get_bg_color, get_fg_color


def _ternary_to_cartesian(q: float, a: float, p: float) -> tuple[float, float]:
    """Convert ternary (q, a, p) where q+a+p=1 to cartesian (x, y)."""
    # Q at top, A at bottom-left, P at bottom-right
    x = 0.5 * (2 * p + a) / max(q + a + p, 1e-10)
    y = q / max(q + a + p, 1e-10)
    return x, y


# IUGS field boundaries (simplified polygons as (x, y) in ternary coords)
# These are approximations of the standard QAPF fields
_FIELDS = [
    ("Quartzolite", [(0.9, 1.0), (0.95, 1.0), (1.0, 0.9), (0.9, 0.9)]),
    ("Quartz-rich", [(0.6, 1.0), (0.9, 1.0), (0.9, 0.9), (0.6, 0.6)]),
    ("Granite (Q-rich)", [(0.2, 0.6), (0.6, 0.6), (0.6, 0.35), (0.2, 0.35)]),
    ("Granite", [(0.2, 0.35), (0.6, 0.35), (0.6, 0.1), (0.2, 0.1)]),
    ("Granodiorite", [(0.1, 0.2), (0.2, 0.35), (0.2, 0.1), (0.1, 0.05)]),
    ("Tonalite", [(0.0, 0.1), (0.1, 0.2), (0.1, 0.05), (0.0, 0.0)]),
    ("Quartz Diorite", [(0.0, 0.1), (0.0, 0.0), (0.05, 0.0), (0.05, 0.05)]),
    ("Diorite", [(0.0, 0.0), (0.0, 0.05), (0.1, 0.1), (0.1, 0.0)]),
    ("Gabbro", [(0.0, 0.0), (0.1, 0.0), (0.2, 0.0), (0.0, 0.0)]),
    ("Syenite", [(0.2, 0.1), (0.2, 0.35), (0.4, 0.35), (0.4, 0.1)]),
    ("Monzonite", [(0.1, 0.1), (0.2, 0.1), (0.4, 0.1), (0.3, 0.0)]),
    ("Monzodiorite", [(0.05, 0.05), (0.1, 0.1), (0.3, 0.0), (0.15, 0.0)]),
    ("Syenodiorite", [(0.1, 0.05), (0.2, 0.1), (0.2, 0.0), (0.1, 0.0)]),
    ("Nepheline Syenite", [(0.2, 0.0), (0.2, -0.15), (0.4, -0.15), (0.4, 0.0)]),
]


class QAPFChart(ChartPlugin):
    def get_name(self) -> str:
        return "QAPF"

    def get_description(self) -> str:
        return "QAPF-треугольник классификации магматических пород (IUGS)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "QAPF — IUGS Classification"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        # Draw triangle edges
        for x1, y1, x2, y2 in [(0, 0, 1, 0), (0, 0, 0.5, 1), (1, 0, 0.5, 1)]:
            ax.plot([x1, x2], [y1, y2], color=fg, linewidth=0.8, alpha=0.4)

        # Draw field boundaries (simplified)
        # Internal lines: Q=10%, Q=20%, Q=60%, A/P boundaries
        for q_val in [0.1, 0.2, 0.6]:
            x_left, y_left = _ternary_to_cartesian(q_val, 1 - q_val, 0)
            x_right, y_right = _ternary_to_cartesian(q_val, 0, 1 - q_val)
            ax.plot([x_left, x_right], [y_left, y_right], color=fg,
                    linewidth=0.4, alpha=0.3, linestyle="--")

        # A=P line (vertical at x=0.5)
        ax.plot([0.5, 0.5], [0, 0.2], color=fg, linewidth=0.4, alpha=0.3, linestyle="--")

        # Plot samples
        names = data.sample_names
        minerals = data.minerals_wt
        n = len(names)

        for i in range(n):
            q = minerals.get("q", np.zeros(n))[i]
            ab = minerals.get("ab", np.zeros(n))[i]
            an = minerals.get("an", np.zeros(n))[i]
            or_ = minerals.get("or_", np.zeros(n))[i]

            total = q + ab + an + or_
            if total < 0.01:
                continue

            q_norm = q / total * 100
            a_norm = (ab + or_) / total * 100
            p_norm = an / total * 100

            x, y = _ternary_to_cartesian(q_norm, a_norm, p_norm)

            color = ACCENT if n == 1 else f"C{i % 10}"
            ax.plot(x, y, "o", color=color, markersize=8, markeredgecolor=fg, markeredgewidth=0.5)
            ax.annotate(names[i], (x, y), textcoords="offset points", xytext=(5, 5),
                        fontsize=8, color=fg, alpha=0.8)

        # Labels at vertices
        ax.text(0.5, 1.05, "Q", ha="center", va="bottom", fontsize=14, color=fg, fontweight="bold")
        ax.text(-0.05, -0.05, "A", ha="center", va="top", fontsize=14, color=fg, fontweight="bold")
        ax.text(1.05, -0.05, "P", ha="center", va="top", fontsize=14, color=fg, fontweight="bold")

        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.axis("off")
        fig.tight_layout()
        return fig
