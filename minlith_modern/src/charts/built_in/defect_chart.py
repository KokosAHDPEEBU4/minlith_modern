"""Defect chart — oxide residuals bar chart."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, BG_COLOR, FG_COLOR, GRID_COLOR, create_figure


class DefectChart(ChartPlugin):
    def get_name(self) -> str:
        return "Defect Chart"

    def get_description(self) -> str:
        return "Столбчатая диаграмма остатков оксидов (defect)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return True

    def render(self, data: ChartData, **kwargs) -> Any:
        defect = data.defect
        if not defect:
            return create_figure(title="No defect data")

        sample_idx = kwargs.get("sample_idx", 0)
        sample_name = data.sample_names[sample_idx] if sample_idx < len(data.sample_names) else "Sample"

        oxides = list(defect.keys())
        values = [float(defect[o][sample_idx]) if sample_idx < len(defect[o]) else 0.0 for o in oxides]

        # Filter non-zero
        pairs = [(o, v) for o, v in zip(oxides, values) if abs(v) > 0.01]
        if not pairs:
            return create_figure(title=f"{sample_name} — defect ≈ 0")
        oxides, values = zip(*pairs)

        fig = create_figure(
            figsize=(max(8, len(oxides) * 0.8), 5),
            title=f"{sample_name} — Oxide Defect (Δ)",
        )
        ax = fig.axes[0]

        colors = ["#a6e3a1" if v >= 0 else "#f38ba8" for v in values]
        ax.bar(range(len(oxides)), values, color=colors, edgecolor="none", width=0.7)

        ax.set_xticks(range(len(oxides)))
        ax.set_xticklabels(oxides, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("Δ (formula units)")
        ax.axhline(y=0, color=FG_COLOR, linewidth=0.5, alpha=0.5)
        ax.grid(axis="y", color=GRID_COLOR, alpha=0.5)
        ax.set_axisbelow(True)
        fig.tight_layout()
        return fig
