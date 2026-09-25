"""Статический каталог решений движка excel_parity.

Единый источник вершин (решений) и веток графа разветвлений MINLITH.
Используется для визуализации маршрута (GUI) и валидации ручного выбора
ветки (``branch_overrides.validate_overrides``). Модуль чистый — без Qt.

Слои решений (см. ``docs/planning/BRANCH_GRAPH_SELECTION.md``):
  * ``coefficient_band`` — полоса коэффициентов k1..k4/achl (стадия 0);
  * ``rock_type`` — тип породы 1..5 (стадия 0);
  * ``stage_vi`` — этап VI (распределение Ca/Mg/Fe/Mn);
  * ``type12.*`` / ``type3.*`` / ``type45.*`` — заготовки внутренних
    решений типов (этап 6), ``overridable=False``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.excel_parity.branches import (
    COEFFICIENT_BAND_INFO,
    ROCK_TYPE_INFO,
    STAGE_VI_INFO,
    TYPE_BRANCH_INFO,
)


@dataclass(frozen=True)
class BranchInfo:
    """Одна ветка решения (вариант исхода)."""

    id: str                 # идентификатор ветки ("H5", "3", "A", "t_67"…)
    title: str              # человекочитаемая подпись
    condition: str = ""     # условие выбора ветки
    source: str = ""        # источник в Excel (ячейка/флаг/процедура)


@dataclass(frozen=True)
class DecisionSpec:
    """Вершина графа: решение и его возможные ветки."""

    id: str                     # "coefficient_band", "rock_type", "stage_vi"…
    title: str                  # человекочитаемое название
    stage: str                  # "stage0" | "type" | "stage_vi"
    overridable: bool           # можно ли выбрать ветку вручную
    branches: tuple[BranchInfo, ...] = field(default_factory=tuple)


def _band_branch(bid: str) -> BranchInfo:
    cond, src = COEFFICIENT_BAND_INFO[bid]
    return BranchInfo(id=bid, title=bid, condition=cond, source=src)


def _rock_branch(n: int) -> BranchInfo:
    cond, src = ROCK_TYPE_INFO[n]
    return BranchInfo(id=str(n), title=f"Тип {n}", condition=cond, source=src)


def _vi_branch(bid: str) -> BranchInfo:
    cond, src = STAGE_VI_INFO[bid]
    return BranchInfo(id=bid, title=bid, condition=cond, source=src)


def _type_branch(key: str) -> BranchInfo:
    cond, src = TYPE_BRANCH_INFO[key]
    return BranchInfo(id=key, title=key, condition=cond, source=src)


# Заготовки внутренних решений типов (этап 6). Группировка веток будет
# уточнена при реализации override; id веток = подписи TYPE_BRANCH_INFO.
_TYPE_STUBS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("type12.plagioclase", "Типы 1–2: распределение плагиоклаза",
     ("t_52~53", "t_58", "t_67", "t_83", "an=0.2na", "an=0.2na(I)",
      "an=ca", "D61", "D68")),
    ("type12.illite", "Типы 1–2: распределение иллита",
     ("ill-kz (D177-D179)", "ill+or", "ill-gb (D274)", "fe-ill",
      "fe-ill-mg", "p_53t", "p_142")),
    ("type3.chlorite", "Тип 3: распределение хлорита",
     ("F119+", "F126-", "3331", "3332a", "3332b", "3333a", "3333b",
      "s_271")),
    ("type3.exit", "Тип 3: переход в тип 5",
     ("p253->t5", "t5")),
    ("type45.route", "Типы 4/5: Fe-путь",
     ("t45-aType5", "t45-m504", "t45-m513->t5", "t45-m552t->t5",
      "t45-m418t", "t45-m424->t5", "type45-normal", "D106")),
)


def _build_catalog() -> dict[str, DecisionSpec]:
    band = tuple(_band_branch(bid) for bid in COEFFICIENT_BAND_INFO)
    rock = tuple(_rock_branch(n) for n in sorted(ROCK_TYPE_INFO))
    vi = tuple(_vi_branch(bid) for bid in STAGE_VI_INFO)

    specs = [
        DecisionSpec(
            id="coefficient_band",
            title="Полоса коэффициентов k1..k4/achl",
            stage="stage0",
            overridable=True,
            branches=band,
        ),
        DecisionSpec(
            id="rock_type",
            title="Тип породы",
            stage="stage0",
            overridable=True,
            branches=rock,
        ),
        DecisionSpec(
            id="stage_vi",
            title="Этап VI (Ca/Mg/Fe/Mn)",
            stage="stage_vi",
            overridable=True,
            branches=vi,
        ),
    ]
    for dec_id, title, keys in _TYPE_STUBS:
        specs.append(DecisionSpec(
            id=dec_id,
            title=title,
            stage="type",
            overridable=False,
            branches=tuple(_type_branch(k) for k in keys),
        ))
    # Этап 6: переопределяемые внутренние решения (однозначные бинарные).
    specs.append(DecisionSpec(
        id="type3.p_114",
        title="Тип 3: хлорит по Al / по Mg (p_114)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="F119+", title="F119+ (хлорит по Al)",
                       condition="E119 >= 0", source="p_119t"),
            BranchInfo(id="F126-", title="F126- (хлорит по Mg)",
                       condition="E119 < 0", source="p_126"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d418",
        title="Типы 4/5: Fe-путь m_418t / m_424 (d418)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="t45-m418t", title="m_418t (Fe-путь p_201)",
                       condition="0.2*Na - Ca >= 0", source="d418"),
            BranchInfo(id="t45-m424->t5", title="m_424 (тип 5)",
                       condition="0.2*Na - Ca < 0", source="m_424"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type1.t_49",
        title="Тип 1: an/kn/gb (t_49)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="t_52~53", title="t_52~53",
                       condition="al1 <= ca и Si хватает", source="t_52/t_53"),
            BranchInfo(id="t_58", title="t_58",
                       condition="al1 <= ca, Si не хватает", source="t_58"),
            BranchInfo(id="t_67", title="t_67",
                       condition="al1 > ca и Si хватает", source="t_67"),
            BranchInfo(id="t_83", title="t_83",
                       condition="al1 > ca, Si не хватает", source="t_83"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.d61",
        title="Тип 3: анортит D61 / D68",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="D61", title="D61 (an = 0.2Na)",
                       condition="c60 >= 0 и c61 >= 0", source="p_61t"),
            BranchInfo(id="D68", title="D68 (an = Ca)",
                       condition="иначе", source="p_68"),
        ),
    ))
    return {s.id: s for s in specs}


DECISIONS: dict[str, DecisionSpec] = _build_catalog()


def find_decision(decision_id: str) -> DecisionSpec:
    """Вернуть ``DecisionSpec`` по id; при отсутствии — ``KeyError``."""
    try:
        return DECISIONS[decision_id]
    except KeyError:
        raise KeyError(
            f"решение {decision_id!r} отсутствует в каталоге; "
            f"доступны: {sorted(DECISIONS)}"
        ) from None


def branch_ids(decision_id: str) -> tuple[str, ...]:
    """Идентификаторы всех веток решения (в порядке каталога)."""
    return tuple(b.id for b in find_decision(decision_id).branches)


def catalog_to_dict() -> dict:
    """Каталог в виде dict (для GUI и экспорта JSON)."""
    return {
        "decisions": [
            {
                "id": s.id,
                "title": s.title,
                "stage": s.stage,
                "overridable": s.overridable,
                "branches": [
                    {"id": b.id, "title": b.title,
                     "condition": b.condition, "source": b.source}
                    for b in s.branches
                ],
            }
            for s in DECISIONS.values()
        ]
    }
