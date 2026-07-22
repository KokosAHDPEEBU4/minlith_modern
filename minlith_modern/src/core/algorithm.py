"""Algorithm protocol — the contract between calculator and mineral logic.

This is the interface that must be implemented when the VBA macro is found.
The calculator calls algorithm.compute() with all preprocessed inputs,
and gets back mineral formula units.

To integrate VBA macro:
  1. Read the macro's branching logic line by line
  2. Implement compute() to reproduce it
  3. Swap StubAlgorithm for your implementation in calculator.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class AlgorithmInput:
    """All inputs the algorithm needs. Preprocessed by calculator (Stage 0).

    Values are formula units (ф.е.), already corrected for:
      - Fe2O3 → FeO total
      - CaO − apatite
      - F − fluorite
      - Na2O − halite

    Variable names match Excel/Type sheet conventions.
    """

    # Formula units (oxide rows from Excel, rows 2-19)
    sio2: float     # Si° (D2)
    tio2: float     # Ti° (D3)
    al2o3: float    # Al° (D4)
    feo: float      # Fe° total (D6) — Fe2O3*0.9+FeO converted to ф.е.
    mgo: float      # Mg° (D7)
    cao: float      # Ca° (D8) — corrected for apatite
    na2o: float     # Na° (D9) — corrected for halite
    k2o: float      # K° (D10)
    p2o5: float     # P° (D11)
    mno: float      # Mn° (D12)
    c: float        # C° (D13)
    so3: float      # SO3° (D14)
    f: float        # F° (D15) — corrected for fluorite
    cl: float       # Cl° (D16)
    s: float        # S° (D17)

    # Adaptive coefficients (from Stage 0)
    k1: float       # Mg in chlorite
    k2: float       # Fe in chlorite
    k3: float       # Al in chlorite
    k4: float       # Si in chlorite
    F: float        # Fe3+/sum(Fe)
    A: float        # Al/(Al+Fe)

    # Rock type (1-5)
    rock_type: int


@dataclass
class AlgorithmOutput:
    """Mineral formula units produced by the algorithm.

    Negative values are allowed — they represent stoichiometric artifacts
    that get clamped or carried through to the defect calculation.
    """

    # Feldspars
    Ab: float = 0.0    # Albite (NaAlSi3O8)
    An: float = 0.0    # Anorthite (CaAl2Si2O8)
    Or: float = 0.0    # Orthoclase (KAlSi3O8)

    # Clay minerals
    Ill: float = 0.0   # Illite
    Chl: float = 0.0   # Chlorite
    Kn: float = 0.0    # Kaolinite
    Mm: float = 0.0    # Montmorillonite
    Gb: float = 0.0    # Gibbsite

    # Quartz
    Q: float = 0.0

    # Carbonates
    Dl: float = 0.0    # Dolomite
    Ank: float = 0.0   # Ankerite
    Cc: float = 0.0    # Calcite
    Rch: float = 0.0   # Rhodochrosite
    Sd: float = 0.0    # Siderite

    # Others
    Srp: float = 0.0   # Serpentine
    Mst: float = 0.0   # Magnesite
    Ht: float = 0.0    # Hematite
    Prl: float = 0.0   # Pyrolusite


class MineralAlgorithm(Protocol):
    """Protocol for normative mineral calculation algorithms.

    Implementations include:
      - StubAlgorithm: placeholder with known stoichiometry
      - VbaAlgorithm: when VBA macro is found and ported
    """

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        """Run the normative mineral calculation.

        Args:
            inp: Preprocessed formula units and coefficients.

        Returns:
            Mineral formula units (may include negative values).
        """
        ...
