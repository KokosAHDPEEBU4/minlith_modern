"""Tests for core models — OxideComposition, MineralComposition, FormulaUnits."""

import pytest

from src.core.models import (
    OxideComposition, MineralComposition, FormulaUnits,
    Sample, AdaptiveCoefficients, RockType,
)


class TestOxideComposition:
    def test_zero_composition(self):
        c = OxideComposition()
        assert c.sio2 == 0.0
        assert c.sum() == 0.0

    def test_custom_values(self):
        c = OxideComposition(sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06)
        assert c.sio2 == 52.5
        assert c.sum() == pytest.approx(52.5 + 23.41 + 1.71 + 8.06)

    def test_sum_all_fields(self):
        c = OxideComposition(
            sio2=50, tio2=1, al2o3=20, fe2o3=2, feo=5,
            mgo=3, cao=5, na2o=3, k2o=2, p2o5=0.5, mno=0.1,
        )
        assert abs(c.sum() - 91.6) < 0.01

    def test_attributes(self):
        c = OxideComposition(sio2=52.5, al2o3=23.41)
        assert c.sio2 == 52.5
        assert c.al2o3 == 23.41
        assert c.mgo == 0.0


class TestMineralComposition:
    def test_zero(self):
        m = MineralComposition()
        assert m.ab == 0.0
        assert m.q == 0.0
        assert m.kn == 0.0

    def test_custom(self):
        m = MineralComposition(ab=10.5, or_=5.2, q=30.0)
        assert m.ab == 10.5
        assert m.or_ == 5.2
        assert m.q == 30.0

    def test_attributes(self):
        m = MineralComposition(ab=10.5, ill=20.0)
        assert m.ab == 10.5
        assert m.ill == 20.0
        assert m.chl == 0.0


class TestFormulaUnits:
    def test_zero(self):
        f = FormulaUnits()
        assert f.sio2 == 0.0
        assert f.al2o3 == 0.0

    def test_custom(self):
        f = FormulaUnits(sio2=5313.84, al2o3=183.12, feo=1336.09)
        assert f.sio2 == 5313.84

    def test_corrected_fields(self):
        f = FormulaUnits(cao=49.93, cao_corrected=49.93, fe_total=1336.09)
        assert f.cao_corrected == 49.93
        assert f.fe_total == 1336.09


class TestSample:
    def test_create(self):
        s = Sample(name="T-O2", composition=OxideComposition(sio2=52.5))
        assert s.name == "T-O2"
        assert s.composition.sio2 == 52.5


class TestAdaptiveCoefficients:
    def test_create(self):
        c = AdaptiveCoefficients(k1=0.56, k2=0.3, k3=1.0, k4=2.0, F=1.2, A=0.8)
        assert c.k1 == 0.56
        assert c.k2 == 0.3
        assert c.k3 == 1.0
        assert c.k4 == 2.0
        assert c.F == 1.2
        assert c.A == 0.8


class TestRockType:
    def test_values(self):
        assert RockType.TYPE_1.value == 1
        assert RockType.TYPE_5.value == 5
