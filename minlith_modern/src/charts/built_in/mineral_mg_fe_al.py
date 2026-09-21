"""Mineral Mg-Fe-Al ternary — for mafic minerals (chlorite, mica)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    COLORS,
    create_triangle,
    get_bg_color,
    get_fg_color,
)


class MineralMgFeAl(ChartPlugin):
    def get_name(self) -> str:
        return "Mg-Fe-Al Ternary"

    def get_description(self) -> str:
        return "Треугольник Mg-Fe-Al для магниевых минералов"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        mgo = data.oxides.get("mgo", np.array([]))
        feo = data.oxides.get("feo", np.array([]))
        al2o3 = data.oxides.get("al2o3", np.array([]))

        if len(mgo) == 0:
            from src.charts.engines.matplotlib_engine import create_figure
            return create_figure(title="No oxide data")

        n = len(data.sample_names)
        total = mgo + feo + al2o3
        total[total == 0] = 1.0

        mg_norm = mgo / total
        fe_norm = feo / total
        al_norm = al2o3 / total

        fig = create_triangle(title=kwargs.get("title", "Mg-Fe-Al Ternary"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        # Draw ternary axes
        self._draw_triangle(ax, fg)

        # Convert to Cartesian
        x = 0.5 * (2 * fe_norm + mg_norm) / (mg_norm + fe_norm + al_norm)
        y = np.sqrt(3) / 2 * mg_norm / (mg_norm + fe_norm + al_norm)

        colors = [COLORS[i % len(COLORS)] for i in range(n)]
        ax.scatter(x, y, c=colors, s=60, alpha=0.8, edgecolors=fg, linewidth=0.5, zorder=5)

        for i in range(n):
            ax.annotate(data.sample_names[i], (x[i], y[i]),
                        fontsize=7, color=fg, alpha=0.8,
                        xytext=(5, 5), textcoords="offset points")

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 0.95)
        ax.set_aspect("equal")
        ax.axis("off")

        # Labels
        ax.text(0.5, -0.08, "FeO", ha="center", fontsize=11, fontweight="bold", color=fg)
        ax.text(1.05, 0.5, "MgO", ha="center", fontsize=11,
                fontweight="bold", color=fg, rotation=-60)
        ax.text(-0.05, 0.5, "Al₂O₃", ha="center", fontsize=11,
                fontweight="bold", color=fg, rotation=60)

        fig.tight_layout()
        return fig

    def _draw_triangle(self, ax, fg):
        """Draw equilateral triangle with grid lines."""
        # Outer triangle
        verts = [(0, 0), (1, 0), (0.5, np.sqrt(3) / 2)]
        for i in range(3):
            x0, y0 = verts[i]
            x1, y1 = verts[(i + 1) % 3]
            ax.plot([x0, x1], [y0, y1], color=fg, linewidth=0.8, alpha=0.5)

        # Grid lines (20% increments)
        for frac in [0.2, 0.4, 0.6, 0.8]:
            # Horizontal
            y = frac * np.sqrt(3) / 2
            x_left = frac / 2
            x_right = 1 - frac / 2
            ax.plot([x_left, x_right], [y, y], color=fg, linewidth=0.3, alpha=0.3)
