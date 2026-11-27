"""A-CN-K — Chemical Index of Alteration ternary (Nesbitt & Young, 1984)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts import ternary
from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import ACNK_MINERALS, ACNK_WEATHERING, CIA_LEVELS
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)
from src.charts.labels import add_sample_legend, annotate_points


def acnk_components(oxides: dict[str, np.ndarray], index: int) -> tuple[float, float, float]:
    """Return molar A, CN and K for one sample.

    ``CaO*`` is the silicate calcium: carbonate CaO is removed using CO₂ and
    apatite CaO using P₂O₅, then capped by Na₂O (McLennan, 1993).
    """
    def value(field: str) -> float:
        arr = oxides.get(field)
        if arr is None or index >= len(arr):
            return 0.0
        return float(arr[index])

    al = value("al2o3") / 101.96
    ca = value("cao") / 56.08
    na = value("na2o") / 61.98
    k = value("k2o") / 94.20
    co2 = value("co2") / 44.01
    p = value("p2o5") / 141.94

    ca_silicate = max(ca - co2 - (10.0 / 3.0) * p, 0.0)
    ca_star = min(ca_silicate, na)
    cn = ca_star + na
    return al, cn, k


def acnk_xy(a: float, cn: float, k: float) -> tuple[float, float]:
    """Project A (top), CN (left), K (right) to Cartesian coordinates."""
    return ternary.xy(cn, k, a)


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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "A-CN-K — Weathering Diagram"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        ternary.draw_frame(ax, fg)
        self._draw_cia_lines(ax, fg)
        self._draw_minerals(ax, fg)

        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        n = len(data.sample_names)
        for i, name in enumerate(data.sample_names):
            a, cn, k = acnk_components(data.oxides, i)
            total = a + cn + k
            if total <= 1e-10:
                continue
            x, y = acnk_xy(a / total, cn / total, k / total)
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

        ternary.vertex_labels(ax, "CN (CaO*+Na₂O)", "K (K₂O)", "A (Al₂O₃)", fg,
                              fontsize=10)
        ternary.setup_axes(ax)
        fig.text(0.5, 0.02,
                 "CaO* = min(CaO − CO₂ − 10/3·P₂O₅, Na₂O), мольные количества. "
                 "Горизонтальные линии — CIA 50–90.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig

    @staticmethod
    def _draw_minerals(ax: Any, fg: str) -> None:
        """Plot ideal mineral endmembers and the weathering direction."""
        (a0, cn0, k0), (a1, cn1, k1) = ACNK_WEATHERING
        x0, y0 = acnk_xy(a0, cn0, k0)
        x1, y1 = acnk_xy(a1, cn1, k1)
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", color=COLORS[4], lw=1.2,
                            alpha=0.55, linestyle="--"),
            zorder=3,
        )

        offsets = {
            "Плагиоклаз": (-8, -14),
            "К-полевой шпат": (8, -14),
            "Иллит/мусковит": (8, 8),
            "Каолинит/гиббсит": (16, -4),
        }
        for label, a, cn, k in ACNK_MINERALS:
            x, y = acnk_xy(a, cn, k)
            ax.scatter([x], [y], marker="s", s=34, color=COLORS[4],
                       edgecolors=fg, linewidths=0.5, alpha=0.85, zorder=4)
            dx, dy = offsets.get(label, (6, 6))
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(dx, dy),
                        fontsize=7, color=COLORS[4], alpha=0.8, zorder=6)

    @staticmethod
    def _draw_cia_lines(ax: Any, fg: str) -> None:
        for cia in CIA_LEVELS:
            y = cia / 100.0
            x_left = 0.5 * y
            x_right = 1.0 - 0.5 * y
            ax.plot([x_left, x_right], [y, y], color=fg, linewidth=0.4,
                    alpha=0.25, linestyle="--")
            ax.text(x_left + 0.02, y, f"CIA {cia}", ha="left", va="center",
                    fontsize=7, color=fg, alpha=0.45)
