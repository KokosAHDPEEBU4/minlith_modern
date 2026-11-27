"""Расчётный движок строго по теории (файлы 00-07).

GeologicalTheoryAlgorithm написан по теории из файлов 00-07: стадии 1→2→3
с классификацией типа породы по индикатору R и делением K₂O между
ортоклазом и иллитом (k_or).

Примечание по F: теория считает F и P₂O₅ независимыми элементами, поэтому
F «восстанавливается» из коррекции Stage 0 (которая вычитала 0.67×P₂O₅)
и весь направляется во флюорит. В Stage 0 при этом ничего не меняется.
"""

from __future__ import annotations

from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.stage1 import stage1
from src.core.stage2 import classify_rock_type, k_or_for_type, stage2
from src.core.stage3 import stage3

# Оксиды, которые учитываются в остаточных пулах.
_POOL_KEYS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]


def _build_pools(inp: AlgorithmInput) -> dict[str, float]:
    """Собрать пулы ф.е. из AlgorithmInput.

    Stage 0 в калькуляторе уже вычла апатит-CaO (3.36×P₂O₅), флюорит-F
    (0.67×P₂O₅) и галит-Na₂O (Cl/2). Для честной теории эти коррекции
    «откатываются», чтобы стадия 1 применила собственные правила из файла 01
    (Ap по 3.33×P₂O₅, Fl по полному F — независимо от P₂O₅).

    Примечание: fe2o3 в AlgorithmInput отсутствует — Stage 0 уже перевела
    его в feo (Fe₂O₃ × 0.9 + FeO), поэтому пул fe2o3 = 0.
    """
    pools = {k: float(getattr(inp, k)) for k in _POOL_KEYS if k != "fe2o3"}
    pools["fe2o3"] = 0.0
    # Откат коррекций Stage 0
    pools["cao"] += 3.36 * float(inp.p2o5)
    pools["f"] += 0.67 * float(inp.p2o5)
    pools["na2o"] += float(inp.cl) / 2.0
    return pools


class GeologicalTheoryAlgorithm:
    """Расчётный движок строго по теории (файлы 00-07).

    Этапы:
      1. Stage 1 — второстепенные минералы (Ap, Py, Gy, Fl, Hl).
      2. Классификация типа породы (индикатор R).
      3. Stage 2 — полевые шпаты, глины, гиббсит (с k_or).
      4. Stage 3 — карбонаты, оксиды, кварц.
    """

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        # 1. Stage 1: второстепенные минералы
        pools = _build_pools(inp)
        minerals_s1, pools = stage1(pools)

        # 2. Классификация типа породы
        rock_type = classify_rock_type(
            pools["al2o3"], pools["na2o"], pools["k2o"], pools["cao"],
        )
        k_or = k_or_for_type(rock_type)

        # 3. Stage 2: алюмосодержащие
        minerals_s2, pools = stage2(pools, rock_type, k_or)

        # 4. Stage 3: остаточные минералы (мутирует pools → residuals)
        minerals = {**minerals_s1, **minerals_s2}
        minerals = stage3(pools, minerals)

        # 5. Сборка результата
        out = AlgorithmOutput(
            Ab=minerals["ab"],
            An=minerals["an"],
            Or=minerals["or"],
            Ill=minerals["ilt"],
            Chl=minerals["chl"],
            Kn=minerals["kln"],
            Mm=0.0,
            Gb=minerals["gbs"],
            Q=minerals["qz"],
            Dl=minerals["dl"],
            Ank=0.0,
            Cc=minerals["cc"],
            Rch=minerals["rch"],
            Sd=minerals["sd"],
            Srp=0.0,
            Mst=0.0,
            Ht=minerals["ht"],
            Prl=0.0,
        )
        # Остаточные пулы = defect по теории
        out.residuals = pools
        return out
