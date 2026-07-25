"""k1-k4 vs F chart — visualize adaptive chlorite coefficients."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import COLORS, create_figure, get_fg_color, get_grid_color
from src.core.coefficients import calculate_coefficients


class KFChart(ChartPlugin):
    def get_name(self) -> str:
        return "Коэффициенты хлорита vs F"

    def get_description(self) -> str:
        return "Зависимость адаптивных коэффициентов k1-k4 от F (Fe³⁺/ΣFe)"

    @property
    def requires_minerals(self) -> bool:
        return False

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fig = create_figure(
            figsize=(10, 6),
            title=kwargs.get("title", "Коэффициенты хлорита k1-k4 vs F"),
        )
        ax = fig.add_subplot(111)

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

        # Plot sample points if available
        sample_names = kwargs.get("sample_names", [])
        sample_coeffs = kwargs.get("sample_coefficients", [])
        if sample_names and sample_coeffs:
            for name, coeff in zip(sample_names, sample_coeffs):
                f_val = coeff.F
                ax.plot(f_val, coeff.k1, "o", color="#89b4fa", markersize=6, alpha=0.7)
                ax.plot(f_val, coeff.k2, "o", color="#f38ba8", markersize=6, alpha=0.7)
                ax.plot(f_val, coeff.k3, "o", color="#a6e3a1", markersize=6, alpha=0.7)
                ax.plot(f_val, coeff.k4, "o", color="#fab387", markersize=6, alpha=0.7)
                ax.annotate(name, (f_val, coeff.k1), fontsize=7, ha="center", va="bottom",
                           color=fg)

        ax.set_xlabel("F (Fe³⁺/ΣFe)", color=fg)
        ax.set_ylabel("Значение коэффициента", color=fg)
        ax.legend(loc="upper right", fontsize=9)
        ax.set_xlim(0, 1)
        ax.grid(True, alpha=0.3, color=grid)

        return fig
