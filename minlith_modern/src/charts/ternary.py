"""Shared geometry helpers for ternary (triangle) diagrams.

All built-in ternary charts use the same vertex convention:

    left  = (0, 0)
    right = (1, 0)
    top   = (0.5, sqrt(3)/2)

so a point with components ``(left, right, top)`` maps to::

    x = right + 0.5 * top
    y = sqrt(3)/2 * top

after normalisation to a unit sum.  Keeping the conversion in one place avoids
the axis mix-ups that previously made ternary charts rotate
their samples (A at the top instead of the left corner).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

SQRT3_2 = math.sqrt(3.0) / 2.0


def normalize(left: float, right: float, top: float) -> tuple[float, float, float]:
    """Normalise one ternary composition; returns zeros for a non-positive sum."""
    total = float(left) + float(right) + float(top)
    if total <= 0:
        return 0.0, 0.0, 0.0
    return float(left) / total, float(right) / total, float(top) / total


def normalize_arrays(
    left: np.ndarray, right: np.ndarray, top: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised normalisation. Non-positive sums are replaced by zeros."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    top = np.asarray(top, dtype=float)
    total = left + right + top
    safe = np.where(total > 0, total, 1.0)
    scale = np.where(total > 0, 1.0 / safe, 0.0)
    return left * scale, right * scale, top * scale


def xy(left: float, right: float, top: float) -> tuple[float, float]:
    """Convert one ternary composition to Cartesian coordinates."""
    left, right, top = normalize(left, right, top)
    return right + 0.5 * top, SQRT3_2 * top


def xy_arrays(
    left: np.ndarray, right: np.ndarray, top: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Convert arrays of ternary compositions to Cartesian coordinates."""
    left, right, top = normalize_arrays(left, right, top)
    return right + 0.5 * top, SQRT3_2 * top


def vertices() -> list[tuple[float, float]]:
    """Return the three triangle vertices (left, right, top)."""
    return [(0.0, 0.0), (1.0, 0.0), (0.5, SQRT3_2)]


def draw_frame(ax: Any, color: str, linewidth: float = 0.8, alpha: float = 0.4) -> None:
    """Draw the outer triangle."""
    verts = vertices()
    for i in range(3):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % 3]
        ax.plot([x0, x1], [y0, y1], color=color, linewidth=linewidth, alpha=alpha)


def draw_component_grid(
    ax: Any,
    color: str,
    step: float = 0.2,
    linewidth: float = 0.3,
    alpha: float = 0.25,
) -> None:
    """Draw a full ternary grid (lines of constant left/right/top)."""
    levels = np.arange(step, 1.0, step)
    for level in (float(v) for v in levels):
        # Constant top component: horizontal line near the top.
        ax.plot(
            [level, 1 - level],
            [SQRT3_2 * level, SQRT3_2 * level],
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            linestyle="--",
        )
        # Constant right component: parallel to the left edge.
        x1, y1 = xy(0.0, level, 1 - level)
        x2, y2 = xy(1 - level, level, 0.0)
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, alpha=alpha,
                linestyle="--")
        # Constant left component: parallel to the right edge.
        x1, y1 = xy(level, 0.0, 1 - level)
        x2, y2 = xy(level, 1 - level, 0.0)
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, alpha=alpha,
                linestyle="--")


def draw_segment(
    ax: Any,
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    color: str,
    linewidth: float = 0.5,
    alpha: float = 0.35,
    linestyle: str = "-",
) -> None:
    """Draw a straight segment between two ternary compositions."""
    x1, y1 = xy(*p1)
    x2, y2 = xy(*p2)
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth,
            alpha=alpha, linestyle=linestyle)


def draw_polyline(
    ax: Any,
    points: list[tuple[float, float, float]],
    color: str,
    linewidth: float = 0.5,
    alpha: float = 0.35,
    linestyle: str = "-",
) -> None:
    """Draw a polyline through ternary compositions."""
    xs, ys = zip(*(xy(*p) for p in points), strict=False)
    ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=alpha,
            linestyle=linestyle)


def vertex_labels(
    ax: Any,
    left: str,
    right: str,
    top: str,
    color: str,
    fontsize: float = 13,
) -> None:
    """Place the three vertex labels just outside the triangle."""
    ax.text(0.5, 1.04, top, ha="center", va="bottom", fontsize=fontsize,
            color=color, fontweight="bold")
    ax.text(-0.06, -0.05, left, ha="center", va="top", fontsize=fontsize,
            color=color, fontweight="bold")
    ax.text(1.06, -0.05, right, ha="center", va="top", fontsize=fontsize,
            color=color, fontweight="bold")


def setup_axes(ax: Any) -> None:
    """Common limits/aspect for ternary plots."""
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
