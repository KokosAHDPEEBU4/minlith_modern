"""Radar/spider chart — mineral profile of a single sample."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, get_bg_color, get_fg_color, get_grid_color, get_accent, create_figure


class RadarChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Radar"

    def get_description(self) -> str:
        return "Профиль минералов одного образца (spider diagram)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()
        grid = get_grid_color()
        accent = get_accent()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        sample_idx = kwargs.get("sample_idx", 0)
        sample_name = data.sample_names[sample_idx] if sample_idx < len(data.sample_names) else "Sample"

        names = list(minerals.keys())
        n = len(names)
        if n < 3:
            fig = create_figure(title=f"{sample_name} — need ≥3 minerals for radar")
            return fig

        values = [float(minerals[m][sample_idx]) if sample_idx < len(minerals[m]) else 0.0 for m in names]
        max_val = max(values) if values else 1.0
        if max_val == 0:
            max_val = 1.0

        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        values_plot = values + [values[0]]
        angles += [angles[0]]

        fig = create_figure(figsize=(8, 8), title=f"{sample_name} — Mineral Profile")
        ax = fig.add_subplot(111, polar=True)
        ax.set_facecolor(bg)

        ax.plot(angles, values_plot, color=accent, linewidth=2, linestyle="-")
        ax.fill(angles, values_plot, color=accent, alpha=0.25)

        ax.set_xticks(np.linspace(0, 2 * np.pi, n, endpoint=False))
        ax.set_xticklabels(names, fontsize=9, color=fg)
        ax.set_yticks([0.25 * max_val, 0.5 * max_val, 0.75 * max_val, max_val])
        ax.set_yticklabels([f"{v:.1f}" for v in [0.25 * max_val, 0.5 * max_val, 0.75 * max_val, max_val]],
                           fontsize=7, color=fg)
        ax.set_ylim(0, max_val * 1.1)
        ax.tick_params(colors=fg)
        ax.grid(color=grid, alpha=0.5)

        fig.tight_layout()
        return fig
