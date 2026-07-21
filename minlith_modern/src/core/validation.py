"""Validation of input oxide compositions."""

from __future__ import annotations

from src.core.models import CalculationConfig, OxideComposition


def validate_sample(
    composition: OxideComposition,
    config: CalculationConfig,
) -> tuple[bool, list[str]]:
    """
    Validate oxide composition.

    Returns:
        (is_valid, warnings)
    """
    warnings = []
    is_valid = True

    # Check sum
    total = composition.sum()
    lo, hi = config.sum_tolerance
    if total < lo:
        warnings.append(f"Сумма оксидов {total:.2f}% ниже допустимого диапазона {lo}-{hi}%")
    elif total > hi:
        warnings.append(f"Сумма оксидов {total:.2f}% выше допустимого диапазона {lo}-{hi}%")

    # Check for negative values
    oxides = composition.__dict__
    for name, value in oxides.items():
        if isinstance(value, (int, float)) and value < 0:
            warnings.append(f"Отрицательное значение {name}: {value}")
            is_valid = False

    # Check for NaN/inf
    for name, value in oxides.items():
        if isinstance(value, float):
            if value != value:  # NaN check
                warnings.append(f"Некорректное значение {name}: NaN")
                is_valid = False
            elif abs(value) == float("inf"):
                warnings.append(f"Некорректное значение {name}: inf")
                is_valid = False

    return is_valid, warnings
