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
        id="type3.d180",
        title="Тип 3: хлорит Fe-путь 3332a / иначе (d180)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="3332a", title="3332a (chl по Al)",
                       condition="C180 > 0", source="p_181t"),
            BranchInfo(id="no_3332a", title="без 3332a (3332b / p_196)",
                       condition="C180 <= 0", source=""),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.d200",
        title="Тип 3: Fe-путь 3333a / 3333b (d200)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="3333a", title="3333a (ill = fe3_1)",
                       condition="C200 < 0", source="p_201t"),
            BranchInfo(id="3333b", title="3333b (ill = k/2)",
                       condition="C200 >= 0", source="p_215t"),
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
    specs.append(DecisionSpec(
        id="type2.an",
        title="Тип 2: анортит по Na / Ca / Na(I)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="an=0.2na", title="an = 0.2Na",
                       condition="Ca >= 0.2*Na", source="D192"),
            BranchInfo(id="an=ca", title="an = Ca",
                       condition="0 < Ca < 0.2*Na", source="D199"),
            BranchInfo(id="an=0.2na(I)", title="an = 0.2Na (I)",
                       condition="Ca <= 0", source="s_198an"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type2.fe_ill",
        title="Тип 2: иллит по Fe / по Mg (s_221)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="fe-ill", title="fe-ill (Ill по Fe)",
                       condition="Mg - Fe3 >= 0", source="s_221t"),
            BranchInfo(id="fe-ill-mg", title="fe-ill-mg (Ill по Mg)",
                       condition="Mg - Fe3 < 0", source="s_230"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.p_142",
        title="Тип 3: ill = mg (p_142) / иначе",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="p_142", title="p_142 (ill = mg)",
                       condition="C90 < 0", source="p_142"),
            BranchInfo(id="no_p_142", title="без p_142 (ill = k/2)",
                       condition="C90 >= 0", source=""),
        ),
    ))
    specs.append(DecisionSpec(
        id="type2.s204",
        title="Тип 2: s_208 / s_271 (s_204)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="s208", title="s_208 (анортит по Ca)",
                       condition="si_2 - (11.5k+2al_1)/2.25 >= 0", source="s_204"),
            BranchInfo(id="s271", title="s_271 (ill-gb)",
                       condition="иначе", source="s_271"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type2.ill_or",
        title="Тип 2: ill+or / Fe-иллит (s_213)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="ill+or", title="ill+or (s_213t)",
                       condition="Fe3-ill_a>0 и Mg-ill_a>0", source="s_213t"),
            BranchInfo(id="no_ill_or", title="без ill+or (Fe-иллит)",
                       condition="иначе", source="s_221"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.d162",
        title="Тип 3: Fe-путь 3331 / иначе (d162)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="3331", title="3331 (ill = fe3_1-k2·chl)",
                       condition="C162 > 0", source="p_163t"),
            BranchInfo(id="no_3331", title="без 3331 (ill = k/2)",
                       condition="C162 <= 0", source="p_176t"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.d188",
        title="Тип 3: Fe-путь 3332b / p_196 (d188)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="3332b", title="3332b (chl по Fe)",
                       condition="C188 < 0", source="p_189t"),
            BranchInfo(id="no_3332b", title="без 3332b (p_196)",
                       condition="C188 >= 0", source="p_196"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.p_53",
        title="Тип 3: редкая плагиоклазовая p_53t / иначе",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="p_53t", title="p_53t (редкая ветка D51&D53)",
                       condition="C50≥0, C51<0, C52<0, C53<0", source="p_53t"),
            BranchInfo(id="no_p_53", title="без p_53t (обычный путь)",
                       condition="иначе", source=""),
        ),
    ))
    specs.append(DecisionSpec(
        id="type3.p_97",
        title="Тип 3: Mg-путь D106 / D109-fe / p_253 (p_97)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="D106", title="D106 (rVI)",
                       condition="C100>=0 и C101>=0", source="D106"),
            BranchInfo(id="D109-fe", title="D109-fe (Fe-путь)",
                       condition="C100 < 0", source="D109"),
            BranchInfo(id="p253->t5", title="p_253 -> t5",
                       condition="иначе", source="D112"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d334",
        title="Типы 4/5: mm-путь (d334) / иначе",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="mm-path", title="mm-путь (D334)",
                       condition="C333>0 и C334<=0", source="m_334t"),
            BranchInfo(id="no_mm", title="без mm (m_346/m_360)",
                       condition="иначе", source=""),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d346",
        title="Типы 4/5: m_346t / m_360 (d346)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="m_346", title="m_346t",
                       condition="C333 <= 0", source="m_346t"),
            BranchInfo(id="m_360", title="m_360",
                       condition="иначе", source="m_360"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type1.t_73",
        title="Тип 1: t_74t / t_78 (после t_67)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="t_74t", title="t_74t (kn=si_r/2)",
                       condition="al_r - si_r >= 0", source="t_73/74"),
            BranchInfo(id="t_78", title="t_78 (kn=al_r)",
                       condition="al_r - si_r < 0", source="t_78/79"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d287",
        title="Типы 4/5: m_287t / m_334 (d287)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="m287", title="m_287t", condition="C287 > 0", source="d287"),
            BranchInfo(id="m334", title="m_334", condition="C287 <= 0", source="m_334"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d302",
        title="Типы 4/5: m_302t / m_311 (d302)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="m302", title="m_302t", condition="Ca - 0.2*ab >= 0", source="d302"),
            BranchInfo(id="m311", title="m_311", condition="иначе", source="m_311"),
        ),
    ))
    specs.append(DecisionSpec(
        id="type45.d322",
        title="Типы 4/5: m_322t / m_296 (d322)",
        stage="type",
        overridable=True,
        branches=(
            BranchInfo(id="m322", title="m_322t (mm=Na)", condition="mg0-2Na > 0", source="d322"),
            BranchInfo(id="m296", title="m_296", condition="иначе", source="m_296"),
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
