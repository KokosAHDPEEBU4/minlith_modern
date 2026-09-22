"""Чистая математика наведения на точки диаграмм (без Qt и matplotlib).

Используется плиткой диаграммы, чтобы по позиции курсора в пикселях найти
ближайшую точку данных и показать имя образца (как tooltip в интерактивном
Plotly-HTML, но внутри приложения).
"""

from __future__ import annotations

import numpy as np


def nearest_point_index(
    x: float,
    y: float,
    points: np.ndarray | None,
    max_distance: float = 12.0,
) -> int | None:
    """Индекс ближайшей точки к ``(x, y)`` (в пикселях) или ``None``.

    ``points`` — массив формы ``(N, 2)`` в экранных координатах. Возвращает
    индекс, если расстояние не больше ``max_distance``.
    """
    if points is None:
        return None
    pts = np.asarray(points, dtype=float)
    if pts.size == 0 or pts.ndim != 2 or pts.shape[1] < 2:
        return None
    dist = np.hypot(pts[:, 0] - x, pts[:, 1] - y)
    idx = int(np.argmin(dist))
    return idx if float(dist[idx]) <= max_distance else None
