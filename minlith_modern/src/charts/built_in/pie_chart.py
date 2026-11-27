"""Pie chart — mineral proportions for a single sample."""

from __future__ import annotations

from typing import Any

from src.charts.base import ChartData, ChartPlugin
from src.charts.data_builder import mineral_label, visible_mineral_fields
from src.charts.engines.matplotlib_engine import (
    COLORS,
    create_figure,
    get_bg_color,
    get_fg_color,
)


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

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        bg = get_bg_color()
        fg = get_fg_color()

        fields = visible_mineral_fields(data)
        if not fields:
            return create_figure(title="No mineral data")

        sample_idx = kwargs.get("sample_idx", 0)
        sample_name = (
            data.sample_names[sample_idx]
            if sample_idx < len(data.sample_names) else "Sample"
        )

        pairs: list[tuple[str, float]] = []
        for field in fields:
            arr = data.minerals_wt[field]
            val = float(arr[sample_idx]) if sample_idx < len(arr) else 0.0
            if val > 0.01:
                pairs.append((mineral_label(field), val))

        if not pairs:
            return create_figure(title=f"{sample_name} — no minerals")

        # Tiny slices create unreadable overlapping labels; fold them into
        # one "Прочие" wedge.
        total = sum(v for _, v in pairs)
        threshold = max(0.8, total * 0.02)
        main = [(name, val) for name, val in pairs if val >= threshold]
        other = sum(val for name, val in pairs if val < threshold)
        if other > 0:
            main.append(("Прочие", other))

        labels = [name for name, _ in main]
        values = [val for _, val in main]

        fig = create_figure(figsize=(10, 8), title=f"{sample_name} — Mineral Composition")
        ax = fig.axes[0]
        ax.set_facecolor(bg)
        ax.axis("off")

        colors = [COLORS[i % len(COLORS)] for i in range(len(labels))]
        wedges, texts, autotexts = ax.pie(  # type: ignore[misc]
            values, autopct="%1.1f%%",
            colors=colors, startangle=90,
            textprops={"color": bg, "fontsize": 8, "fontweight": "bold"},
            pctdistance=0.72,
            wedgeprops={"edgecolor": bg, "linewidth": 0.6},
        )
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.02, 0.5),
                  frameon=False, fontsize=9, labelcolor=fg)
        fig.subplots_adjust(left=0.02, right=0.74, top=0.92, bottom=0.04)
        return fig
