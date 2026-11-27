"""TAS — Total Alkali-Silica diagram (Le Maitre et al., 2005)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.classification import (
    TAS_ALKALI_X,
    TAS_ALKALI_Y,
    TAS_FIELDS,
    TAS_LABELS,
)
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)
from src.charts.labels import add_sample_legend, annotate_points


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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(figsize=(10, 7), title=kwargs.get("title", "TAS — Total Alkali-Silica"))
        ax = fig.axes[0]

        self._draw_fields(ax, fg)

        ax.plot(TAS_ALKALI_X, TAS_ALKALI_Y, "--", color="#f38ba8",
                linewidth=1.0, alpha=0.7, label="Alkali / Subalkali")
        ax.legend(fontsize=9, loc="upper left", framealpha=0.3, labelcolor=fg)

        sio2 = np.asarray(data.oxides.get("sio2", np.array([])), dtype=float)
        na2o = np.asarray(data.oxides.get("na2o", np.zeros(len(sio2))), dtype=float)
        k2o = np.asarray(data.oxides.get("k2o", np.zeros(len(sio2))), dtype=float)
        total_alk = na2o + k2o

        xs: list[float] = []
        ys: list[float] = []
        shown: list[str] = []
        n = min(len(data.sample_names), len(sio2))
        for i in range(n):
            if not (math.isfinite(sio2[i]) and math.isfinite(total_alk[i])):
                continue
            xs.append(float(sio2[i]))
            ys.append(float(total_alk[i]))
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

        # Never clip samples that fall outside the classic 35-80 % SiO2 window.
        if xs:
            x_min = min(35.0, math.floor(min(xs) - 2.0))
            x_max = max(80.0, math.ceil(max(xs) + 2.0))
            y_max = max(16.0, math.ceil(max(ys) + 1.0))
        else:
            x_min, x_max, y_max = 35.0, 80.0, 16.0

        ax.set_xlabel("SiO₂ (wt%)")
        ax.set_ylabel("Na₂O + K₂O (wt%)")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(0, y_max)
        ax.grid(True, color=grid, alpha=0.3)
        fig.text(0.5, 0.02,
                 "Поля и линия — упрощённая схема; вне диапазона 35–80 % SiO₂ "
                 "классификация не стандартна.",
                 ha="center", fontsize=8, color=fg, alpha=0.6)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        if len(xs) > 8:
            fig.subplots_adjust(right=0.76)
        return fig

    @staticmethod
    def _draw_fields(ax: Any, fg: str) -> None:
        for name, points in TAS_FIELDS.items():
            xs = [p[0] for p in points] + [points[0][0]]
            ys = [p[1] for p in points] + [points[0][1]]
            ax.plot(xs, ys, color=fg, linewidth=0.4, alpha=0.3)
            ax.fill(xs, ys, color=fg, alpha=0.02)
            if name in TAS_LABELS:
                lx, ly = TAS_LABELS[name]
                ax.text(lx, ly, name, ha="center", va="center", fontsize=7,
                        color=fg, alpha=0.55)
