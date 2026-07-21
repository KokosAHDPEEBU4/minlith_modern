"""Adaptive coefficients k1-k4 for chlorite based on F (Fe3+/ΣFe)."""

from __future__ import annotations

from src.core.models import AdaptiveCoefficients


def calculate_coefficients(F: float, A: float) -> AdaptiveCoefficients:
    """
    Calculate adaptive coefficients k1-k4 based on F (Fe3+/ΣFe).

    5 ranges of F with different linear formulas for k1, k2, k3.
    k4 = 10 - k1 - k2 - 2*k3 (sum of cations = 10).

    Args:
        F: Fe3+/ΣFe ratio (0.0 to 1.0)
        A: Al/(Al+Fe) ratio

    Returns:
        AdaptiveCoefficients with k1, k2, k3, k4, F, A
    """
    if F < 0.0 or F > 1.0:
        raise ValueError(f"F must be between 0 and 1, got {F}")

    # Range 1: F = 0 — 0.21
    if F < 0.21:
        k1 = -5.18 * F + 4.42
        k2 = 4.09 * F
        k3 = (3.16 - 0.41 * F) / 2

    # Range 2: F = 0.21 — 0.51
    elif F < 0.51:
        k1 = 3.93 - 2.96 * F
        k2 = 5.66 * F - 0.34
        k3 = (3.66 - 2.69 * F) / 2

    # Range 3: F = 0.51 — 0.70
    elif F < 0.70:
        k1 = 5.13 - 5.32 * F
        k2 = 2.54 * F + 1.24
        k3 = (3.46 * F + 0.53) / 2

    # Range 4: F = 0.70 — 0.87
    elif F < 0.87:
        k1 = 6.2 - 12 * F
        k2 = 2.54 * F + 1.24
        k3 = (3.46 * F + 0.53) / 2

    # Range 5: F = 0.87 — 1.0
    else:
        k1 = 4 - 4 * F
        k2 = 18.36 * F - 12.36
        k3 = (25 - 25 * F) / 2

    k4 = 10 - k1 - k2 - 2 * k3

    return AdaptiveCoefficients(
        k1=round(k1, 3),
        k2=round(k2, 3),
        k3=round(k3, 3),
        k4=round(k4, 3),
        F=round(F, 3),
        A=round(A, 3),
    )
