"""Algorithm protocol — the contract between calculator and mineral logic.

This is the interface that must be implemented when the VBA macro is found.
The calculator calls algorithm.compute() with all preprocessed inputs,
and gets back mineral formula units.

To integrate a new engine:
  1. Read the reference branching logic line by line
  2. Implement compute() to reproduce it
  3. Register the engine in Calculator._algorithm_for_engine (calculator.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.core.branch_overrides import BranchOverrides


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
    co2: float      # CO₂° (D18)
    so: float       # SO° (D19)

    # Adaptive coefficients (from Stage 0)
    k1: float       # Mg in chlorite
    k2: float       # Fe in chlorite
    k3: float       # Al in chlorite
    k4: float       # Si in chlorite
    F: float        # Fe3+/sum(Fe)
    A: float        # Al/(Al+Fe)

    # Rock type (1-5)
    rock_type: int

    # Исходные весовые проценты оксидов (ключи как в Excel: "SiO2", "TiO2"…).
    # Нужны движку excel_exact, который, как и книга MINLITH, сам пересчитывает
    # вес.% -> ф.е. с пошаговым ROUND. Для остальных движков необязательно.
    oxide_wt: dict[str, float] | None = None

    # Ручной выбор веток (override). Пусто/None — авто-выбор (поведение не меняется).
    overrides: BranchOverrides | None = None


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

    # Остаточные пулы оксидов (defect по теории). Заполняется GeologicalTheoryAlgorithm.
    residuals: dict[str, float] | None = None

    # Маршрут веток алгоритма (для графа разветвлений/диагностики).
    # Заполняется excel_parity; у остальных движков остаётся None.
    path: dict | None = None


@runtime_checkable
class MineralAlgorithm(Protocol):
    """Protocol for normative mineral calculation algorithms.

    Implementations include:
      - ExcelParityAlgorithm: «как в Excel» — точный паритет (без ROUND)
      - GeologicalTheoryAlgorithm: расчёт по геологической теории (файлы 00-07)
    """

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        """Run the normative mineral calculation.

        Args:
            inp: Preprocessed formula units and coefficients.

        Returns:
            Mineral formula units (may include negative values).
        """
        ...
