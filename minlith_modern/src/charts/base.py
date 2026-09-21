"""Base class for chart plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class ChartData:
    """Data container for chart rendering."""

    sample_names: list[str] = field(default_factory=list)
    # Oxide compositions (rows=samples, cols=oxides)
    oxides: dict[str, np.ndarray] = field(default_factory=dict)
    # Mineral compositions (rows=samples)
    minerals_wt: dict[str, np.ndarray] = field(default_factory=dict)
    minerals_fu: dict[str, np.ndarray] = field(default_factory=dict)
    # Defect (residuals)
    defect: dict[str, np.ndarray] = field(default_factory=dict)
    # Rock types (1-5)
    rock_types: list[int] = field(default_factory=list)
    # Coefficients
    F_values: list[float] = field(default_factory=list)
    A_values: list[float] = field(default_factory=list)
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class ChartPlugin(ABC):
    """Abstract base class for all chart plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Short name for display (e.g. 'QAPF')."""

    @abstractmethod
    def get_description(self) -> str:
        """Human-readable description."""

    @property
    @abstractmethod
    def requires_minerals(self) -> bool:
        """Whether this chart needs mineral results."""

    @property
    @abstractmethod
    def requires_oxides(self) -> bool:
        """Whether this chart needs oxide data."""

    @abstractmethod
    def render(self, data: ChartData, **kwargs) -> Any:
        """Render chart and return the matplotlib Figure."""

    def export(self, data: ChartData, path: Path, fmt: str = "png",
               dpi: int = 150, **kwargs) -> None:
        """Export chart to file.

        ``fmt`` defaults to the file extension of ``path`` (``png`` if unknown).
        """
        path = Path(path)
        if fmt == "png" and path.suffix.lower() in (".pdf", ".svg", ".jpg", ".jpeg"):
            fmt = path.suffix.lower().lstrip(".")
        fig = self.render(data, **kwargs)
        fig.savefig(str(path), format=fmt, dpi=dpi, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)
