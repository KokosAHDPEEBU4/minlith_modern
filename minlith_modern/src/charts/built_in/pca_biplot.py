"""PCA biplot — principal components of mineral composition (2D)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.charts.base import ChartData, ChartPlugin
from src.charts.engines.matplotlib_engine import (
    ACCENT,
    COLORS,
    create_figure,
    get_fg_color,
    get_grid_color,
)


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

    def render(self, data: ChartData, **kwargs) -> Any:
        fg = get_fg_color()
        grid = get_grid_color()

        minerals = data.minerals_wt
        if not minerals:
            return create_figure(title="No mineral data")

        names = list(minerals.keys())
        n_samples = len(data.sample_names)
        n_minerals = len(names)

        if n_samples < 2:
            fig = create_figure(title="Need ≥2 samples for PCA")
            return fig

        if n_minerals < 2:
            fig = create_figure(title="Need ≥2 minerals for PCA")
            return fig

        # Build matrix: rows=samples, cols=minerals
        matrix = np.zeros((n_samples, n_minerals))
        for j, m in enumerate(names):
            for i in range(n_samples):
                matrix[i, j] = minerals[m][i] if i < len(minerals[m]) else 0.0

        # Center and compute covariance
        mean = matrix.mean(axis=0)
        centered = matrix - mean
        cov = np.cov(centered, rowvar=False)

        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Project onto first 2 PCs
        pc = centered @ eigenvectors[:, :2]
        var_explained = eigenvalues[:2] / eigenvalues.sum() * 100

        fig = create_figure(
            figsize=(10, 8),
            title=kwargs.get("title", "PCA Biplot — Mineral Composition"),
        )
        ax = fig.axes[0]

        # Plot samples
        ax.scatter(pc[:, 0], pc[:, 1], c=ACCENT, s=60, alpha=0.8,
                   edgecolors=fg, linewidth=0.5, zorder=5)

        for i, name in enumerate(data.sample_names):
            ax.annotate(name, (pc[i, 0], pc[i, 1]),
                        fontsize=8, color=fg, alpha=0.8,
                        xytext=(5, 5), textcoords="offset points")

        # Plot loadings as arrows
        scale = max(abs(pc[:, 0]).max(), abs(pc[:, 1]).max()) * 0.6
        loading_scale = scale / max(abs(eigenvectors[:, :2]).max(), 1e-10)

        for j, mineral in enumerate(names):
            dx = eigenvectors[j, 0] * loading_scale
            dy = eigenvectors[j, 1] * loading_scale
            ax.annotate("", xy=(dx, dy), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color=COLORS[j % len(COLORS)], lw=1.5))
            ax.text(dx * 1.1, dy * 1.1, mineral, fontsize=8, color=COLORS[j % len(COLORS)],
                    ha="center", va="center")

        ax.set_xlabel(f"PC1 ({var_explained[0]:.1f}%)", color=fg)
        ax.set_ylabel(f"PC2 ({var_explained[1]:.1f}%)", color=fg)
        ax.axhline(y=0, color=fg, linewidth=0.3, alpha=0.5)
        ax.axvline(x=0, color=fg, linewidth=0.3, alpha=0.5)
        ax.grid(color=grid, alpha=0.3)
        fig.tight_layout()
        return fig
