"""Pie chart — mineral proportions for a single sample."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, create_figure, get_bg_color, get_fg_color


class PieChart(ChartPlugin):
    def get_name(self) -> str:
        return "Mineral Pie Chart"

    def get_description(self) -> str:
        return "Круговая диаграмма минерального состава одного образца"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        sample_idx = kwargs.get("sample_idx", 0)
        sample_name = data.sample_names[sample_idx] if sample_idx < len(data.sample_names) else "Sample"

        # Collect non-zero minerals
        labels = []
        values = []
        for name, arr in minerals.items():
            val = float(arr[sample_idx]) if sample_idx < len(arr) else 0.0
            if val > 0.01:
                labels.append(name)
                values.append(val)

        if not values:
            return create_figure(title=f"{sample_name} — no minerals")

        fig = create_figure(figsize=(8, 8), title=f"{sample_name} — Mineral Composition")
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        colors = COLORS[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%",
            colors=colors, startangle=90,
            textprops={"color": fg, "fontsize": 10},
            pctdistance=0.8,
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_color(bg)
            t.set_fontweight("bold")

        fig.tight_layout()
        return fig
