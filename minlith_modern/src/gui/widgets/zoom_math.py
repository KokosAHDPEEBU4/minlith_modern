"""Чистая математика интерактивных операций с диаграммами.

Модуль не импортирует PyQt и matplotlib и тестируется без QApplication.

Инварианты (документированы per-func):
- ``zoom_lims``: ``anchor`` не смещается; ``factor > 1`` — приближение.
- ``pan_lims``: ширина диапазона сохраняется.
"""

from __future__ import annotations

import math
from enum import Enum

# ── constants ───────────────────────────────────────────────────────────────

DEFAULT_ZOOM_STEP: float = 1.2
MIN_RANGE_WIDTH: float = 1e-12

# matplotlib categoricals use StrCategoryLocator; strings for probe without import
_STR_CATEGORY_LOCATOR = "StrCategoryLocator"

# ── ModifierMode ────────────────────────────────────────────────────────────


class ModifierMode(Enum):
    """Результат разбора модификаторов колеса мыши (§8.1 SPEC)."""

    ZOOM_XY = "zoom_xy"
    ZOOM_X = "zoom_x"
    ZOOM_Y = "zoom_y"
    PAN_X = "pan_x"
    NONE = "none"


# ── zoom_lims ───────────────────────────────────────────────────────────────


def zoom_lims(
    lim: tuple[float, float],
    anchor: float,
    factor: float,
    *,
    log: bool = False,
    min_range_width: float = MIN_RANGE_WIDTH,
) -> tuple[float, float]:
    """Новые границы диапазона при зуме вокруг ``anchor``.

    ``factor > 1`` — приближение (диапазон сжимается); ``factor < 1`` —
    отдаление (расширяется).  ``anchor`` — точка в координатах данных, которая
    остаётся на месте: её доля в диапазоне не меняется (инвариант якоря).

    Лог-ветка активируется при ``log=True`` и ``lo > 0, hi > 0, anchor > 0``.
    При ``factor <= 0`` или вырожденном диапазоне (``lo == hi``) возвращаются
    исходные пределы.

    Результат не может быть уже ``min_range_width`` (абсолютная ширина в
    единицах шкалы); при ограничении диапазон остаётся прежним.
    """
    lo, hi = float(lim[0]), float(lim[1])
    factor = float(factor)
    if factor <= 0 or lo == hi:
        return (lo, hi)

    def _clamp(lo_n: float, hi_n: float) -> tuple[float, float]:
        if log:
            w = math.log10(hi_n / lo_n) if lo_n > 0 and hi_n > 0 else 0.0
        else:
            w = hi_n - lo_n
        if w < min_range_width:
            return (lo, hi)
        return (lo_n, hi_n)

    if log and lo > 0 and hi > 0 and anchor > 0:
        lo_l = math.log10(lo)
        hi_l = math.log10(hi)
        a_l = math.log10(anchor)
        new_lo = 10 ** (a_l - (a_l - lo_l) / factor)
        new_hi = 10 ** (a_l + (hi_l - a_l) / factor)
        return _clamp(new_lo, new_hi)

    new_lo = anchor - (anchor - lo) / factor
    new_hi = anchor + (hi - anchor) / factor
    return _clamp(new_lo, new_hi)


# ── normalize_zoom_step ──────────────────────────────────────────────────────


