"""Collision-aware point labels for scatter/ternary charts."""

from __future__ import annotations

import math
from typing import Any

_OFFSETS = (
    (5, 5), (5, -12), (-5, 5), (-5, -12),
    (9, 10), (-9, 10), (9, -16), (-9, -16),
    (0, 11), (0, -16), (12, 2), (-12, 2),
)


def shorten(text: str, limit: int = 24) -> str:
    """Normalise whitespace and truncate long sample names."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 1)].rstrip() + "…"


def add_sample_legend(
    ax: Any,
    labels: Any,
    colors: Any,
    color: str,
    fontsize: float = 8,
    loc: str = "center left",
    bbox: tuple[float, float] = (1.02, 0.5),
    limit: int = 28,
    max_items: int = 15,
) -> Any:
    """Add an out-of-axes legend mapping sample colour to sample name.

    Used for dense selections where in-plot labels would collide.  Callers
    should shrink the axes area (``fig.subplots_adjust(right=...)``) to make
    room for the legend.
    """
    from matplotlib.lines import Line2D

    handles, legend_labels = ax.get_legend_handles_labels()
    for i, label in enumerate(list(labels)[:max_items]):
        handles.append(
            Line2D(
                [0], [0], marker="o", linestyle="none",
                markerfacecolor=colors[i % len(colors)],
                markeredgecolor="none", markersize=6,
            )
        )
        legend_labels.append(shorten(label, limit))
    return ax.legend(
        handles=handles, labels=legend_labels, loc=loc, bbox_to_anchor=bbox,
        frameon=False, fontsize=fontsize, labelcolor=color,
        handletextpad=0.4, borderaxespad=0.0,
    )


def annotate_points(
    ax: Any,
    xs: Any,
    ys: Any,
    labels: Any,
    color: str,
    fontsize: float = 8,
    max_labels: int | None = None,
    limit: int = 24,
) -> int:
    """Annotate points, skipping labels that would overlap an already placed one.

    Returns the number of labels actually drawn.  This keeps dense clusters
    readable without adding a heavy dependency such as ``adjustText``.
    """
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    placed: list = []
    drawn = 0

    for x, y, label in zip(xs, ys, labels, strict=False):
        if not (math.isfinite(float(x)) and math.isfinite(float(y))):
            continue
        if max_labels is not None and drawn >= max_labels:
            break

        text = shorten(label, limit)
        for dx, dy in _OFFSETS:
            ann = ax.annotate(
                text,
                (float(x), float(y)),
                textcoords="offset points",
                xytext=(dx, dy),
                fontsize=fontsize,
                color=color,
                alpha=0.85,
                zorder=6,
            )
            bbox = ann.get_window_extent(renderer=renderer).expanded(1.06, 1.18)
            if not any(bbox.overlaps(other) for other in placed):
                placed.append(bbox)
                drawn += 1
                break
            ann.remove()

    return drawn
