"""Stub algorithm — placeholder until VBA macro is found.

Contains ALL verified constants from the Excel file:
  - Consumption matrix (rows 155-162): how each mineral consumes oxides
  - Molar masses and formula weights
  - Type classification thresholds
  - Branching conditions

The compute() method implements a simplified version of the algorithm.
When the VBA macro is found, replace compute() with the real logic.

VERIFIED DATA FROM EXCEL (Нач+Type 12 sheet):
───────────────────────────────────────────────
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

  MW values (row 31-42):
    Ab=524.482, An=278.22, Or=556.7, Q=60.09, Mm=2202.6,
    Ill=2014.75, Chl=683.396, Gb=156.008, Kn=258.172,
    Ap=336.21, Cc=100.091, Dl=184.42, Ank=215.952,
    Rch=114.952, Sd=115.861, Srp=227.172, Mst=84.331,
    Ht=177.716, Prl=86.94, Pr=119.982, Rt=60.09,
    Hl=116.896, Gy=172.178, Fl=78.08

VERIFIED T-O2 RESULTS (row 147, Нач+Type 12):
  Ab=151.66, An=0, Chl=383.27, Ill=183.12, Or=101.15,
  Q=5313.84, Dl=-23, Srp=69.42, Prl=22.2, Kn=-385.09
"""

from __future__ import annotations

import logging

from src.core.algorithm import AlgorithmInput, AlgorithmOutput

logger = logging.getLogger(__name__)


class StubAlgorithm:
    """Placeholder algorithm. Returns approximate results.

    TODO: Replace compute() with VBA macro logic once found.
    """

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        """Run stub calculation.

        This implements a simplified version of the Type 3/12 logic.
        Results will NOT match Excel until VBA macro is ported.
        """
        out = AlgorithmOutput()

        # Stage I: Feldspars
        # Ab = Na° (all sodium goes to albite)
        out.Ab = inp.na2o

        # Anorthite: Ca available after apatite correction
        # In Excel: An = max(Ca°, 0) clamped
        out.An = max(inp.cao, 0.0)

        # Stage II: Remaining Al, Si after feldspars
        # Al1 = Al° - Ab - An
        al1 = inp.al2o3 - out.Ab - out.An
        # Si1 = Si° - 6*Ab - 2*An
        si1 = inp.sio2 - 6 * out.Ab - 2 * out.An

        # Stage III: Illite + Chlorite + Or distribution
        # Simplified: distribute K between Or and Ill
        # Illite consumes K=2 per f.u., Or consumes K=1 per f.u.
        # Or = K° - 2*Ill (if K° >= 2*Ill, else Or=0)

        # Chlorite first (uses Mg, Fe)
        # Chl = Mg° / k1 (simplified — real algo is more complex)
        if inp.k1 > 0:
            out.Chl = inp.mgo / inp.k1
        else:
            out.Chl = 0.0

        # Illite = remaining Mg after chlorite
        ill_mg = inp.mgo - inp.k1 * out.Chl
        if ill_mg > 0:
            out.Ill = ill_mg
        else:
            out.Ill = 0.0

        # Or = K° - 2*Ill (K goes to illite first, remainder to orthoclase)
        out.Or = max(inp.k2o - 2 * out.Ill, 0.0)

        # Kaolinite from remaining Al
        remaining_al = al1 - out.Ill * 6.5 - out.Or
        if remaining_al > 0:
            out.Kn = remaining_al
        else:
            out.Kn = 0.0

        # Gibbsite from any leftover Al
        remaining_al2 = remaining_al - out.Kn
        if remaining_al2 > 0:
            out.Gb = remaining_al2

        # Quartz = remaining Si
        remaining_si = si1 - 16 * out.Ill - 6 * out.Or - 2 * out.Kn
        out.Q = max(remaining_si, 0.0)

        # Stage VI: Carbonates (simplified)
        # Dolomite = Ca° (after anorthite)
        remaining_ca = inp.cao - out.An
        if remaining_ca > 0 and inp.mgo > 0:
            out.Dl = min(remaining_ca, inp.mgo)

        # Hematite from Fe
        out.Ht = inp.feo / 2 if inp.feo > 0 else 0.0

        # Pyrolusite from Mn
        out.Prl = inp.mno

        # Serpentine (simplified)
        out.Srp = 0.0

        return out