def normalize_zoom_step(value: float) -> float:
    """Нормализовать шаг зума из настроек.

    Диапазон валидации: ``(1.0, 5.0]``.  Вне диапазона — откат на
    :data:`DEFAULT_ZOOM_STEP` (1.2); предупреждение в лог делает вызывающий.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_ZOOM_STEP
    if v > 1.0 and v <= 5.0 and v == v:  # NaN check (v==v)
        return v
    return DEFAULT_ZOOM_STEP


# ── pan_lims ────────────────────────────────────────────────────────────────


def pan_lims(
    lim: tuple[float, float],
    delta_fraction: float,
    *,
    log: bool = False,
) -> tuple[float, float]:
    """Сдвинуть диапазон на долю его ширины (панорамирование).

    ``delta_fraction > 0`` — сдвиг вправо/вверх; ``< 0`` — влево/вниз.
    Ширина диапазона сохраняется.

    Лог-ветка: сдвиг реализуется через умножение на ``10**(width_l * d)``,
    где ``width_l`` — ширина в декадах.  Активируется при ``log=True`` и
    ``lo > 0, hi > 0``.
    """
    lo, hi = float(lim[0]), float(lim[1])
    if lo == hi:
        return (lo, hi)

    if log and lo > 0 and hi > 0:
        lo_l = math.log10(lo)
        hi_l = math.log10(hi)
        d_l = (hi_l - lo_l) * delta_fraction
        scale = 10 ** d_l
        return (lo * scale, hi * scale)

    width = hi - lo
    delta = width * delta_fraction
    return (lo + delta, hi + delta)


# ── anchor_fraction / value_at_fraction ─────────────────────────────────────


def anchor_fraction(anchor: float, lims: tuple[float, float]) -> float:
    """Доля ``anchor`` в диапазоне ``lims`` (0.0 — ``lo``, 1.0 — ``hi``).

    Линейная интерполяция; при вырожденном диапазоне (``lo == hi``)
    возвращает 0.5.
    """
    lo, hi = float(lims[0]), float(lims[1])
    if hi == lo:
        return 0.5
    return (anchor - lo) / (hi - lo)


def value_at_fraction(fraction: float, lims: tuple[float, float]) -> float:
    """Значение по доле ``fraction`` в диапазоне ``lims``.

    Обратная функция к :func:`anchor_fraction`; линейная интерполяция.
    """
    lo, hi = float(lims[0]), float(lims[1])
    return lo + (hi - lo) * fraction


# ── modifier detection (Qt events) ─────────────────────────────────────────


def modifier_mode(event) -> ModifierMode:
    """Разобрать модификаторы колеса мыши из ``scroll_event.guiEvent``.

    Если ``guiEvent`` отсутствует (синтетические события, offscreen)
    или модификаторы неизвестны → ``ZOOM_XY`` (поведение по умолчанию).

    Returns:
        ``ZOOM_X`` — Ctrl, ``ZOOM_Y`` — Ctrl+Shift,
        ``PAN_X`` — Shift, ``NONE`` — ``event.inaxes is None``,
        ``ZOOM_XY`` — без модификаторов.
    """
    if getattr(event, "inaxes", None) is None:
        return ModifierMode.NONE

    gui = getattr(event, "guiEvent", None)
    if gui is None:
        return ModifierMode.ZOOM_XY

    try:
        from PyQt6.QtCore import Qt

        def _mask(flag):
            return getattr(flag, "value", flag) if not isinstance(flag, int) else flag

        m = _mask(gui.modifiers())
        ctrl_m = _mask(Qt.KeyboardModifier.ControlModifier)
        shift_m = _mask(Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(m & ctrl_m)
        shift = bool(m & shift_m)
    except (AttributeError, TypeError):
        return ModifierMode.ZOOM_XY

    if ctrl and shift:
        return ModifierMode.ZOOM_Y
    if ctrl:
        return ModifierMode.ZOOM_X
    if shift:
        return ModifierMode.PAN_X
    return ModifierMode.ZOOM_XY


# ── categorical axis detection ──────────────────────────────────────────────


def is_categorical_axis(ax, which: str = "x") -> bool:  # pragma: no cover
    """Проверить, является ли ось категориальной (matplotlib StrCategory).

    ``which``: ``'x'`` или ``'y'``.

    Модуль zoom_math не импортирует matplotlib; детекция идёт через строковое
    имя класса локатора, что безопасно и не зависит от версии.
    """
    try:
        axis = ax.xaxis if which == "x" else ax.yaxis
        return type(axis.get_major_locator()).__name__ == _STR_CATEGORY_LOCATOR
    except AttributeError:
        return False
