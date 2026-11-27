"""QAPF — IUGS classification of plutonic rocks (Streckeisen, 1976)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts import ternary
from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import QAPF_LABELS, QAPF_Q_LEVELS, QAPF_RATIO_LEVELS
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)
from src.charts.labels import add_sample_legend, annotate_points


def qapf_xy(q: float, a: float, p: float) -> tuple[float, float]:
    """Project QAP (Q top, A left, P right) to Cartesian coordinates."""
    return ternary.xy(a, p, q)


def _ratio_point(q: float, ratio: float) -> tuple[float, float, float]:
    """Return (Q, A, P) for a given Q fraction and A/(A+P) ratio."""
    return q, (1.0 - q) * ratio, (1.0 - q) * (1.0 - ratio)


class QAPFChart(ChartPlugin):
    def get_name(self) -> str:
        return "QAPF"

    def get_description(self) -> str:
        return "QAPF-треугольник классификации магматических пород (IUGS, QAP-часть)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "QAPF — IUGS Classification (QAP)"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        ternary.draw_frame(ax, fg)
        self._draw_grid(ax, fg)
        self._draw_field_labels(ax, fg)

        names = data.sample_names
        n = len(names)
        minerals = data.minerals_wt

        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        for i, name in enumerate(names):
            q = float(minerals.get("q", np.zeros(n))[i])
            ab = max(float(minerals.get("ab", np.zeros(n))[i]), 0.0)
            an = max(float(minerals.get("an", np.zeros(n))[i]), 0.0)
            or_ = max(float(minerals.get("or_", np.zeros(n))[i]), 0.0)

            total = q + ab + an + or_
            if total <= 1e-10:
                continue

            q_norm = q / total
            a_norm = (ab + or_) / total
            p_norm = an / total
            x, y = qapf_xy(q_norm, a_norm, p_norm)
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

        ternary.vertex_labels(ax, "A", "P", "Q", fg)
        ternary.setup_axes(ax)
        fig.text(0.5, 0.02,
                 "QAP-часть; A = Ab + Or, P = An. Сетка IUGS, поля упрощены.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig

    @staticmethod
    def _draw_grid(ax: Any, fg: str) -> None:
        for q_percent in QAPF_Q_LEVELS:
            q = q_percent / 100.0
            ternary.draw_segment(ax, (q, 1.0 - q, 0.0), (q, 0.0, 1.0 - q),
                                 fg, linewidth=0.5, alpha=0.35)
        for ratio in QAPF_RATIO_LEVELS:
            ternary.draw_segment(ax, (0.0, 1.0 - ratio, ratio), (1.0, 0.0, 0.0),
                                 fg, linewidth=0.5, alpha=0.35, linestyle="--")

    @staticmethod
    def _draw_field_labels(ax: Any, fg: str) -> None:
        for label, q_percent, ratio in QAPF_LABELS:
            q, a, p = _ratio_point(q_percent / 100.0, ratio)
            x, y = qapf_xy(q, a, p)
            ax.text(x, y, label, ha="center", va="center", fontsize=6.5,
                    color=fg, alpha=0.45)
