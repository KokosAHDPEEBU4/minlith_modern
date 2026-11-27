"""SiO₂ vs K₂O diagram — Peccerillo & Taylor (1976) rock series classification."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import K2O_BOUNDARIES, K2O_FIELD_LABELS, K2O_SIO2
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_figure,
    get_bg_color,
    get_fg_color,
    get_grid_color,
)
from src.charts.labels import add_sample_legend, annotate_points


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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(figsize=(8, 7),
                            title=kwargs.get("title", "SiO₂–K₂O (Peccerillo & Taylor, 1976)"))
        ax = fig.axes[0]

        sio2 = np.asarray(data.oxides.get("sio2", np.array([])), dtype=float)
        k2o = np.asarray(data.oxides.get("k2o", np.zeros(len(sio2))), dtype=float)

        self._draw_boundaries(ax, fg, get_bg_color())

        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        n = min(len(data.sample_names), len(sio2))
        for i in range(n):
            if not (math.isfinite(sio2[i]) and math.isfinite(k2o[i])):
                continue
            xs.append(float(sio2[i]))
            ys.append(float(k2o[i]))
            shown.append(data.sample_names[i])

        if xs:
            colors = [ACCENT if len(xs) == 1 else COLORS[i % len(COLORS)]
                      for i in range(len(xs))]
            ax.scatter(xs, ys, c=colors, s=64, alpha=0.9,
                       edgecolors=fg, linewidths=0.6, zorder=5)
            if len(xs) > 8:
                add_sample_legend(ax, shown, colors, fg)
            else:
                annotate_points(ax, xs, ys, shown, fg, fontsize=8,
                                max_labels=8, limit=20)

        x_min = min(45.0, math.floor(min(xs) - 1.0)) if xs else 45.0
        x_max = max(80.0, math.ceil(max(xs) + 1.0)) if xs else 80.0
        y_max = max(5.0, math.ceil(max(ys) + 0.5)) if ys else 5.0

        ax.set_xlabel("SiO₂ (wt%)")
        ax.set_ylabel("K₂O (wt%)")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(0, y_max)
        ax.grid(True, color=grid, alpha=0.3)
        fig.text(0.5, 0.02,
                 "Границы серий — упрощённые кривые Peccerillo & Taylor (1976).",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig

    @staticmethod
    def _draw_boundaries(ax: Any, fg: str, bg: str) -> None:
        colors = {
            "low_medium": COLORS[3],
            "medium_high": COLORS[2],
            "high_shoshonite": COLORS[4],
        }
        for key, y_vals in K2O_BOUNDARIES.items():
            ax.plot(K2O_SIO2, y_vals, "--", color=colors[key], linewidth=1.2, alpha=0.85)
        for label, (lx, ly) in K2O_FIELD_LABELS.items():
            ax.text(lx, ly, label, fontsize=8, alpha=0.7, fontstyle="italic",
                    color=fg,
                    bbox=dict(facecolor=bg, edgecolor="none", alpha=0.55, pad=1.5))
