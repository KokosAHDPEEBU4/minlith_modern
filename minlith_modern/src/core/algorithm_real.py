"""Real algorithm — uses types_logic.py for actual MINLITH calculations.

This replaces the stub algorithm with the real type-specific logic.
"""

from __future__ import annotations

import logging

from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.models import AdaptiveCoefficients, FormulaUnits, MineralComposition
from src.core.types_logic import (
    calculate_type1,
    calculate_type2,
    calculate_type3,
    calculate_type4,
    calculate_type5,
    stage_vi,
)

logger = logging.getLogger(__name__)


class RealAlgorithm:
    """Real MINLITH algorithm using type-specific logic from types_logic.py."""

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        """Run real calculation using types_logic.py."""
        # Build FormulaUnits from AlgorithmInput
        fu = FormulaUnits(
            sio2=inp.sio2,
            tio2=inp.tio2,
            al2o3=inp.al2o3,
            fe2o3=0.0,  # Already converted to FeO total in Stage 0
            feo=inp.feo,
            mgo=inp.mgo,
            cao=inp.cao,
            na2o=inp.na2o,
            k2o=inp.k2o,
            p2o5=inp.p2o5,
            mno=inp.mno,
            c=inp.c,
            so3=inp.so3,
            f=inp.f,
            cl=inp.cl,
            s=inp.s,
        )

        coeff = AdaptiveCoefficients(
            k1=inp.k1, k2=inp.k2, k3=inp.k3, k4=inp.k4,
            F=inp.F, A=inp.A,
        )

        # Dispatch to type-specific calculation
        rock_type = inp.rock_type
        if rock_type == 1:
            minerals = calculate_type1(fu, coeff)
        elif rock_type == 2:
            minerals = calculate_type2(fu, coeff)
        elif rock_type == 3:
            minerals = calculate_type3(fu, coeff)
        elif rock_type == 4:
            minerals = calculate_type4(fu, coeff)
        elif rock_type == 5:
            minerals = calculate_type5(fu, coeff)
        else:
            minerals = calculate_type3(fu, coeff)  # fallback

        # Build fe array for stage_vi (18 values in OXIDE_ORDER)
        import numpy as np
        from src.core.constants import OXIDE_ORDER

        fe = np.zeros(18, dtype=np.float64)
        fe[OXIDE_ORDER.index("sio2")] = inp.sio2
        fe[OXIDE_ORDER.index("tio2")] = inp.tio2
        fe[OXIDE_ORDER.index("al2o3")] = inp.al2o3
        fe[OXIDE_ORDER.index("feo")] = inp.feo
        fe[OXIDE_ORDER.index("mgo")] = inp.mgo
        fe[OXIDE_ORDER.index("cao")] = inp.cao
        fe[OXIDE_ORDER.index("na2o")] = inp.na2o
        fe[OXIDE_ORDER.index("k2o")] = inp.k2o
        fe[OXIDE_ORDER.index("p2o5")] = inp.p2o5
        fe[OXIDE_ORDER.index("mno")] = inp.mno
        fe[OXIDE_ORDER.index("c")] = inp.c
        fe[OXIDE_ORDER.index("so3")] = inp.so3
        fe[OXIDE_ORDER.index("f")] = inp.f
        fe[OXIDE_ORDER.index("cl")] = inp.cl
        fe[OXIDE_ORDER.index("s")] = inp.s

        # Stage VI: carbonates, oxides, serpentine
        minerals = stage_vi(fu, minerals, fe, coeff)

        # Map to AlgorithmOutput
        return AlgorithmOutput(
            Ab=minerals.ab,
            An=minerals.an,
            Or=minerals.or_,
            Ill=minerals.ill,
            Chl=minerals.chl,
            Kn=minerals.kn,
            Mm=minerals.mm,
            Gb=minerals.gb,
            Q=minerals.q,
            Dl=minerals.dl,
            Ank=minerals.ank,
            Cc=minerals.cc,
            Rch=minerals.rch,
            Sd=minerals.sd,
            Srp=minerals.srp,
            Mst=minerals.mst,
            Ht=minerals.ht,
            Prl=minerals.prl,
        )
