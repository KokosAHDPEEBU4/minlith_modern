"""Heatmap — mineral composition matrix (samples × minerals)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import create_figure, get_bg_color, get_fg_color


class HeatmapChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Heatmap"

    def get_description(self) -> str:
        return "Тепловая карта минерального состава (образцы × минералы)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        from src.charts.engines.matplotlib_engine import get_chart_theme

        bg = get_bg_color()
        fg = get_fg_color()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        names = list(minerals.keys())
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        matrix = np.zeros((n_samples, n_minerals))
        for j, mineral in enumerate(names):
            arr = minerals[mineral]
            matrix[: len(arr), j] = arr[:n_samples]

        fig = create_figure(
            figsize=(max(8, n_minerals * 0.6), max(4, n_samples * 0.4)),
            title=kwargs.get("title", "Mineral Composition Heatmap"),
        )
        ax = fig.axes[0]

        import matplotlib.colors as mcolors
        if get_chart_theme() == "light":
            cmap = mcolors.LinearSegmentedColormap.from_list(
                "minlith_light", ["#ffffff", "#e8f0fe", "#89b4fa", "#f38ba8"],
            )
            text_low = "#1e1e2e"
            text_high = "#ffffff"
        else:
            cmap = mcolors.LinearSegmentedColormap.from_list(
                "minlith_dark", ["#1e1e2e", "#313244", "#45475a", "#89b4fa", "#f38ba8"],
            )
            text_low = fg
            text_high = bg

        im = ax.imshow(matrix, cmap=cmap, aspect="auto", interpolation="nearest")

        ax.set_xticks(range(n_minerals))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9, color=fg)
        ax.set_yticks(range(n_samples))
        ax.set_yticklabels(data.sample_names[:n_samples], fontsize=9, color=fg)

        for i in range(n_samples):
            for j in range(n_minerals):
                val = matrix[i, j]
                if val > 0.01:
                    tc = text_high if val > matrix.max() * 0.5 else text_low
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                            fontsize=7, color=tc)

        cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
        cbar.ax.tick_params(colors=fg)
        cbar.set_label("wt%", color=fg)

        fig.tight_layout()
        return fig
