"""PCA biplot — principal components of mineral composition (2D)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.data_builder import (
    mineral_label,
    mineral_series,
    visible_mineral_fields,
)
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)
from src.charts.labels import add_sample_legend, annotate_points


class PCABiplot(ChartPlugin):
    def get_name(self) -> str:
        return "PCA Biplot"

    def get_description(self) -> str:
        return "Главные компоненты минерального состава (2D)"

    @property
    def requires_minerals(self) -> bool:
        return True

    @property
    def requires_oxides(self) -> bool:
        return False

    def render(self, data: ChartData, **kwargs: Any) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        fields = visible_mineral_fields(data)
        n_samples = len(data.sample_names)
        n_minerals = len(fields)

        if n_samples < 2:
            return create_figure(title="Need ≥2 samples for PCA")
        if n_minerals < 2:
            return create_figure(title="Need ≥2 non-zero minerals for PCA")

        matrix = np.vstack([mineral_series(data, field, n_samples) for field in fields]).T

        # Center and compute covariance
        mean = matrix.mean(axis=0)
        centered = matrix - mean
        cov = np.cov(centered, rowvar=False)

        # Eigendecomposition; tiny negative eigenvalues are numerical noise.
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = np.clip(eigenvalues[idx], 0.0, None)
        eigenvectors = eigenvectors[:, idx]

        total_variance = float(eigenvalues.sum())
        if total_variance <= 1e-12:
            return create_figure(title="PCA: no variance in mineral data")

        # Project onto first 2 PCs
        pc = centered @ eigenvectors[:, :2]
        var_explained = eigenvalues[:2] / total_variance * 100

        fig = create_figure(
            figsize=(10, 8),
            title=kwargs.get("title", "PCA Biplot — Mineral Composition"),
        )
        ax = fig.axes[0]

        colors = [ACCENT if n_samples == 1 else COLORS[i % len(COLORS)]
                  for i in range(n_samples)]
        ax.scatter(pc[:, 0], pc[:, 1], c=colors, s=60, alpha=0.8,
                   edgecolors=fg, linewidth=0.5, zorder=5)
        if n_samples > 8:
            add_sample_legend(ax, data.sample_names, colors, fg)
        else:
            annotate_points(ax, pc[:, 0], pc[:, 1], data.sample_names, fg,
                            fontsize=8, max_labels=8, limit=20)

        # Plot loadings as arrows.  Scale each axis independently so the
        # arrows stay inside the sample cloud instead of stretching the canvas.
        span_x = max(float(np.abs(pc[:, 0]).max()), 1e-10)
        span_y = max(float(np.abs(pc[:, 1]).max()), 1e-10)
        loading_x = span_x * 0.9 / max(float(np.abs(eigenvectors[:, 0]).max()), 1e-10)
        loading_y = span_y * 0.9 / max(float(np.abs(eigenvectors[:, 1]).max()), 1e-10)

        norms = np.hypot(eigenvectors[:, 0], eigenvectors[:, 1])
        max_norm = max(float(norms.max()), 1e-10)
        for j, field in enumerate(fields):
            # Very small loadings produce labels stacked on the origin.
            if float(norms[j]) < 0.18 * max_norm:
                continue
            dx = eigenvectors[j, 0] * loading_x
            dy = eigenvectors[j, 1] * loading_y
            color = COLORS[j % len(COLORS)]
            ax.annotate("", xy=(dx, dy), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color=color, lw=1.5))
            ax.text(dx * 1.05, dy * 1.05, mineral_label(field), fontsize=8,
                    color=color, ha="center", va="center")

        ax.set_xlim(-span_x * 1.25, span_x * 1.25)
        ax.set_ylim(-span_y * 1.25, span_y * 1.25)
        ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}%)", color=fg)
        ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}%)", color=fg)
        ax.axhline(y=0, color=fg, linewidth=0.3, alpha=0.5)
        ax.axvline(x=0, color=fg, linewidth=0.3, alpha=0.5)
        ax.grid(color=grid, alpha=0.3)
        fig.subplots_adjust(
            left=0.12, right=0.76 if n_samples > 8 else 0.95,
            bottom=0.1, top=0.92,
        )
        return fig
