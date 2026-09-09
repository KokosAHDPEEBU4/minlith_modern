"""Stage 2 — алюмосодержащие минералы и классификация типов пород.

Теория, файлы 02 (и индикатор R из файла 02, раздел 1.1).

Порядок: Or → Ab → An → Ilt → Kln → Chl → Gbs.
K2O делится между Or и Ilt через коэффициент k_or (долю K, идущую в
ортоклаз). Значения k_or по типам пород — эмпирические, ТРЕБУЮТ КАЛИБРОВКИ
(см. план).
"""

from __future__ import annotations

from typing import Optional

from src.core.debug_tracer import DebugTraceCollector

# Доля K2O, идущая в ортоклаз (не в иллит) по типу породы.
# Значения — начальные рекомендации из плана, требуют калибровки.
K_OR_BY_TYPE: dict[int, float] = {
    1: 1.0,  # Кварцевый песчаник — K в полевом шпате
    2: 0.7,  # Аркоз — большая часть K в полевом шпате
    3: 0.5,  # Граувака — поровну
    4: 0.2,  # Глины — большая часть K в иллите
    5: 0.1,  # Латериты — почти весь K в иллите
}

# Пороги индикатора R = Al2O3/(Na2O+K2O+CaO) для классификации типа.
# Эмпирические, ТРЕБУЮТ КАЛИБРОВКИ (файл 02).
R_THRESHOLDS: list[float] = [1.0, 1.5, 2.5, 5.0]


def classify_rock_type(al: float, na: float, k: float, ca: float) -> int:
    """Классификация типа породы 1-5 по индикатору R.

    R = Al2O3 / (Na2O + K2O + CaO)  — все величины в молях (после стадии 1).
    Высокое R → избыток Al₂O₃ (глины, латериты); низкое → избыток щелочей.
    """
    denom = na + k + ca
    if denom <= 1e-12:
        return 5 if al > 1e-12 else 1
    R = al / denom
    if R < R_THRESHOLDS[0]:
        return 1
    if R < R_THRESHOLDS[1]:
        return 2
    if R < R_THRESHOLDS[2]:
        return 3
    if R < R_THRESHOLDS[3]:
        return 4
    return 5


def k_or_for_type(rock_type: int) -> float:
    """Доля K2O в ортоклазе для данного типа породы."""
    return K_OR_BY_TYPE.get(rock_type, 0.5)


def _clamp(x: float) -> float:
    return max(x, 0.0)


def stage2(
    fe: dict[str, float],
    rock_type: int,
    k_or: float,
    tracer: Optional[DebugTraceCollector] = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Стадия 2: Or → Ab → An → Ilt → Kln → Chl → Gbs.

    Args:
        fe: остаточные пулы (моли) после стадии 1.
        rock_type: тип породы 1-5 (для хлорита/иллита и расчёта k_or).
        k_or: доля K2O, идущая в ортоклаз.
        tracer: коллектор trace.

    Returns:
        (minerals, residuals) — минералы и остаточные пулы.
    """
    al = fe["al2o3"]
    na = fe["na2o"]
    k = fe["k2o"]
    ca = fe["cao"]
    si = fe["sio2"]
    mg = fe["mgo"]
    feo = fe["feo"]

    out = {
        "or": 0.0,  # Orthoclase
        "ab": 0.0,  # Albite
        "an": 0.0,  # Anorthite
        "ilt": 0.0,  # Illite
        "kln": 0.0,  # Kaolinite
        "chl": 0.0,  # Chlorite
        "gbs": 0.0,  # Gibbsite
    }

    # 1. Ортоклаз: (K2O)(Al2O3)(SiO2)6, доля K через k_or
    or_ = k_or * min(k, al)
    out["or"] = or_
    al -= or_
    si -= 6 * or_
    k -= or_
    if tracer:
        tracer.record("Stage2", "Or", or_, "Or = k_or*min(K,Al)")

    # 2. Альбит: (Na2O)(Al2O3)(SiO2)6
    ab = min(na, al)
    out["ab"] = ab
    al -= ab
    si -= 6 * ab
    na -= ab
    if tracer:
        tracer.record("Stage2", "Ab", ab, "Ab = min(Na,Al)")

    # 3. Анортит: (CaO)(Al2O3)(SiO2)2
    an = min(ca, al)
    out["an"] = an
    al -= an
    si -= 2 * an
    ca -= an
    if tracer:
        tracer.record("Stage2", "An", an, "An = min(Ca,Al)")

    # 4. Иллит: (K2O)(Al2O3)3(SiO2)6, K — доля (1-k_or) от исходного K2O
    k_for_ill = (1.0 - k_or) * fe["k2o"]
    ilt = min(k_for_ill, al / 3.0, si / 6.0)
    out["ilt"] = ilt
    al -= 3 * ilt
    si -= 6 * ilt
    k -= ilt
    if tracer:
        tracer.record("Stage2", "Ilt", ilt, "Ilt = min((1-k_or)*K, Al/3, Si/6)")

    # 5. Каолинит: (Al2O3)(SiO2)2
    kln = min(al, si / 2.0)
    out["kln"] = kln
    al -= kln
    si -= 2 * kln
    if tracer:
        tracer.record("Stage2", "Kln", kln, "Kln = min(Al, Si/2)")

    # 6. Хлорит: ((MgO,FeO))5(Al2O3)(SiO2)3 — если остались Al и Si
    if al > 1e-9 and si > 1e-9 and (mg + feo) > 1e-9:
        chl = min(mg + feo, al) / 5.0
        out["chl"] = chl
        mg_used = mg if mg <= 5 * chl else 5 * chl
        fe_used = 5 * chl - mg_used
        mg -= mg_used
        feo -= fe_used
        al -= chl
        si -= 3 * chl
    if tracer:
        tracer.record("Stage2", "Chl", out["chl"], "Chl = min(Mg+Fe, Al)/5")

    # 7. Гиббсит: весь остаток Al2O3
    gbs = max(al, 0.0)
    out["gbs"] = gbs
    al -= gbs
    if tracer:
        tracer.record("Stage2", "Gbs", gbs, "Gbs = Al_ост")

    res = dict(fe)
    res.update(
        al2o3=al, na2o=na, k2o=k, cao=ca, sio2=si, mgo=mg, feo=feo,
    )
    return out, res
