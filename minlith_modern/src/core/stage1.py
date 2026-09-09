"""Stage 1 — второстепенные минералы (теория, файл 01).

Порядок: Ap → Py → Gp → Fl → Hl. Чистая стехиометрия, без эмпирики.

Вход: dict с молями оксидов (после пересчёта из вес.%).
Выход: (minerals, residuals) — минералы и остаточные пулы.

Ключевое отличие от VBA-порта: F не корректируется через P₂O₅ —
F и P₂O₅ считаются независимыми элементами (файл 01, раздел про апатит).
"""

from __future__ import annotations

from typing import Optional

from src.core.debug_tracer import DebugTraceCollector


def stage1(
    fe: dict[str, float],
    tracer: Optional[DebugTraceCollector] = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Стадия 1: Ap → Py → Gp → Fl → Hl.

    Args:
        fe: моли оксидов (после пересчёта из вес.%, ключи как в OXIDE_ORDER).
        tracer: коллектор отладочного trace.

    Returns:
        (minerals, residuals) — минералы и остаточные пулы.
    """
    out = {
        "ap": 0.0,  # Apatite
        "py": 0.0,  # Pyrite
        "gy": 0.0,  # Gypsum
        "fl": 0.0,  # Fluorite
        "hl": 0.0,  # Halite
    }
    res = dict(fe)

    def _get(key: str) -> float:
        return float(res.get(key, 0.0))

    # 1. Апатит: n(Ap) = n(P2O5), расход CaO = 3.33 * P2O5
    ap = _get("p2o5")
    out["ap"] = ap
    res["cao"] = _get("cao") - 3.33 * ap
    res["p2o5"] = 0.0
    if tracer:
        tracer.record("Stage1", "Ap", ap, "Ap = P2O5")

    # 2. Пирит: n(Py) = n(S) / 2, расход FeO = n(Py)
    py = _get("s") / 2.0
    out["py"] = py
    res["feo"] = _get("feo") - py
    res["s"] = 0.0
    if tracer:
        tracer.record("Stage1", "Py", py, "Py = S/2")

    # 3. Гипс: n(Gp) = n(SO3), расход CaO = n(SO3)
    gy = _get("so3")
    out["gy"] = gy
    res["cao"] = _get("cao") - gy
    res["so3"] = 0.0
    if tracer:
        tracer.record("Stage1", "Gy", gy, "Gy = SO3")

    # 4. Флюорит: n(Fl) = n_ост(F) / 2, расход CaO = n(Fl)
    fl = _get("f") / 2.0
    out["fl"] = fl
    res["cao"] = _get("cao") - fl
    res["f"] = 0.0
    if tracer:
        tracer.record("Stage1", "Fl", fl, "Fl = F/2")

    # 5. Галит: n(Hl) = n(Cl) / 2, расход Na2O = n(Hl)
    hl = _get("cl") / 2.0
    out["hl"] = hl
    res["na2o"] = _get("na2o") - hl
    res["cl"] = 0.0
    if tracer:
        tracer.record("Stage1", "Hl", hl, "Hl = Cl/2")

    return out, res
