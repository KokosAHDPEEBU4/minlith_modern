"""Bland-Altman plot — compare two measurement sets (e.g. MINLITH vs manual)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    create_figure, COLORS, BG_COLOR, FG_COLOR, GRID_COLOR, ACCENT,
)


class BlandAltmanPlugin(ChartPlugin):
    def get_name(self) -> str:
        return "bland_altman"

    def get_description(self) -> str:
        return "Bland-Altman agreement plot"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        fig = create_figure(figsize=(8, 6),
                            title=kwargs.get("title", "Bland-Altman Agreement Plot"))
        ax = fig.axes[0]

        # Expect data.metadata["compare"] = {"set_a": [...], "set_b": [...]}
        compare = data.metadata.get("compare", {})
        set_a = compare.get("set_a", [])
        set_b = compare.get("set_b", [])
        label_a = compare.get("label_a", "Set A")
        label_b = compare.get("label_b", "Set B")

        if not set_a or not set_b or len(set_a) != len(set_b):
            ax.text(0.5, 0.5, "Need equal-length 'set_a' and 'set_b'\nin data.metadata['compare']",
                    ha="center", va="center", fontsize=11, transform=ax.transAxes, color=FG_COLOR)
            return fig

        a = np.array(set_a)
        b = np.array(set_b)
        mean_val = (a + b) / 2
        diff = a - b

        mean_diff = np.mean(diff)
        std_diff = np.std(diff, ddof=1)
        loa_upper = mean_diff + 1.96 * std_diff
        loa_lower = mean_diff - 1.96 * std_diff

        ax.scatter(mean_val, diff, c=ACCENT, s=40, alpha=0.8,
                   edgecolors=FG_COLOR, linewidth=0.5, zorder=5)

        ax.axhline(mean_diff, color=ACCENT, linewidth=1.5, linestyle="-",
                    label=f"Mean diff = {mean_diff:.3f}")
        ax.axhline(loa_upper, color=COLORS[2], linewidth=1, linestyle="--",
                    label=f"+1.96 SD = {loa_upper:.3f}")
        ax.axhline(loa_lower, color=COLORS[2], linewidth=1, linestyle="--",
                    label=f"-1.96 SD = {loa_lower:.3f}")
        ax.axhline(0, color=FG_COLOR, linewidth=0.5, linestyle=":")

        ax.set_xlabel(f"Mean of {label_a} and {label_b}")
        ax.set_ylabel(f"Difference ({label_a} - {label_b})")
        ax.legend(loc="upper right", fontsize=9, framealpha=0.3, labelcolor=FG_COLOR)
        ax.grid(True, color=GRID_COLOR, alpha=0.3)
        fig.tight_layout()
        return fig
