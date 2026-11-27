"""Feldspar Triangle — Ab-An-Or (Streckeisen, 1976)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts import ternary
from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import FELDSPAR_AN_LEVELS, FELDSPAR_LABELS
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)
from src.charts.labels import add_sample_legend, annotate_points


def feldspar_xy(ab: float, an: float, or_: float) -> tuple[float, float]:
    """Project Ab (left), An (right), Or (top) to Cartesian coordinates."""
    return ternary.xy(ab, an, or_)


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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "Feldspar Triangle — Ab-An-Or"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        ternary.draw_frame(ax, fg)
        self._draw_grid(ax, fg)
        self._draw_field_labels(ax, fg)

        minerals = data.minerals_wt
        n = len(data.sample_names)
        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []

        for i, name in enumerate(data.sample_names):
            ab = max(float(minerals.get("ab", np.zeros(n))[i]), 0.0)
            an = max(float(minerals.get("an", np.zeros(n))[i]), 0.0)
            or_ = max(float(minerals.get("or_", np.zeros(n))[i]), 0.0)

            total = ab + an + or_
            if total <= 1e-10:
                continue

            ab_n, an_n, or_n = ab / total, an / total, or_ / total
            x, y = feldspar_xy(ab_n, an_n, or_n)
            xs.append(x)
            ys.append(y)
            shown.append(name)

        if xs:
            colors = [ACCENT if n == 1 else COLORS[i % len(COLORS)] for i in range(len(xs))]
            ax.scatter(xs, ys, c=colors, s=64, alpha=0.9,
                       edgecolors=fg, linewidths=0.6, zorder=5)
            if len(xs) > 8:
                add_sample_legend(ax, shown, colors, fg)
            else:
                annotate_points(ax, xs, ys, shown, fg, fontsize=8, max_labels=8, limit=20)

        ternary.vertex_labels(ax, "Ab", "An", "Or", fg)
        ternary.setup_axes(ax)
        fig.text(0.5, 0.02,
                 "Границы An/(Ab+An) = 10, 30, 50, 70, 90 %; Or = 90 %.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig

    @staticmethod
    def _draw_grid(ax: Any, fg: str) -> None:
        for an_fraction in FELDSPAR_AN_LEVELS:
            # Constant An/(Ab+An) line: bottom edge -> Or corner.
            ternary.draw_segment(
                ax,
                (1.0 - an_fraction, an_fraction, 0.0),
                (0.0, 0.0, 1.0),
                fg, linewidth=0.5, alpha=0.35,
            )
        # Alkali-feldspar boundary Or = 90 %.
        ternary.draw_segment(ax, (0.1, 0.0, 0.9), (0.0, 0.1, 0.9),
                             fg, linewidth=0.5, alpha=0.35, linestyle="--")

    @staticmethod
    def _draw_field_labels(ax: Any, fg: str) -> None:
        for label, ab, an, or_ in FELDSPAR_LABELS:
            x, y = feldspar_xy(ab, an, or_)
            ax.text(x, y, label, ha="center", va="center", fontsize=7,
                    color=fg, alpha=0.5)
