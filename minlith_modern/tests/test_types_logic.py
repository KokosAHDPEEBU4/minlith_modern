"""Tests for types_logic.py — Type 1-5 and Stage VI."""

from __future__ import annotations

import pytest

from src.core.models import (
    AdaptiveCoefficients,
    FormulaUnits,
    MineralComposition,
)
from src.core.types_logic import (
    _calc_an,
    _calc_kn_gb,
    calculate_type1,
    calculate_type2,
    calculate_type3,
    calculate_type4,
    calculate_type5,
    stage_vi,
)


def _coeff(F: float = 0.5, A: float = 0.5) -> AdaptiveCoefficients:
    from src.core.coefficients import calculate_coefficients
    return calculate_coefficients(F, A)


def _fu(**kwargs) -> FormulaUnits:
    defaults = {
        "sio2": 200.0, "tio2": 1.0, "al2o3": 50.0, "fe2o3": 0.0,
        "feo": 30.0, "mgo": 15.0, "cao": 10.0, "na2o": 5.0,
        "k2o": 3.0, "p2o5": 1.0, "mno": 0.5, "c": 0.0, "so3": 0.0,
        "f": 0.0, "cl": 0.0, "s": 0.0, "co2": 0.0, "so": 0.0,
    }
    defaults.update(kwargs)
    return FormulaUnits(**defaults)


class TestCalcAn:
    def test_al_exceeds_ca(self):
        an, si, al = _calc_an(al1=10.0, si1=30.0, ca=5.0)
        assert an == pytest.approx(5.0)
        assert al == pytest.approx(5.0)

    def test_al_limited_by_si(self):
        an, si, al = _calc_an(al1=10.0, si1=5.0, ca=10.0)
        assert an == pytest.approx(2.5)
        assert si == pytest.approx(0.0)

    def test_ca_exceeds_al(self):
        an, si, al = _calc_an(al1=3.0, si1=20.0, ca=10.0)
        assert an == pytest.approx(3.0)


class TestCalcKnGb:
    def test_al_limited(self):
        kn, gb, si = _calc_kn_gb(al_resid=5.0, si_resid=20.0)
        assert kn == pytest.approx(5.0)
        assert gb == pytest.approx(0.0)
        assert si == pytest.approx(10.0)

    def test_si_limited(self):
        kn, gb, si = _calc_kn_gb(al_resid=10.0, si_resid=5.0)
        assert kn == pytest.approx(2.5)
        assert gb == pytest.approx(7.5)
        assert si == pytest.approx(0.0)


class TestType1:
    def test_returns_mineral_composition(self):
        fu = _fu(al2o3=5.0, na2o=5.0, k2o=3.0)
        m = calculate_type1(fu, _coeff())
        assert isinstance(m, MineralComposition)

    def test_ab_equals_na(self):
        fu = _fu(na2o=7.0)
        m = calculate_type1(fu, _coeff())
        assert m.ab == pytest.approx(7.0)

    def test_or_equals_k(self):
        fu = _fu(k2o=4.0)
        m = calculate_type1(fu, _coeff())
        assert m.or_ == pytest.approx(4.0)

    def test_q_non_negative(self):
        fu = _fu(sio2=10.0)
        m = calculate_type1(fu, _coeff())
        assert m.q >= 0


class TestType2:
    def test_returns_mineral_composition(self):
        fu = _fu(al2o3=20.0, na2o=5.0, k2o=3.0)
        m = calculate_type2(fu, _coeff())
        assert isinstance(m, MineralComposition)

    def test_ab_equals_na(self):
        fu = _fu(na2o=6.0)
        m = calculate_type2(fu, _coeff())
        assert m.ab == pytest.approx(6.0)

    def test_illite_can_be_positive(self):
        fu = _fu(al2o3=30.0, na2o=2.0, k2o=5.0, sio2=300.0)
        m = calculate_type2(fu, _coeff())
        assert m.ill >= 0


class TestType3:
    def test_returns_mineral_composition(self):
        fu = _fu(al2o3=40.0, na2o=3.0, k2o=2.0, mgo=10.0, feo=20.0)
        m = calculate_type3(fu, _coeff())
        assert isinstance(m, MineralComposition)

    def test_ab_equals_na(self):
        fu = _fu(na2o=4.0)
        m = calculate_type3(fu, _coeff())
        assert m.ab == pytest.approx(4.0)

    def test_chl_uses_real_coefficients(self):
        coeff = _coeff(F=0.3)
        fu = _fu(al2o3=40.0, na2o=2.0, k2o=2.0, mgo=20.0, feo=20.0, sio2=300.0)
        m = calculate_type3(fu, coeff)
        assert m.chl >= 0


class TestType4:
    def test_returns_mineral_composition(self):
        fu = _fu(al2o3=50.0, na2o=2.0, k2o=1.0, mgo=15.0, feo=25.0)
        m = calculate_type4(fu, _coeff())
        assert isinstance(m, MineralComposition)


class TestType5:
    def test_returns_mineral_composition(self):
        fu = _fu(al2o3=60.0, na2o=1.0, k2o=0.5, mgo=10.0, feo=30.0)
        m = calculate_type5(fu, _coeff())
        assert isinstance(m, MineralComposition)


class TestStageVI:
    def test_returns_mineral_composition(self):
        fu = _fu(cao=10.0, mgo=15.0, feo=20.0)
        m = MineralComposition(ab=5.0, an=3.0, or_=2.0, ill=4.0, chl=6.0, q=50.0)
        result = stage_vi(fu, m, None, _coeff())
        assert isinstance(result, MineralComposition)

    def test_cc_when_ca_excess(self):
        fu = _fu(cao=50.0, mgo=0.1, feo=0.1)
        m = MineralComposition(ab=1.0, an=0.0, or_=0.0, ill=0.0, chl=0.0, q=10.0)
        result = stage_vi(fu, m, None, _coeff())
        assert result.cc > 0

    def test_q_preserved(self):
        fu = _fu(cao=0.0, mgo=0.0, feo=0.0)
        m = MineralComposition(ab=1.0, an=0.0, or_=0.0, q=42.0)
        result = stage_vi(fu, m, None, _coeff())
        assert result.q == pytest.approx(42.0)
