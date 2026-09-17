"""Стандарты размеров отображения диаграмм.

Единственное место, где тип диаграммы (``type_id``) связывается с целевыми
пропорциями и ограничениями плитки. Плитка сетки запрашивает стандарт через
:func:`get_size_spec` и никогда не содержит ветвлений по типу.

Зачем это нужно: ``FigureCanvasQTAgg`` растягивает фигуру под размер виджета,
поэтому в режиме одной колонки диаграмма с «родной» пропорцией 4:3
растягивалась до, например, 4:1 и становилась нечитаемой. Стандарт задаёт
целевой аспект (ширина/высота) и максимальную ширину содержимого, а
:class:`~src.gui.widgets.chart_grid._ChartTile` держит канвас в этих рамках и
центрирует его.

Поля :class:`ChartSizeSpec`:

- ``aspect`` — целевой аспект (ширина/высота). ``None`` — взять «родной»
  аспект фигуры, зажатый в ``[min_aspect, max_aspect]``;
- ``max_width`` — предел ширины содержимого в логических пикселях (``None`` —
  заполнять ячейку целиком). Применяется для квадратных/радиальных/
  классификационных диаграмм, которым не нужна вся ширина окна;
- ``min_aspect`` / ``max_aspect`` — границы «родного» аспекта;
- ``min_height`` / ``max_height`` — границы высоты канваса.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ChartSizeSpec",
    "DEFAULT_SIZE_SPEC",
    "STANDARDS",
    "BUILTIN_SIZE_IDS",
    "aspect_for",
    "get_size_spec",
]


@dataclass(frozen=True)
class ChartSizeSpec:
    """Целевые пропорции и ограничения отображения диаграммы."""

    aspect: float | None = None
    max_width: int | None = None
    min_aspect: float = 0.75
    max_aspect: float = 2.6
    min_height: int = 240
    max_height: int = 1400


DEFAULT_SIZE_SPEC = ChartSizeSpec()

# Порядок соответствует BUILTIN_CHARTS / BUILTIN_TYPE_IDS.
BUILTIN_SIZE_IDS: tuple[str, ...] = (
    "bar",
    "pie",
    "defect",
    "qapf",
    "tas",
    "a_cn_k",
    "heatmap",
    "rock_type",
    "feldspar_triangle",
    "harker",
    "afm",
    "sio2_k2o",
    "bland_altman",
    "correlation",
    "k1_k4",
    "box_plot",
    "radar",
    "coefficient_heatmap",
    "defect_accumulation",
    "pca_biplot",
    "dendrogram",
    "parallel_coordinates",
    "mg_fe_al_ternary",
)

# ── Стандарты по типам ──────────────────────────────────────────────────────
# aspect   — целевой аспект; None → родной аспект фигуры (в границах ниже).
# max_width — предел ширины содержимого, px; None → на всю ширину ячейки.
STANDARDS: dict[str, ChartSizeSpec] = {
    # Групповые столбцы: число категорий = число образцов, допускаем ширину.
    "bar": ChartSizeSpec(max_aspect=2.6, max_width=1100),
    # Круговая: строго квадрат, не раздувается на всю ширину.
    "pie": ChartSizeSpec(aspect=1.0, max_width=620),
    # Отклонения по оксидам: умеренно широкие столбцы.
    "defect": ChartSizeSpec(max_aspect=2.6, max_width=900),
    # Классификационные/тройные: квадратные, ограниченная ширина.
    "qapf": ChartSizeSpec(aspect=1.0, max_width=620),
    "tas": ChartSizeSpec(aspect=1.35, max_width=780),
    "a_cn_k": ChartSizeSpec(aspect=1.0, max_width=620),
    # Тепловые карты: пропорции задаёт матрица (образцы × минералы/оксиды).
    "heatmap": ChartSizeSpec(max_aspect=2.4, max_width=1100),
    # Распределение типов пород: столбцы или круг, умеренная ширина.
    "rock_type": ChartSizeSpec(max_aspect=2.0, max_width=720),
    "feldspar_triangle": ChartSizeSpec(aspect=1.0, max_width=620),
    # Харкер: сетка подграфиков, допускаем ширину, но не «ленту».
    "harker": ChartSizeSpec(max_aspect=2.4, max_width=1100),
    "afm": ChartSizeSpec(aspect=1.0, max_width=620),
    "sio2_k2o": ChartSizeSpec(aspect=1.15, max_width=720),
    # Точечные диаграммы рассеяния: близки к квадрату.
    "bland_altman": ChartSizeSpec(aspect=1.35, max_width=760),
    "correlation": ChartSizeSpec(aspect=1.1, max_width=760),
    # Параметры K: фиксированная широкая фигура (10×6).
    "k1_k4": ChartSizeSpec(aspect=1.67, max_width=860),
    "box_plot": ChartSizeSpec(max_aspect=2.4, max_width=1100),
    # Полярные: квадрат.
    "radar": ChartSizeSpec(aspect=1.0, max_width=620),
    # Коэффициентная тепловая карта: намеренно низкая и широкая.
    "coefficient_heatmap": ChartSizeSpec(max_aspect=3.0, max_width=1100),
    "defect_accumulation": ChartSizeSpec(max_aspect=2.6, max_width=1100),
    "pca_biplot": ChartSizeSpec(aspect=1.25, max_width=820),
    "dendrogram": ChartSizeSpec(max_aspect=2.4, max_width=1100),
    "parallel_coordinates": ChartSizeSpec(max_aspect=2.6, max_width=1100),
    "mg_fe_al_ternary": ChartSizeSpec(aspect=1.0, max_width=620),
}


def _validate_standards() -> None:
    """Стартовая проверка: все 23 type_id покрыты и уникальны."""
    expected_len = 23
    if len(BUILTIN_SIZE_IDS) != expected_len:
        raise AssertionError(
            f"Ожидалось {expected_len} стандартов размеров, получено {len(BUILTIN_SIZE_IDS)}"
        )
    if len(set(BUILTIN_SIZE_IDS)) != expected_len:
        raise AssertionError("BUILTIN_SIZE_IDS содержит дубликаты")
    missing = [tid for tid in BUILTIN_SIZE_IDS if tid not in STANDARDS]
    extra = [tid for tid in STANDARDS if tid not in set(BUILTIN_SIZE_IDS)]
    if missing:
        raise AssertionError(f"Нет стандарта размера для type_id: {missing}")
    if extra:
        raise AssertionError(f"Лишние type_id в STANDARDS: {extra}")
    for tid, spec in STANDARDS.items():
        if spec.aspect is not None and spec.aspect <= 0:
            raise AssertionError(f"Некорректный aspect для {tid!r}: {spec.aspect}")
        if not (0 < spec.min_aspect <= spec.max_aspect):
            raise AssertionError(f"Некорректные границы аспекта для {tid!r}")
        if spec.min_height <= 0 or spec.max_height < spec.min_height:
            raise AssertionError(f"Некорректные границы высоты для {tid!r}")
        if spec.max_width is not None and spec.max_width <= 0:
            raise AssertionError(f"Некорректный max_width для {tid!r}: {spec.max_width}")


_validate_standards()


def get_size_spec(type_id: str | None) -> ChartSizeSpec:
    """Вернуть стандарт размера по ``type_id``.

    Неизвестный или ``None`` — общий :data:`DEFAULT_SIZE_SPEC` (без исключения:
    размерный слой не должен ронять рендер из-за нового типа без стандарта).
    """
    if type_id is None:
        return DEFAULT_SIZE_SPEC
    return STANDARDS.get(type_id, DEFAULT_SIZE_SPEC)


def aspect_for(spec: ChartSizeSpec, native_aspect: float | None) -> float:
    """Целевой аспект с учётом «родного» аспекта фигуры и границ стандарта.

    ``native_aspect`` — ширина/высота «родной» фигуры; ``None`` или
    некорректное значение игнорируется (берётся ``max_aspect``).
    """
    if spec.aspect is not None:
        return spec.aspect
    if native_aspect is None or native_aspect <= 0:
        return spec.max_aspect
    return max(spec.min_aspect, min(native_aspect, spec.max_aspect))
