"""k1-k4 vs F chart — visualize adaptive chlorite coefficients."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import create_figure, get_fg_color, get_grid_color
from src.core.coefficients import calculate_coefficients


class KFChart(ChartPlugin):
    def get_name(self) -> str:
        return "Коэффициенты хлорита vs F"

    def get_description(self) -> str:
        return "Зависимость коэффициентов k1-k4 от F = FeO*/(FeO*+MgO)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(
            figsize=(10, 6),
            title=kwargs.get("title", "Коэффициенты хлорита k1-k4 vs F"),
        )
        ax = fig.axes[0]

        # Generate k1-k4 curves
        f_range = np.linspace(0.0, 1.0, 500)
        k1_vals, k2_vals, k3_vals, k4_vals = [], [], [], []
        for f in f_range:
            c = calculate_coefficients(f, 0.0)
            k1_vals.append(c.k1)
            k2_vals.append(c.k2)
            k3_vals.append(c.k3)
            k4_vals.append(c.k4)

        # Plot curves
        ax.plot(f_range, k1_vals, color="#89b4fa", linewidth=2, label="k1 (Mg→Chl)")
        ax.plot(f_range, k2_vals, color="#f38ba8", linewidth=2, label="k2 (Fe²⁺→Chl)")
        ax.plot(f_range, k3_vals, color="#a6e3a1", linewidth=2, label="k3 (Al→Chl)")
        ax.plot(f_range, k4_vals, color="#fab387", linewidth=2, label="k4 (Si→Chl)")

        # Range boundaries
        boundaries = [0.21, 0.51, 0.70, 0.87]
        for b in boundaries:
            ax.axvline(x=b, color="#585b70", linestyle="--", linewidth=0.8, alpha=0.5)

        # Plot the actual samples from ChartData (F + k1-k4), if present.
        k_values = data.metadata.get("k_values", {})
        f_samples = list(data.F_values)
        series_colors = {
            "k1": "#89b4fa", "k2": "#f38ba8", "k3": "#a6e3a1", "k4": "#fab387",
        }
        if f_samples and k_values:
            for key, color in series_colors.items():
                vals = k_values.get(key, [])
                if len(vals) >= len(f_samples):
                    ax.scatter(f_samples, vals[:len(f_samples)], color=color,
                               s=22, alpha=0.85, edgecolors=fg,
                               linewidths=0.3, zorder=6)

        ax.set_xlabel("F = FeO*/(FeO* + MgO)", color=fg)
        ax.set_ylabel("Значение коэффициента", color=fg)
        ax.legend(loc="upper right", fontsize=9, labelcolor=fg)
        ax.set_xlim(0, 1)
        ax.grid(True, alpha=0.3, color=grid)
        fig.tight_layout()

        return fig
