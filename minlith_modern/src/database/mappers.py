"""Mappers between domain models and database models."""

from __future__ import annotations

from src.core.models import (
    AdaptiveCoefficients,
    CalculationResult,
    FormulaUnits,
    MineralComposition,
    OxideComposition,
    RockType,
)

_OXIDE_FIELDS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]

_MINERAL_FIELDS = [
    "ab", "an", "or_", "ill", "chl", "kn", "mm", "gb", "q", "dl",
    "ank", "cc", "rch", "sd", "srp", "mst", "ht", "prl",
    "ap", "pr", "hl", "fl", "rt", "gy", "c",
]


def domain_to_db(result: CalculationResult) -> dict:
    """Convert a CalculationResult to a dict suitable for DB storage."""
    return {
        "sample": result.sample_name,
        "oxides": {f: getattr(result.input_composition, f, 0.0) for f in _OXIDE_FIELDS},
        "rock_type": int(result.rock_type),
        "F": result.coefficients.F,
        "A": result.coefficients.A,
        "k1": result.coefficients.k1,
        "k2": result.coefficients.k2,
        "k3": result.coefficients.k3,
        "k4": result.coefficients.k4,
        "warnings": result.warnings,
        "minerals_fu": {f: getattr(result.minerals_formula, f, 0.0) for f in _MINERAL_FIELDS},
        "minerals_wt": {f: getattr(result.minerals_weight, f, 0.0) for f in _MINERAL_FIELDS},
    }


def db_to_domain(
    sample_name: str,
    oxides: dict[str, float],
    rock_type: int,
    F: float, A: float,
    k1: float, k2: float, k3: float, k4: float,
    minerals_fu: dict[str, float],
    minerals_wt: dict[str, float],
    warnings: list[str] | None = None,
) -> CalculationResult:
    """Convert DB data back to a CalculationResult domain object."""
    fu_keys = {f for f in _OXIDE_FIELDS} | {"cao_corrected", "na2o_corrected", "fe_total", "fe1"}
    fu_data = {k: v for k, v in minerals_fu.items() if k in fu_keys}
    return CalculationResult(
        sample_name=sample_name,
        input_composition=OxideComposition(**oxides),
        formula_units=FormulaUnits(**fu_data),
        coefficients=AdaptiveCoefficients(k1=k1, k2=k2, k3=k3, k4=k4, F=F, A=A),
        rock_type=RockType(rock_type),
        minerals_formula=MineralComposition(**minerals_fu),
        minerals_weight=MineralComposition(**minerals_wt),
        defect={},
        warnings=warnings or [],
    )
