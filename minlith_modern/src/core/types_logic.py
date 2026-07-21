"""Type-specific calculation logic for MINLITH (Types 1-5, Stage VI)."""

from __future__ import annotations

from typing import Optional

import numpy as np

from src.core.models import (
    AdaptiveCoefficients,
    FormulaUnits,
    MineralComposition,
)
from src.core.debug_tracer import DebugTraceCollector


def calculate_type1(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Type 1 calculation: Al <= 1.2Na + K.

    Feldspars only, no illite/chlorite.
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao

    # Ab = Na
    ab = na
    # Or = K
    or_ = k

    si1 = si - 6 * ab
    al1 = al - or_ - ab

    an = 0.0
    kn = 0.0
    gb = 0.0
    q = 0.0
    ill = 0.0
    chl = 0.0

    # An distribution
    if al1 <= ca:
        # 1.1.1
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si1 = 0
    else:
        # 1.2
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si1 = 0

    ca2 = ca - an
    si2 = si1 - 2 * an if si1 > 0 else 0
    al2 = al1 - an

    # Kn/Gb
    if 2 * al2 >= si2:
        kn = si2 / 2
        gb = al2 - kn
        si3 = 0
    else:
        kn = al2
        si3 = si2 - 2 * kn

    # Q = remaining Si
    q = max(si3, 0)

    if tracer:
        tracer.record("Type1", "ab", ab, "Ab = Na")
        tracer.record("Type1", "or_", or_, "Or = K")
        tracer.record("Type1", "an", an, "An")
        tracer.record("Type1", "kn", kn, "Kn")
        tracer.record("Type1", "gb", gb, "Gb")
        tracer.record("Type1", "q", q, "Q")

    return MineralComposition(ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q)


def calculate_type2(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Type 2 calculation: Al <= 1.2Na + 3.25K.

    Adds illite (requires K, Al, Si).
    Feldspars + illite + quartz.
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao

    # Step 1: Ab = Na, Or = K
    ab = na
    or_ = k

    # Step 2: Calculate initial Si and Al after feldspars
    si1 = si - 6 * ab
    al1 = al - or_ - ab

    # Step 3: An distribution (similar to Type 1)
    an = 0.0
    if al1 <= ca:
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si1 = 0
    else:
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si1 = 0

    ca2 = ca - an
    si2 = si1 - 2 * an if si1 > 0 else 0
    al2 = al1 - an

    # Step 4: Illite distribution
    # Illite formula: K(Al,Si)(Si,Al)O10(OH)2 — needs K, Al, Si
    ill = 0.0
    kn = 0.0
    gb = 0.0

    # Check if we have enough K for illite
    # Illite uses K, Al, Si in specific ratios
    if k > 0 and al2 > 0 and si2 > 0:
        # Illite consumes: K, Al, Si in ratio approximately 1:1:2
        # But constrained by available K (already assigned to Or)
        # Actually in Type 2, some Al goes to illite instead of Kaolinite/Gibbsite
        ill = min(al2, si2 / 2)
        si3 = si2 - 2 * ill
        al3 = al2 - ill
    else:
        si3 = si2
        al3 = al2

    # Step 5: Kn/Gb distribution
    if 2 * al3 >= si3:
        kn = si3 / 2
        gb = al3 - kn
        si4 = 0
    else:
        kn = al3
        si4 = si3 - 2 * kn

    # Step 6: Q = remaining Si
    q = max(si4, 0)

    if tracer:
        tracer.record("Type2", "ab", ab, "Ab = Na")
        tracer.record("Type2", "or_", or_, "Or = K")
        tracer.record("Type2", "an", an, "An")
        tracer.record("Type2", "ill", ill, "Ill")
        tracer.record("Type2", "kn", kn, "Kn")
        tracer.record("Type2", "gb", gb, "Gb")
        tracer.record("Type2", "q", q, "Q")

    return MineralComposition(
        ab=ab, an=an, or_=or_, ill=ill, chl=0.0, kn=kn, gb=gb, q=q
    )


def calculate_type3(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Type 3 calculation: Al <= 1.2Na + 3.25K + (Mg - 0.5K*k3)/k1.

    Most complex type with chlorite (adaptive k1-k4).
    Chlorite composition: (Mg,Fe,Al)6(Si,Al)4O10(OH)8
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo + fu.fe2o3 * 0.9  # Total Fe as FeO equivalent

    k1 = coeff.k1
    k2 = coeff.k2
    k3 = coeff.k3
    k4 = coeff.k4

    # Step 1: Ab = Na
    ab = na
    or_ = k

    # Step 2: Initial Si and Al
    si1 = si - 6 * ab
    al1 = al - or_ - ab

    # Step 3: An distribution
    an = 0.0
    if al1 <= ca:
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si1 = 0
    else:
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si1 = 0

    ca2 = ca - an
    si2 = si1 - 2 * an if si1 > 0 else 0
    al2 = al1 - an

    # Step 4: Chlorite distribution (using k1-k4 coefficients)
    # Chlorite formula: (Mg,Fe,Al)6(Si,Al)4O10(OH)8
    # Uses: k1*Mg, k2*Fe, k3*Al, k4*Si per formula unit
    chl = 0.0
    ill = 0.0
    kn = 0.0
    gb = 0.0

    # Calculate available Mg and Fe for chlorite
    # 1 f.u. chlorite consumes k1 Mg, k2 Fe, k3 Al, k4 Si
    # Maximum chlorite = min(available / per_formula_unit)
    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0:
        chl = min(mg / k1, fe / k2, al2 / k3, si2 / k4)
        chl = max(chl, 0)  # Clamp to non-negative
        si3 = si2 - chl * k4
        al3 = al2 - chl * k3
    else:
        si3 = si2
        al3 = al2

    # Step 5: Illite distribution
    if k > 0 and al3 > 0 and si3 > 0:
        ill = min(al3, si3 / 2)
        si4 = si3 - 2 * ill
        al4 = al3 - ill
    else:
        si4 = si3
        al4 = al3

    # Step 6: Kn/Gb distribution
    if 2 * al4 >= si4:
        kn = si4 / 2
        gb = al4 - kn
        si5 = 0
    else:
        kn = al4
        si5 = si4 - 2 * kn

    # Step 7: Q = remaining Si
    q = max(si5, 0)

    if tracer:
        tracer.record("Type3", "ab", ab, "Ab = Na")
        tracer.record("Type3", "or_", or_, "Or = K")
        tracer.record("Type3", "an", an, "An")
        tracer.record("Type3", "chl", chl, "Chl")
        tracer.record("Type3", "ill", ill, "Ill")
        tracer.record("Type3", "kn", kn, "Kn")
        tracer.record("Type3", "gb", gb, "Gb")
        tracer.record("Type3", "q", q, "Q")

    return MineralComposition(
        ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q
    )


def calculate_type4(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Type 4 calculation: Al <= 5Na + 3.25K + (Mg - 0.5K - 2Na)*k3/k1.

    Higher Al content, more complex distribution.
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo + fu.fe2o3 * 0.9

    k1 = coeff.k1
    k2 = coeff.k2
    k3 = coeff.k3
    k4 = coeff.k4

    # Step 1: Ab = Na
    ab = na
    or_ = k

    # Step 2: Initial Si and Al
    si1 = si - 6 * ab
    al1 = al - or_ - ab

    # Step 3: An distribution
    an = 0.0
    if al1 <= ca:
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si1 = 0
    else:
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si1 = 0

    ca2 = ca - an
    si2 = si1 - 2 * an if si1 > 0 else 0
    al2 = al1 - an

    # Step 4: Chlorite (more Al available)
    chl = 0.0
    ill = 0.0
    mm = 0.0
    kn = 0.0
    gb = 0.0

    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0:
        chl = min(mg / k1, fe / k2, al2 / k3, si2 / k4)
        chl = max(chl, 0)
        si3 = si2 - chl * k4
        al3 = al2 - chl * k3
    else:
        si3 = si2
        al3 = al2

    # Step 5: Montmorillonite (needs Na, Al, Si)
    if na > 0 and al3 > 0 and si3 > 0:
        mm = min(al3, si3 / 4)  # Montmorillonite uses more Si per Al
        si4 = si3 - 4 * mm
        al4 = al3 - mm
    else:
        si4 = si3
        al4 = al3

    # Step 6: Illite
    if k > 0 and al4 > 0 and si4 > 0:
        ill = min(al4, si4 / 2)
        si5 = si4 - 2 * ill
        al5 = al4 - ill
    else:
        si5 = si4
        al5 = al4

    # Step 7: Kn/Gb
    if 2 * al5 >= si5:
        kn = si5 / 2
        gb = al5 - kn
        si6 = 0
    else:
        kn = al5
        si6 = si5 - 2 * kn

    # Step 8: Q
    q = max(si6, 0)

    if tracer:
        tracer.record("Type4", "ab", ab, "Ab = Na")
        tracer.record("Type4", "or_", or_, "Or = K")
        tracer.record("Type4", "an", an, "An")
        tracer.record("Type4", "chl", chl, "Chl")
        tracer.record("Type4", "mm", mm, "Mm")
        tracer.record("Type4", "ill", ill, "Ill")
        tracer.record("Type4", "kn", kn, "Kn")
        tracer.record("Type4", "gb", gb, "Gb")
        tracer.record("Type4", "q", q, "Q")

    return MineralComposition(
        ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q, mm=mm
    )


def calculate_type5(
    fu: FormulaUnits,
    coeff: AdaptiveCoefficients,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Type 5 calculation: everything else (highest Al).

    Highest Al content, most complex distribution.
    All clay minerals possible.
    """
    na = fu.na2o
    k = fu.k2o
    al = fu.al2o3
    si = fu.sio2
    ca = fu.cao
    mg = fu.mgo
    fe = fu.feo + fu.fe2o3 * 0.9

    k1 = coeff.k1
    k2 = coeff.k2
    k3 = coeff.k3
    k4 = coeff.k4

    # Step 1: Ab = Na
    ab = na
    or_ = k

    # Step 2: Initial Si and Al
    si1 = si - 6 * ab
    al1 = al - or_ - ab

    # Step 3: An distribution
    an = 0.0
    if al1 <= ca:
        if si1 >= 2 * al1:
            an = al1
        else:
            an = si1 / 2
            si1 = 0
    else:
        if si1 >= 2 * ca:
            an = ca
        else:
            an = si1 / 2
            si1 = 0

    ca2 = ca - an
    si2 = si1 - 2 * an if si1 > 0 else 0
    al2 = al1 - an

    # Step 4: Chlorite
    chl = 0.0
    ill = 0.0
    mm = 0.0
    kn = 0.0
    gb = 0.0

    if k1 > 0 and k2 > 0 and k3 > 0 and k4 > 0:
        chl = min(mg / k1, fe / k2, al2 / k3, si2 / k4)
        chl = max(chl, 0)
        si3 = si2 - chl * k4
        al3 = al2 - chl * k3
    else:
        si3 = si2
        al3 = al2

    # Step 5: Montmorillonite (highest Al, more montmorillonite)
    if na > 0 and al3 > 0 and si3 > 0:
        mm = min(al3, si3 / 3)  # More montmorillonite in Type 5
        si4 = si3 - 3 * mm
        al4 = al3 - mm
    else:
        si4 = si3
        al4 = al3

    # Step 6: Illite
    if k > 0 and al4 > 0 and si4 > 0:
        ill = min(al4, si4 / 2)
        si5 = si4 - 2 * ill
        al5 = al4 - ill
    else:
        si5 = si4
        al5 = al4

    # Step 7: Kn/Gb
    if 2 * al5 >= si5:
        kn = si5 / 2
        gb = al5 - kn
        si6 = 0
    else:
        kn = al5
        si6 = si5 - 2 * kn

    # Step 8: Q
    q = max(si6, 0)

    if tracer:
        tracer.record("Type5", "ab", ab, "Ab = Na")
        tracer.record("Type5", "or_", or_, "Or = K")
        tracer.record("Type5", "an", an, "An")
        tracer.record("Type5", "chl", chl, "Chl")
        tracer.record("Type5", "mm", mm, "Mm")
        tracer.record("Type5", "ill", ill, "Ill")
        tracer.record("Type5", "kn", kn, "Kn")
        tracer.record("Type5", "gb", gb, "Gb")
        tracer.record("Type5", "q", q, "Q")

    return MineralComposition(
        ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn, gb=gb, q=q, mm=mm
    )


def stage_vi(
    fu: FormulaUnits,
    minerals: MineralComposition,
    fe: "np.ndarray",
    coeff: Optional[AdaptiveCoefficients] = None,
    tracer: Optional[DebugTraceCollector] = None,
) -> MineralComposition:
    """
    Stage VI: Final distribution of remaining elements.

    Distributes Ca, Mg, Fe, Mn, Si into carbonates, oxides, serpentine.
    Residuals = formula units - consumed by previous stages.
    """
    from src.core.constants import OXIDE_ORDER

    # Chlorite coefficients (default to 1.0 if not provided)
    k1 = coeff.k1 if coeff else 1.0
    k2 = coeff.k2 if coeff else 1.0
    k3 = coeff.k3 if coeff else 1.0
    k4 = coeff.k4 if coeff else 1.0

    # Calculate residuals from formula units minus mineral consumption
    # Ca consumed: by anorthite (An) and apatite (Ap)
    ca_an = minerals.an  # Ca in anorthite (1 Ca per An f.u.)
    ca_ap = minerals.ap * 5  # Ca in apatite (5 Ca per Ap f.u.)
    ca_n = fu.cao - ca_an - ca_ap

    # Mg consumed: by chlorite (k1 per Chl f.u.) and serpentine (3 per Srp f.u.)
    mg_chl = minerals.chl * k1
    mg_srp = minerals.srp * 3
    mg_n = fu.mgo - mg_chl - mg_srp

    # Fe consumed: by chlorite (k2 per Chl f.u.) and hematite (2 per Ht f.u.)
    fe_total = fu.feo  # Already FeO total in formula units
    fe_chl = minerals.chl * k2
    fe_ht = minerals.ht * 2
    fe_n = fe_total - fe_chl - fe_ht

    # Mn remains (goes to prl/pyrolusite)
    mn_n = fu.mno

    # Si consumed: by all Si-bearing minerals
    si_consumed = (
        minerals.ab * 3 +   # Abite: NaAlSi3O8 → 3 Si
        minerals.an * 2 +   # Anorthite: CaAl2Si2O8 → 2 Si
        minerals.or_ * 3 +  # Orthoclase: KAlSi3O8 → 3 Si
        minerals.ill * 3 +  # Illite: KAl2(AlSi3O10)(OH)2 → 3 Si
        minerals.chl * k4 + # Chlorite → k4 Si
        minerals.kn * 2 +   # Kaolinite: Al2Si2O5(OH)4 → 2 Si
        minerals.mm * 4 +   # Montmorillonite → 4 Si
        minerals.srp * 2    # Serpentine: Mg3Si2O5(OH)4 → 2 Si
    )
    si_n = fu.sio2 - si_consumed

    if tracer:
        tracer.record("StageVI", "ca_n_before", ca_n, "Ca residual before branching")
        tracer.record("StageVI", "mg_n_before", mg_n, "Mg residual before branching")
        tracer.record("StageVI", "fe_n_before", fe_n, "Fe residual before branching")
        tracer.record("StageVI", "si_n_before", si_n, "Si residual before branching")

    # Branching logic
    # VI A: Ca_n >= Mg_n + Fe_n
    if ca_n >= mg_n + fe_n:
        dl = mg_n
        ank = fe_n
        cc = ca_n - dl - ank
        rch = mn_n
        q = si_n
        ht = 0.0
        sd = 0.0

        if ca_n <= 250:
            ht = fe_n / 2
        else:
            sd = fe_n

        minerals = MineralComposition(
            ab=minerals.ab, an=minerals.an, or_=minerals.or_,
            ill=minerals.ill, chl=minerals.chl, kn=minerals.kn,
            mm=minerals.mm, gb=minerals.gb,
            cc=cc, dl=dl, ank=ank, rch=rch, sd=sd,
            q=q, ap=minerals.ap, c=minerals.c,
            srp=0.0, mst=0.0, ht=ht, prl=mn_n,
            pr=minerals.pr, rt=minerals.rt,
            hl=minerals.hl, gy=minerals.gy, fl=minerals.fl,
        )
    else:
        # VI B: Ca_n < Mg_n + Fe_n
        if ca_n < mg_n:
            dl = ca_n
            mg_n1 = mg_n - dl

            # VI B a: Si_n >= 2/3 * Mg_n1
            q = 0.0
            mst = 0.0
            if si_n >= 2 / 3 * mg_n1:
                srp = mg_n1 / 3
                q = si_n - 2 * srp
                ht = fe_n / 2
            # VI B b: Si_n < 2/3 * Mg_n1
            else:
                srp = si_n / 2
                mst = mg_n1 - 3 * srp
                ht = fe_n / 2

            minerals = MineralComposition(
                ab=minerals.ab, an=minerals.an, or_=minerals.or_,
                ill=minerals.ill, chl=minerals.chl, kn=minerals.kn,
                mm=minerals.mm, gb=minerals.gb,
                cc=0.0, dl=dl, ank=0.0, rch=0.0, sd=0.0,
                q=q, ap=minerals.ap, c=minerals.c,
                srp=srp, mst=mst, ht=ht, prl=mn_n,
                pr=minerals.pr, rt=minerals.rt,
                hl=minerals.hl, gy=minerals.gy, fl=minerals.fl,
            )
        else:
            # Ca_n >= Mg_n but < Mg_n + Fe_n
            dl = mg_n
            ca_n1 = ca_n - dl
            ank = ca_n1
            fe_n1 = fe_n - ank
            ht = fe_n1 / 2
            q = si_n

            minerals = MineralComposition(
                ab=minerals.ab, an=minerals.an, or_=minerals.or_,
                ill=minerals.ill, chl=minerals.chl, kn=minerals.kn,
                mm=minerals.mm, gb=minerals.gb,
                cc=0.0, dl=dl, ank=ank, rch=mn_n, sd=0.0,
                q=q, ap=minerals.ap, c=minerals.c,
                srp=0.0, mst=0.0, ht=ht, prl=0.0,
                pr=minerals.pr, rt=minerals.rt,
                hl=minerals.hl, gy=minerals.gy, fl=minerals.fl,
            )

    return minerals
