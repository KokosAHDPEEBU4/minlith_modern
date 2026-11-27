"""AFM diagram — Irvine & Baragar (1971) tholeiitic vs calc-alkaline."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts import ternary
from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import afm_boundary
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)
from src.charts.labels import add_sample_legend, annotate_points


def afm_xy(a: float, f: float, m: float) -> tuple[float, float]:
    """Project A (top), F (left), M (right) to Cartesian coordinates."""
    return ternary.xy(f, m, a)


class AFMPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "afm"

    def get_description(self) -> str:
        return "AFM — Irvine & Baragar (1971), треугольник A-F-M"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fig = create_triangle(title=kwargs.get("title", "AFM Diagram (Irvine & Baragar, 1971)"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        ternary.draw_frame(ax, fg)
        ternary.draw_component_grid(ax, fg, step=0.2)

        # Schematic divide: F-rich side is tholeiitic, M-rich side calc-alkaline.
        boundary = afm_boundary()
        xs_b, ys_b = zip(*(afm_xy(a, f, m) for a, f, m in boundary), strict=False)
        ax.plot(xs_b, ys_b, "--", color=COLORS[2], linewidth=1.4, alpha=0.9)
        tx, ty = afm_xy(0.18, 0.52, 0.30)
        ax.text(tx, ty, "Tholeiitic", fontsize=10, fontweight="bold", alpha=0.45,
                fontstyle="italic", color=fg, ha="center", va="center")
        tx, ty = afm_xy(0.18, 0.25, 0.57)
        ax.text(tx, ty, "Calc-Alkaline", fontsize=10, fontweight="bold", alpha=0.45,
                fontstyle="italic", color=fg, ha="center", va="center")

        n = len(data.sample_names)
        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        for i, name in enumerate(data.sample_names):
            feo = float(data.oxides.get("feo", np.zeros(n))[i])
            fe2o3 = float(data.oxides.get("fe2o3", np.zeros(n))[i])
            mgo = float(data.oxides.get("mgo", np.zeros(n))[i])
            na2o = float(data.oxides.get("na2o", np.zeros(n))[i])
            k2o = float(data.oxides.get("k2o", np.zeros(n))[i])

            f = feo + 0.8998 * fe2o3
            a = na2o + k2o
            m = mgo
            total = a + f + m
            if total <= 1e-10:
                continue

            x, y = afm_xy(a / total, f / total, m / total)
            xs.append(x)
            ys.append(y)
            shown.append(name)

        if xs:
            colors = [ACCENT if n == 1 else COLORS[i % len(COLORS)] for i in range(len(xs))]
            ax.scatter(xs, ys, c=colors, s=60, alpha=0.9,
                       edgecolors=fg, linewidths=0.6, zorder=5)
            if len(xs) > 8:
                add_sample_legend(ax, shown, colors, fg)
            else:
                annotate_points(ax, xs, ys, shown, fg, fontsize=8, max_labels=8, limit=20)

        ternary.vertex_labels(ax, "F (FeOᵀ)", "M (MgO)", "A (Na₂O+K₂O)", fg,
                              fontsize=11)
        ternary.setup_axes(ax)
        fig.text(0.5, 0.02,
                 "FeOᵀ = FeO + 0.8998·Fe₂O₃; граница показана схематично.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig
