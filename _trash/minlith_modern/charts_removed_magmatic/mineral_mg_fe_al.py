"""Mineral Mg-Fe-Al ternary — mafic-mineral / whole-rock composition."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts import ternary
from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)
from src.charts.labels import add_sample_legend, annotate_points


def mg_fe_al_xy(al: float, fe: float, mg: float) -> tuple[float, float]:
    """Project Al (top), Fe (left), Mg (right) cation fractions."""
    return ternary.xy(fe, mg, al)


class MineralMgFeAl(ChartPlugin):
    def get_name(self) -> str:
        return "Mg-Fe-Al Ternary"

    def get_description(self) -> str:
        return "Треугольник Mg-Fe-Al (катионные пропорции)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        mgo = data.oxides.get("mgo", np.array([]))
        feo = data.oxides.get("feo", np.array([]))
        fe2o3 = data.oxides.get("fe2o3", np.array([]))
        al2o3 = data.oxides.get("al2o3", np.array([]))

        if len(mgo) == 0:
            from src.charts.engines.matplotlib_engine import create_figure
            return create_figure(title="No oxide data")

        n = min(len(data.sample_names), len(mgo))
        fig = create_triangle(title=kwargs.get("title", "Mg-Fe-Al Ternary (mol)"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        ternary.draw_frame(ax, fg)
        ternary.draw_component_grid(ax, fg, step=0.2)

        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        for i in range(n):
            mg = float(mgo[i]) / 40.30
            f_tot = (float(feo[i]) if i < len(feo) else 0.0) + \
                0.8998 * (float(fe2o3[i]) if i < len(fe2o3) else 0.0)
            fe = f_tot / 71.85
            al = 2.0 * (float(al2o3[i]) if i < len(al2o3) else 0.0) / 101.96
            total = al + fe + mg
            if total <= 1e-10:
                continue
            x, y = mg_fe_al_xy(al / total, fe / total, mg / total)
            xs.append(x)
            ys.append(y)
            shown.append(data.sample_names[i])

        if xs:
            colors = [ACCENT if len(xs) == 1 else COLORS[i % len(COLORS)]
                      for i in range(len(xs))]
            ax.scatter(xs, ys, c=colors, s=64, alpha=0.9,
                       edgecolors=fg, linewidths=0.6, zorder=5)
            if len(xs) > 8:
                add_sample_legend(ax, shown, colors, fg)
            else:
                annotate_points(ax, xs, ys, shown, fg, fontsize=8, max_labels=8, limit=20)
        else:
            ax.text(0.5, 0.5, "Нет данных Mg-Fe-Al", ha="center", va="center",
                    fontsize=12, color=fg, alpha=0.7, transform=ax.transAxes)

        ternary.vertex_labels(ax, "Fe", "Mg", "Al", fg)
        ternary.setup_axes(ax)
        fig.text(0.5, 0.02,
                 "Катионные пропорции: Al = 2·Al₂O₃/101.96, Fe = FeOᵀ/71.85, Mg = MgO/40.30.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if xs and len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig
