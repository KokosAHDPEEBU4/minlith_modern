"""Type-specific calculation logic for MINLITH (Types 1-5, Stage VI).

VERIFIED from Excel Нач+Type 12 sheet:

Flow for Types 3-5:
  1. Ab = Na, Or = K
  2. Al1 = Al° - Ab, Si1 = Si° - 6*Ab
  3. An = f(Ca, Al1, Si1)
  4. Illite = min(K/2, al2/6.5, si2/16)
  5. Chlorite = min(mg/k1, fe/k2, (al2-6.5*ill)/k3, (si2-16*ill)/k4)
  6. Kn = remaining Al (can be negative)
  7. Q = remaining Si (Si4 - 2*Kn)

Consumption per formula unit:
  Mineral  │ K₂O  Al₂O₃  SiO₂  MgO  FeO  Na₂O  CaO  MnO
  ─────────┼───────────────────────────────────────────────
  Ab       │  —    1      6     —    —    1     —    —
  An       │  —    1      2     —    —    —     1    —
  Or       │  1    1      6     —    —    —     —    —
  Illite   │  2    6.5    16    1    1    —     —    —
  Chlorite │  —    k3     k4    k1   k2   —     —    —
  Kn       │  —    1      2     —    —    —     —    —
  Mm       │  —    5      24    2    —    1     —    2
  Gb       │  —    1      —     —    —    —     —    —
  Dl       │  —    —      —     1    —    —     1    —
  Ank      │  —    —      —     —    1    —     1    —
  Cc       │  —    —      —     —    —    —     1    —
  Sd       │  —    —      —     —    1    —     —    —
  Rch      │  —    —      —     —    —    —     —    1
  Srp      │  —    —      2     3    —    —     —    —
  Mst      │  —    —      —     1    —    —     —    —
  Ht       │  —    —      —     —    2    —     —    —
  Ap       │  —    —      —     —    —    —     3.36 —
  Prl      │  —    —      —     —    —    —     —    1
"""

from __future__ import annotations

import numpy as np

from src.core.debug_tracer import DebugTraceCollector
from src.core.models import (
    AdaptiveCoefficients,
    FormulaUnits,
    MineralComposition,
)


def _calc_an(al1: float, si1: float, ca: float) -> tuple[float, float, float]:
    """Calculate anorthite distribution.

    Returns (an, si_after, al_after).
    An consumes 1 Al₂O₃ and 2 SiO₂ per f.u.
    """
    an = 0.0
    si_out = si1
    if al1 <= ca:
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si_out = 0
    else:
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si_out = 0
    return an, si_out, al1 - an


def _calc_kn_gb(al_resid: float, si_resid: float) -> tuple[float, float, float]:
    """Calculate kaolinite + gibbsite from remaining Al, Si.

    Returns (kn, gb, si_after).
    Kn = Al₂O₃ (1 per f.u.), consumes 2 SiO₂ per f.u.
    Gb = excess Al₂O₃
    """
    kn = 0.0
    gb = 0.0
    si_after = si_resid
    if 2 * al_resid >= si_resid:
        kn = si_resid / 2
        gb = al_resid - kn
        si_after = 0
    else:
        kn = al_resid
        si_after = si_resid - 2 * kn
    return kn, gb, si_after


