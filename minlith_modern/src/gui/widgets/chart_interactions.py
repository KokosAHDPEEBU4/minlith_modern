"""Реестр спецификаций взаимодействий диаграмм.

Единственное место, где тип диаграммы (``type_id``) связывается с категорией
и набором разрешённых взаимодействий (зум, пан, rect-zoom, hover, клик).
Плитка и сетка никогда не содержат ветвлений по типу — они запрашивают
спецификацию только через этот реестр.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "ChartCategory",
    "InteractionSpec",
    "get_spec",
    "resolve_type_id",
    "BUILTIN_TYPE_IDS",
    "MIN_RANGE_WIDTH_DEFAULT",
]

MIN_RANGE_WIDTH_DEFAULT = 1e-12

# Настройки проекта: ключ шага зума (Этап 2). Для Этапа 1 дефолт не меняется.
ZOOM_STEP_DEFAULT = 1.2


class ChartCategory(Enum):
    """Категория диаграммы по матрице взаимодействий."""

    DECARTESIAN = "A"  # декартовы, обе оси числовые
    CATEGORY_AXIS = "B"  # декартовы с категориальной осью
    EQUAL_ASPECT = "C"  # равноаспектные / тройные / классификационные
    PIE = "D"  # круговые
    HEATMAP = "E"  # тепловые / матричные
    POLAR = "B_POLAR"  # полярный частный случай (radar)


@dataclass(frozen=True)
class InteractionSpec:
    """Неизменяемое описание возможностей взаимодействия типа диаграммы.

    Инварианты:
    - ``zoom_xy`` — колесо зумит обе оси к якорю;
    - ``zoom_x`` / ``zoom_y`` — колесо зумит только соответствующую ось;
    - ``pan`` — доступно панорамирование;
    - ``rect_zoom`` — доступно выделение области;
    - ``resettable`` — доступен сброс «По умолчанию»;
    - ``hover_info`` / ``click_action`` — подсказка / действие по клику;
    - ``sync_group`` — ключ синхронизации (``None`` — не участвует);
    - ``default_limits`` — пределы сброса, отличные от autoscale;
    - ``min_range_width`` — лимит зума по абсолютной ширине диапазона.
    """

    category: ChartCategory
    zoom_xy: bool = True
    zoom_x: bool = True
    zoom_y: bool = True
    pan: bool = True
    rect_zoom: bool = True
    resettable: bool = True
    hover_info: bool = False
    click_action: bool = False
    sync_group: str | None = None
    default_limits: tuple[float, float] | None = None
    min_range_width: float = MIN_RANGE_WIDTH_DEFAULT
    min_range_fraction: float | None = None

    @property
    def supports_zoom(self) -> bool:
        """Есть хотя бы одна зум-способность (кнопки «Приблизить/Отдалить»)."""
        return self.zoom_xy or self.zoom_x or self.zoom_y


# Порядок соответствует порядку BUILTIN_CHARTS (см. Приложение А SPEC).
BUILTIN_TYPE_IDS: tuple[str, ...] = (
    "bar",
    "pie",
    "defect",
    "a_cn_k",
    "heatmap",
    "rock_type",
    "box_plot",
    "pca_biplot",
)


def _cat_bar_tiered(sync: str | None) -> InteractionSpec:
    """Категория B: колесо/rect-зум только по числовой оси Y."""
    return InteractionSpec(
        category=ChartCategory.CATEGORY_AXIS,
        zoom_xy=False,
        zoom_x=False,
        zoom_y=True,
        sync_group=sync,
    )


def _cat_equal_aspect(sync: str | None, min_range_fraction: float | None = None) -> InteractionSpec:
    """Категория C: зум единым фактором обеих осей (равный аспект)."""
    return InteractionSpec(
        category=ChartCategory.EQUAL_ASPECT,
        zoom_xy=True,
        zoom_x=False,
        zoom_y=False,
        sync_group=sync,
        min_range_fraction=min_range_fraction,
    )


SPECS: dict[str, InteractionSpec] = {
    "bar": _cat_bar_tiered("bar-y"),
    "pie": InteractionSpec(
        category=ChartCategory.PIE,
        zoom_xy=False,
        zoom_x=False,
        zoom_y=False,
        pan=False,
        rect_zoom=False,
        resettable=True,
        hover_info=True,
        click_action=True,
    ),
    "defect": _cat_bar_tiered("bar-y"),
    "a_cn_k": _cat_equal_aspect("ternary-100"),
    "heatmap": InteractionSpec(
        category=ChartCategory.HEATMAP,
        hover_info=True,
        sync_group="samples",
    ),
    "rock_type": _cat_bar_tiered("bar-y"),
    "box_plot": _cat_bar_tiered("bar-y"),
    "pca_biplot": InteractionSpec(
        category=ChartCategory.DECARTESIAN,
        hover_info=True,
        sync_group="pca",
    ),
}

def _validate_registry() -> None:
    """Стартовая проверка реестра: все 8 type_id определены и уникальны."""
    expected_len = 8
    if len(BUILTIN_TYPE_IDS) != expected_len:
        raise AssertionError(
            f"Ожидалось {expected_len} встроенных диаграмм, получено {len(BUILTIN_TYPE_IDS)}"
        )
    if len(set(BUILTIN_TYPE_IDS)) != expected_len:
        raise AssertionError("BUILTIN_TYPE_IDS содержит дубликаты")
    missing = [tid for tid in BUILTIN_TYPE_IDS if tid not in SPECS]
    extra = [tid for tid in SPECS if tid not in set(BUILTIN_TYPE_IDS)]
    if missing:
        raise AssertionError(f"Нет спецификации для type_id: {missing}")
    if extra:
        raise AssertionError(f"Лишние type_id в SPECS: {extra}")


_validate_registry()


def get_spec(type_id: str) -> InteractionSpec:
    """Вернуть спецификацию по ``type_id``; неизвестный — ``KeyError``."""
    try:
        return SPECS[type_id]
    except KeyError:
        raise KeyError(f"Неизвестный type_id диаграммы: {type_id!r}") from None


def resolve_type_id(idx: int) -> str:
    """Вернуть ``type_id`` по индексу в ``BUILTIN_CHARTS`` (позиционный маппинг).

    Неизвестный индекс — ``ValueError`` (не молчаливый fallback).
    """
    if not (0 <= idx < len(BUILTIN_TYPE_IDS)):
        raise ValueError(f"Диаграмма с индексом {idx} отсутствует в реестре")
    return BUILTIN_TYPE_IDS[idx]
