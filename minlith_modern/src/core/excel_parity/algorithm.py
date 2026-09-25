"""Адаптер excel_parity к интерфейсу MineralAlgorithm.

Принимает :class:`AlgorithmInput` с формульными единицами оксидов и возвращает
:class:`AlgorithmOutput`: ф.е. минералов типов 1-5 и этапа VI + остатки.

Важно: фильтра f.e. — единственный источник истины. Коэффициенты k1..k4,
F, A и тип породы НЕ берутся из AlgorithmInput, а вычисляются движком из ф.е.
по полосам исходной книги: поля входа формируются легаси-Calculator'ом
(другие массы, округления F/A, состарившиеся формулы полос) и не согласованы
с excel_parity. Движок, как и книга MINLITH, сам выводит их из ф.е.
"""

from __future__ import annotations

from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.excel_parity.runner import ExcelRun, run_from_stage0
from src.core.excel_parity.stage0 import (
    Stage0,
    classify,
    classify_conditions,
    coefficient_band,
    coefficients,
    f_and_a,
)


def stage0_from_input(inp: AlgorithmInput) -> Stage0:
    """Строит стадию 0 из ф.е. AlgorithmInput (все производные — самодостаточно).

    Производные величины выводятся из ф.е. так же, как в ``stage0.compute``:
        D17  = S ф.е. (уже сумма S + SO3, как на листе);
        пирит pr0 = D17/2;  Fe после пирита = FeO* − pr0;
        Ca для стадий = max(D8, 0);  D8 (raw) = D8 + 3.33·P2O5 + F/2;
        F, A, k1..k4, achl, rock_type — полосы книги (см. stage0.coefficients).
    """
    fe = {
        "SiO2": inp.sio2, "TiO2": inp.tio2, "Al2O3": inp.al2o3,
        "Fe2O3": 0.0, "FeO": inp.feo, "MgO": inp.mgo, "CaO": inp.cao,
        "Na2O": inp.na2o, "K2O": inp.k2o, "P2O5": inp.p2o5,
        "MnO": inp.mno, "C": inp.c, "SO3": inp.so3, "F": inp.f,
        "Cl": inp.cl, "S": inp.s, "CO2": inp.co2, "SO": inp.so,
    }
    overrides = inp.overrides
    band_override = overrides.get("coefficient_band") if overrides else None
    type_override = overrides.get("rock_type") if overrides else None
    f, a = f_and_a(fe)
    k1, k2, k3, k4, achl = coefficients(f, a, override=band_override)
    rock_type = classify(fe, k1, k3, override=type_override)
    s_total = fe["S"]
    pr0 = s_total / 2.0
    ca_raw = inp.cao + 3.33 * inp.p2o5 + 0.5 * inp.f
    return Stage0(
        fe=fe, F=f, A=a,
        k1=k1, k2=k2, k3=k3, k4=k4, achl=achl,
        rock_type=rock_type,
        ca_raw=ca_raw,
        pr0=pr0,
        fe3_1=fe["FeO"] - pr0,
        ca=inp.cao if inp.cao > 0.0 else 0.0,
        ca_n_in=inp.cao,
        s=s_total,
        coefficient_band=band_override or coefficient_band(f, a),
        type_conditions=classify_conditions(fe, k1, k3),
        overrides=inp.overrides,
    )


class ExcelParityAlgorithm:
    """Адаптер :class:`~src.core.algorithm.MineralAlgorithm` → excel_parity.

    Используется Calculator'ом как полноценный алгоритм расчёта минерального
    состава (replaceable для :class:`GeologicalTheoryAlgorithm`).
    """

    def __init__(self) -> None:
        self.last: ExcelRun | None = None

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        run = run_from_stage0(stage0_from_input(inp))
        self.last = run
        tsol, vi = run.tsol, run.vi
        return AlgorithmOutput(
            Ab=tsol.ab, An=tsol.an, Or=tsol.or_,
            Ill=tsol.ill, Chl=tsol.chl, Kn=tsol.kn,
            Mm=tsol.mm, Gb=tsol.gb, Q=vi.q,
            Dl=vi.dl, Ank=vi.ank, Cc=vi.cc, Rch=vi.rch,
            Sd=vi.sd, Srp=vi.srp, Mst=vi.mst, Ht=vi.ht, Prl=vi.prl,
            residuals={"ca_n": tsol.ca_n, "mg_n": tsol.mg_n,
                       "fe_n": tsol.fe_n, "si_n": tsol.si_n},
            path=run.path.to_dict(),
        )