def calculate_type1(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Type 1: Al <= 1.2Na + K. Feldspars only."""
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao

    ab = na
    or_ = k

    si1 = si - 6 * ab
    al1 = al - ab

    an, si2, al2 = _calc_an(al1, si1, ca)
    kn, gb, si3 = _calc_kn_gb(al2, si2)
    q = max(si3, 0)

    if tracer:
        tracer.record("Type1", "ab", ab, "Ab = Na")
        tracer.record("Type1", "or_", or_, "Or = K")
        tracer.record("Type1", "an", an, "An")
        tracer.record("Type1", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, kn=kn, gb=gb, q=q)


def calculate_type2(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Type 2: Al <= 1.2Na + 3.25K. Feldspars + illite."""
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao

    ab = na
    or_ = k

    si1 = si - 6 * ab
    al1 = al - ab

    an, si2, al2 = _calc_an(al1, si1, ca)

    ill = 0.0
    if k > 0 and al2 > 0 and si2 > 0:
        ill = min(k / 2, al2 / 6.5, si2 / 16)
        si3 = si2 - 16 * ill
        al3 = al2 - 6.5 * ill
    else:
        si3 = si2
        al3 = al2

    kn, gb, si4 = _calc_kn_gb(al3, si3)
    q = max(si4, 0)

    if tracer:
        tracer.record("Type2", "ab", ab, "Ab = Na")
        tracer.record("Type2", "or_", or_, "Or = K")
        tracer.record("Type2", "an", an, "An")
        tracer.record("Type2", "ill", ill, "Ill")
        tracer.record("Type2", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, ill=ill, kn=kn, gb=gb, q=q)


def calculate_type3(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Type 3: Al <= 1.2Na + 3.25K + (Mg - 0.5K*k3)/k1.

    Illite → Chlorite → Kn/Gb → Q
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo  # fe2o3 is always 0 (already converted to feo in Stage 0)

    k1, k2, k3, k4 = coeff.k1, coeff.k2, coeff.k3, coeff.k4

    ab = na
    or_ = k

    si1 = si - 6 * ab
    al1 = al - ab

    an, si2, al2 = _calc_an(al1, si1, ca)

    ill = 0.0
    if k > 0 and al2 > 0 and si2 > 0:
        ill = min(k / 2, al2 / 6.5, si2 / 16)
        si3 = si2 - 16 * ill
        al3 = al2 - 6.5 * ill
    else:
        si3 = si2
        al3 = al2

    chl = 0.0
    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0 and al3 > 0 and si3 > 0:
        chl = min(mg / k1, fe / k2, al3 / k3, si3 / k4)
        chl = max(chl, 0)
        si4 = si3 - chl * k4
        al4 = al3 - chl * k3
    else:
        si4 = si3
        al4 = al3

    kn, gb, si5 = _calc_kn_gb(al4, si4)
    q = max(si5, 0)

    if tracer:
        tracer.record("Type3", "ab", ab, "Ab = Na")
        tracer.record("Type3", "or_", or_, "Or = K")
        tracer.record("Type3", "an", an, "An")
        tracer.record("Type3", "ill", ill, "Ill")
        tracer.record("Type3", "chl", chl, "Chl")
        tracer.record("Type3", "kn", kn, "Kn")
        tracer.record("Type3", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q)


def calculate_type4(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Type 4: Al <= 5Na + 3.25K + (Mg - 0.5K - 2Na)*k3/k1.

    Illite → Chlorite → Mm → Kn/Gb → Q
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo  # fe2o3 is always 0 (already converted to feo in Stage 0)

    k1, k2, k3, k4 = coeff.k1, coeff.k2, coeff.k3, coeff.k4

    ab = na
    or_ = k

    si1 = si - 6 * ab
    al1 = al - ab

    an, si2, al2 = _calc_an(al1, si1, ca)

    ill = 0.0
    if k > 0 and al2 > 0 and si2 > 0:
        ill = min(k / 2, al2 / 6.5, si2 / 16)
        si3 = si2 - 16 * ill
        al3 = al2 - 6.5 * ill
    else:
        si3 = si2
        al3 = al2

    chl = 0.0
    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0 and al3 > 0 and si3 > 0:
        chl = min(mg / k1, fe / k2, al3 / k3, si3 / k4)
        chl = max(chl, 0)
        si4 = si3 - chl * k4
        al4 = al3 - chl * k3
    else:
        si4 = si3
        al4 = al3

    mm = 0.0
    if na > 0 and al4 > 0 and si4 > 0:
        mm = min(al4 / 5, si4 / 24)
        si5 = si4 - 24 * mm
        al5 = al4 - 5 * mm
    else:
        si5 = si4
        al5 = al4

    kn, gb, si6 = _calc_kn_gb(al5, si5)
    q = max(si6, 0)

    if tracer:
        tracer.record("Type4", "ab", ab, "Ab = Na")
        tracer.record("Type4", "or_", or_, "Or = K")
        tracer.record("Type4", "an", an, "An")
        tracer.record("Type4", "ill", ill, "Ill")
        tracer.record("Type4", "chl", chl, "Chl")
        tracer.record("Type4", "mm", mm, "Mm")
        tracer.record("Type4", "kn", kn, "Kn")
        tracer.record("Type4", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q, mm=mm)


def calculate_type5(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Type 5: everything else (highest Al).

    Illite → Chlorite → Mm → Kn/Gb → Q
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo  # fe2o3 is always 0 (already converted to feo in Stage 0)

    k1, k2, k3, k4 = coeff.k1, coeff.k2, coeff.k3, coeff.k4

    ab = na
    or_ = k

    si1 = si - 6 * ab
    al1 = al - ab

    an, si2, al2 = _calc_an(al1, si1, ca)

    ill = 0.0
    if k > 0 and al2 > 0 and si2 > 0:
        ill = min(k / 2, al2 / 6.5, si2 / 16)
        si3 = si2 - 16 * ill
        al3 = al2 - 6.5 * ill
    else:
        si3 = si2
        al3 = al2

    chl = 0.0
    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0 and al3 > 0 and si3 > 0:
        chl = min(mg / k1, fe / k2, al3 / k3, si3 / k4)
        chl = max(chl, 0)
        si4 = si3 - chl * k4
        al4 = al3 - chl * k3
    else:
        si4 = si3
        al4 = al3

    mm = 0.0
    if na > 0 and al4 > 0 and si4 > 0:
        mm = min(al4 / 5, si4 / 24)
        si5 = si4 - 24 * mm
        al5 = al4 - 5 * mm
    else:
        si5 = si4
        al5 = al4

    kn, gb, si6 = _calc_kn_gb(al5, si5)
    q = max(si6, 0)

    if tracer:
        tracer.record("Type5", "ab", ab, "Ab = Na")
        tracer.record("Type5", "or_", or_, "Or = K")
        tracer.record("Type5", "an", an, "An")
        tracer.record("Type5", "ill", ill, "Ill")
        tracer.record("Type5", "chl", chl, "Chl")
        tracer.record("Type5", "mm", mm, "Mm")
        tracer.record("Type5", "kn", kn, "Kn")
        tracer.record("Type5", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q, mm=mm)


def stage_vi(
    fu: FormulaUnits,
    minerals: MineralComposition,
    fe: np.ndarray,
    coeff: AdaptiveCoefficients | None = None,
    tracer: DebugTraceCollector | None = None,
) -> MineralComposition:
    """Stage VI: Final distribution of remaining elements.

    Distributes Ca, Mg, Fe, Mn into carbonates, oxides, serpentine.
    Does NOT recalculate Q — Q is already set by the type function.
    """
    k1 = coeff.k1 if coeff else 1.0
    k2 = coeff.k2 if coeff else 1.0

    ca_an = minerals.an
    ca_ap = minerals.ap * 3.36
    ca_n = fu.cao - ca_an - ca_ap

    mg_chl = minerals.chl * k1
    mg_ill = minerals.ill
    mg_n = fu.mgo - mg_chl - mg_ill

    fe_total = fu.feo
    fe_chl = minerals.chl * k2
    fe_ill = minerals.ill
    fe_n = fe_total - fe_chl - fe_ill

    mn_n = fu.mno

    if tracer:
        tracer.record("StageVI", "ca_n", ca_n, "Ca residual")
        tracer.record("StageVI", "mg_n", mg_n, "Mg residual")
        tracer.record("StageVI", "fe_n", fe_n, "Fe residual")

    dl = 0.0
    ank = 0.0
    cc = 0.0
    rch = 0.0
    sd = 0.0
    srp = 0.0
    mst = 0.0
    ht = 0.0
    prl = mn_n
    q = minerals.q

    if ca_n >= mg_n + fe_n:
        dl = mg_n
        ank = fe_n
        cc = ca_n - dl - ank
        rch = mn_n
        if ca_n <= 250:
            ht = fe_n / 2
        else:
            sd = fe_n
    else:
        if ca_n < mg_n:
            dl = ca_n
            mg_n1 = mg_n - dl
            if mg_n1 > 0:
                srp = mg_n1 / 3
            ht = fe_n / 2
        else:
            dl = mg_n
            ca_n1 = ca_n - dl
            ank = ca_n1
            fe_n1 = fe_n - ank
            ht = fe_n1 / 2

    return MineralComposition(
        ab=minerals.ab, an=minerals.an, or_=minerals.or_,
        ill=minerals.ill, chl=minerals.chl, kn=minerals.kn,
        mm=minerals.mm, gb=minerals.gb,
        cc=cc, dl=dl, ank=ank, rch=rch, sd=sd,
        q=q, ap=minerals.ap, c=minerals.c,
        srp=srp, mst=mst, ht=ht, prl=prl,
        pr=minerals.pr, rt=minerals.rt,
        hl=minerals.hl, gy=minerals.gy, fl=minerals.fl,
    )
