"""Этап VI: раскладка остатков Ca/Mg/Fe/Si на доломит-анкерит-карбонаты
и кварц-серпентин-магнезит во всех трёх ветках (A/B/C) листа «Нач+Type 12»
(строки 92-140), без округлений.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.clean_engine.stage0 import Stage0
from src.core.clean_engine.types import TypeSolution


@dataclass
class StageVI:
    """Минералы VI этапа (ф.е.)."""

    dl: float = 0.0    # доломит
    ank: float = 0.0   # анкерит
    cc: float = 0.0    # кальцит
    rch: float = 0.0   # родохрозит
    q: float = 0.0     # кварц
    sd: float = 0.0    # сидерит
    prl: float = 0.0   #    прe(..)
    srp: float = 0.0   # серпентин
    mst: float = 0.0   # магнезит
    ht: float = 0.0    # гётит/гематит

    trace: list[str] = field(default_factory=list)


def solve_stage_vi(st0: Stage0, tsol: TypeSolution) -> StageVI:
    """Выполняет VI этап по остаткам ca_n/mg_n/fe_n/si_n."""
    ca_n = tsol.ca_n
    mg_n = tsol.mg_n
    fe_n = tsol.fe_n
    si_n = tsol.si_n
    mn_fe = st0.fe["MnO"]
    vi = StageVI()

    # Ветка A: ca_n >= mg_n + fe_n (карбонатная щёлочноземельная)
    # Mn -> родохрозит (rch); в ветках B/C Mn -> prl.
    if ca_n - mg_n - fe_n >= 0.0:
        vi.dl = mg_n
        vi.ank = fe_n
        vi.cc = ca_n - vi.dl - vi.ank
        vi.rch = mn_fe
        vi.q = si_n
        vi.trace.append("A")
        return vi

    # Ветка B: mg_n <= ca_n < mg_n + fe_n
    if mg_n <= ca_n < mg_n + fe_n:
        vi.dl = mg_n
        vi.ank = ca_n - mg_n
        fe_left = fe_n - vi.ank
        vi.prl = mn_fe
        if ca_n - vi.dl <= 250.0:
            vi.ht = fe_left / 2.0
        else:
            vi.ht = fe_left
        vi.q = si_n
        vi.trace.append("B")
        return vi

    # Ветка C: ca_n - mg_n < 0
    if ca_n - mg_n < 0.0:
        vi.dl = ca_n
        c123 = mg_n - ca_n
        vi.prl = mn_fe
        if si_n - (2.0 / 3.0) * c123 > 0.0:
            vi.srp = c123 / 3.0
            vi.q = si_n - 2.0 * vi.srp
            vi.ht = fe_n / 2.0
            vi.trace.append("C-srp")
        elif si_n - c123 < 0.0:
            vi.q = si_n / 2.0
            vi.mst = c123 - 3.0 * vi.q
            vi.ht = fe_n / 2.0
            vi.trace.append("C-mst")
        elif si_n == 0.0:
            vi.srp = c123
            vi.ht = fe_n
            vi.trace.append("C-srp0")
        else:
            raise NotImplementedError(
                "Этап VI: ветка C (si_n>0, без остатка) не реализована."
            )
        return vi

    raise NotImplementedError("Этап VI: ни одна ветка A/B/C не сошлась.")
