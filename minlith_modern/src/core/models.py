"""Data models for MINLITH Modern."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

import numpy as np


class RockType(IntEnum):
    """Rock type classification (1-5)."""

    TYPE_1 = 1  # Al <= 1.2Na + K
    TYPE_2 = 2  # Al <= 1.2Na + 3.25K
    TYPE_3 = 3  # Al <= 1.2Na + 3.25K + (Mg - 0.5K*k3)/k1
    TYPE_4 = 4  # Al <= 5Na + 3.25K + (Mg - 0.5K - 2Na)*k3/k1
    TYPE_5 = 5  # everything else


@dataclass(frozen=True)
class OxideComposition:
    """Chemical composition of a rock sample (weight %)."""

    sio2: float = 0.0
    tio2: float = 0.0
    al2o3: float = 0.0
    fe2o3: float = 0.0
    feo: float = 0.0
    mgo: float = 0.0
    cao: float = 0.0
    na2o: float = 0.0
    k2o: float = 0.0
    p2o5: float = 0.0
    mno: float = 0.0
    c: float = 0.0
    so3: float = 0.0
    f: float = 0.0
    cl: float = 0.0
    s: float = 0.0
    co2: float = 0.0
    so: float = 0.0

    def sum(self) -> float:
        """Sum of all oxides."""
        return sum([
            self.sio2, self.tio2, self.al2o3, self.fe2o3, self.feo,
            self.mgo, self.cao, self.na2o, self.k2o, self.p2o5,
            self.mno, self.c, self.so3, self.f, self.cl,
            self.s, self.co2, self.so,
        ])

    def to_array(self) -> np.ndarray:
        """Convert to numpy array (18 values)."""
        return np.array([
            self.sio2, self.tio2, self.al2o3, self.fe2o3, self.feo,
            self.mgo, self.cao, self.na2o, self.k2o, self.p2o5,
            self.mno, self.c, self.so3, self.f, self.cl,
            self.s, self.co2, self.so,
        ], dtype=np.float64)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> OxideComposition:
        """Create from dictionary of oxide names to values."""
        return cls(**{k.lower(): v for k, v in data.items() if hasattr(cls, k.lower())})


@dataclass(frozen=True)
class FormulaUnits:
    """Formula units (ф.е.) after conversion from weight %."""

    sio2: float = 0.0
    tio2: float = 0.0
    al2o3: float = 0.0
    fe2o3: float = 0.0
    feo: float = 0.0
    mgo: float = 0.0
    cao: float = 0.0
    na2o: float = 0.0
    k2o: float = 0.0
    p2o5: float = 0.0
    mno: float = 0.0
    c: float = 0.0
    so3: float = 0.0
    f: float = 0.0
    cl: float = 0.0
    s: float = 0.0
    co2: float = 0.0
    so: float = 0.0
    # Corrected values
    cao_corrected: float = 0.0
    na2o_corrected: float = 0.0
    fe_total: float = 0.0
    fe1: float = 0.0


@dataclass(frozen=True)
class AdaptiveCoefficients:
    """Adaptive coefficients for chlorite (k1-k4) and oxidation state."""

    k1: float  # Mg in chlorite
    k2: float  # Fe in chlorite
    k3: float  # Al in chlorite
    k4: float  # Si in chlorite
    F: float   # Fe3+/sum(Fe)
    A: float   # Al/(Al+Fe)
    k_or: float = 1.0  # доля K2O, идущая в ортоклаз (0.0-1.0)

    @classmethod
    def from_F(cls, F: float, A: float, mass_source: str = "iupac") -> AdaptiveCoefficients:
        """Calculate coefficients from F and A values."""
        from src.core.coefficients import calculate_coefficients
        return calculate_coefficients(F, A)


@dataclass(frozen=True)
class MineralComposition:
    """Mineral composition (in formula units or weight %)."""

    # Feldspars
    ab: float = 0.0    # Albite
    an: float = 0.0    # Anorthite
    pl: float = 0.0    # Plagioclase (Ab+An)
    or_: float = 0.0   # Orthoclase
    # Clay minerals
    ill: float = 0.0   # Illite
    chl: float = 0.0   # Chlorite
    kn: float = 0.0    # Kaolinite
    mm: float = 0.0    # Montmorillonite
    gb: float = 0.0    # Gibbsite
    # Carbonates
    cc: float = 0.0    # Calcite
    dl: float = 0.0    # Dolomite
    ank: float = 0.0   # Ankerite
    rch: float = 0.0   # Rhodochrosite
    sd: float = 0.0    # Siderite
    # Other
    q: float = 0.0     # Quartz
    ap: float = 0.0    # Apatite
    c: float = 0.0     # Carbon
    srp: float = 0.0   # Serpentine
    mst: float = 0.0   # Magnesite
    ht: float = 0.0    # Hematite
    prl: float = 0.0   # Pyrolusite
    pr: float = 0.0    # Pyrite
    rt: float = 0.0    # Rutile
    hl: float = 0.0    # Halite
    gy: float = 0.0    # Gypsum
    fl: float = 0.0    # Fluorite
    # Derived groups
    fsp: float = 0.0       # Feldspars
    pel: float = 0.0       # Pelitic (clay)
    pel_fsp: float = 0.0   # Pelitic + feldspars
    carsd: float = 0.0     # Carbonates
    ill_kn: float = 0.0    # Ill + Kn
    chl_mm_srp: float = 0.0  # Chl + Mm + Srp

    def sum_formula_units(self) -> float:
        """Sum of base mineral formula units."""
        return (self.ab + self.an + self.or_ + self.ill + self.chl +
                self.kn + self.mm + self.gb + self.cc + self.dl +
                self.ank + self.rch + self.sd + self.q + self.ap +
                self.c + self.srp + self.mst + self.ht + self.prl +
                self.pr + self.rt + self.hl + self.gy + self.fl)


@dataclass(frozen=True)
class Sample:
    """Input sample with name and oxide composition."""

    name: str
    composition: OxideComposition


# Допустимые значения ``calculation_engine`` (как считает модель).
CALCULATION_ENGINES = ("excel_parity", "geological_theory", "python_rework")

# Старые имена движков → новые (обратная совместимость конфигов/кода).
LEGACY_ENGINE_ALIASES = {
    "clean": "excel_parity",
    "stub": "geological_theory",
    "custom": "python_rework",
}


@dataclass(frozen=True)
class CalculationConfig:
    """Configuration for calculation."""

    molar_mass_source: str = "iupac"  # "iupac" | "minlith"
    custom_molar_masses: dict[str, float] = field(default_factory=dict)
    sum_tolerance: tuple[float, float] = (98.0, 102.0)
    warn_negative: bool = True
    auto_correct_sum: bool = False
    decimal_places: int = 2
    include_formula_units: bool = False
    include_defect: bool = True
    include_parameters: bool = True
    timeout_seconds: int = 120
    batch_size: int | str = "auto"
    # "excel_parity" | "geological_theory" | "python_rework"
    # (безопасный дефолт; приложение явно ставит "excel_parity")
    calculation_engine: str = "geological_theory"


@dataclass(frozen=True)
class CalculationResult:
    """Result of mineralogical calculation for one sample."""

    sample_name: str
    input_composition: OxideComposition
    formula_units: FormulaUnits
    coefficients: AdaptiveCoefficients
    rock_type: RockType
    minerals_formula: MineralComposition   # in formula units
    minerals_weight: MineralComposition     # in weight %
    defect: dict[str, float]               # oxide residuals
    warnings: list[str]
    debug_trace: Optional[object] = None
    geo_params: Optional[object] = None    # GeoParameters (CIA, ICV, PIA, ASI, AI)
    anomalies: Optional[list] = None       # list[AnomalyHypothesis]
