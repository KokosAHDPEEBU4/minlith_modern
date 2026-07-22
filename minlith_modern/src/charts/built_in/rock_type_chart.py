"""Rock type distribution chart (Type 1-5)."""

from __future__ import annotations

from typing import Any

from collections import Counter

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, BG_COLOR, FG_COLOR, create_figure


_TYPE_NAMES = {
    1: "Type 1",
    2: "Type 2",
    3: "Type 3",
    4: "Type 4",
    5: "Type 5",
}


class RockTypeChart(ChartPlugin):
    def get_name(self) -> str:
        return "Rock Type Distribution"

    def get_description(self) -> str:
        return "Распределение образцов по типам пород (1-5)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        rock_types = data.rock_types
        if not rock_types:
            return create_figure(title="No rock type data")

        counts = Counter(rock_types)
        labels = [_TYPE_NAMES.get(t, f"Type {t}") for t in sorted(counts.keys())]
        values = [counts[t] for t in sorted(counts.keys())]

        chart_type = kwargs.get("chart_type", "pie")  # "pie" or "bar"

        if chart_type == "bar":
            fig = create_figure(figsize=(8, 5), title="Rock Type Distribution")
            ax = fig.axes[0]
            colors = COLORS[:len(labels)]
            ax.bar(labels, values, color=colors, edgecolor="none", width=0.6)
            ax.set_ylabel("Count")
            ax.grid(axis="y", color="#313244", alpha=0.3)
            for i, v in enumerate(values):
                ax.text(i, v + 0.1, str(v), ha="center", va="bottom", color=FG_COLOR, fontsize=10)
        else:
            fig = create_figure(figsize=(7, 7), title="Rock Type Distribution")
            ax = fig.add_subplot(111)
            ax.set_facecolor(BG_COLOR)
            colors = COLORS[:len(labels)]
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct="%1.0f%%",
                colors=colors, startangle=90,
                textprops={"color": FG_COLOR, "fontsize": 11},
            )
            for t in autotexts:
                t.set_fontsize(10)
                t.set_color(BG_COLOR)
                t.set_fontweight("bold")

        fig.tight_layout()
        return fig
