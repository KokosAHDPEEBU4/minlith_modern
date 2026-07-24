"""Tests for coefficients.py — all 5 F ranges."""

from __future__ import annotations

import math

import pytest

from src.core.coefficients import calculate_coefficients
from src.core.models import AdaptiveCoefficients


class TestCoefficients:
    """Test k1-k4 calculation across all 5 F ranges."""

    def test_range_1_f_zero(self):
        c = calculate_coefficients(0.0, 0.5)
        assert c.k1 == pytest.approx(4.42, abs=0.01)
        assert c.k2 == pytest.approx(0.0, abs=0.01)
        assert c.k3 == pytest.approx(1.58, abs=0.01)
        assert c.k4 == pytest.approx(10 - 4.42 - 0.0 - 2 * 1.58, abs=0.01)

    def test_range_1_f_mid(self):
        c = calculate_coefficients(0.10, 0.5)
        assert c.k1 == pytest.approx(-5.18 * 0.10 + 4.42, abs=0.01)
        assert c.k2 == pytest.approx(4.09 * 0.10, abs=0.01)
        assert c.k3 == pytest.approx((3.16 - 0.41 * 0.10) / 2, abs=0.01)

    def test_range_2(self):
        c = calculate_coefficients(0.30, 0.5)
        assert c.k1 == pytest.approx(3.93 - 2.96 * 0.30, abs=0.01)
        assert c.k2 == pytest.approx(5.66 * 0.30 - 0.34, abs=0.01)

    def test_range_3(self):
        c = calculate_coefficients(0.60, 0.5)
        assert c.k1 == pytest.approx(5.13 - 5.32 * 0.60, abs=0.01)
        assert c.k2 == pytest.approx(2.54 * 0.60 + 1.24, abs=0.01)

    def test_range_4(self):
        c = calculate_coefficients(0.80, 0.5)
        assert c.k1 == pytest.approx(max(6.2 - 12 * 0.80, 0.0), abs=0.01)
        assert c.k2 == pytest.approx(2.54 * 0.80 + 1.24, abs=0.01)

    def test_range_5(self):
        c = calculate_coefficients(0.95, 0.5)
        assert c.k1 == pytest.approx(max(4 - 4 * 0.95, 0.0), abs=0.01)
        assert c.k2 == pytest.approx(18.36 * 0.95 - 12.36, abs=0.01)

    def test_k4_formula(self):
        for F in [0.0, 0.1, 0.21, 0.3, 0.51, 0.6, 0.7, 0.8, 0.87, 0.95, 1.0]:
            c = calculate_coefficients(F, 0.5)
            expected_k4 = 10 - c.k1 - c.k2 - 2 * c.k3
            assert c.k4 == pytest.approx(expected_k4, abs=0.01), f"Failed at F={F}"

    def test_f_out_of_range_raises(self):
        with pytest.raises(ValueError):
            calculate_coefficients(-0.1, 0.5)
        with pytest.raises(ValueError):
            calculate_coefficients(1.5, 0.5)

    def test_boundary_values(self):
        for F in [0.21, 0.51, 0.70, 0.87]:
            c = calculate_coefficients(F, 0.5)
            assert isinstance(c, AdaptiveCoefficients)

    def test_f_preserved(self):
        c = calculate_coefficients(0.42, 0.7)
        assert c.F == pytest.approx(0.42, abs=0.001)
        assert c.A == pytest.approx(0.7, abs=0.001)
