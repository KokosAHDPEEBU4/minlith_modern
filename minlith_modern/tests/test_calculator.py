"""Tests for calculator — basic runs, all rock types, edge cases."""

from src.core.calculator import Calculator
from src.core.models import OxideComposition, Sample


class TestCalculatorBasic:
    def setup_method(self):
        self.calc = Calculator()

    def test_quartz_only(self):
        s = Sample(name="quartz", composition=OxideComposition(sio2=100.0))
        r = self.calc.calculate_single(s)
        assert r.sample_name == "quartz"
        assert r.minerals_weight.q > 90.0

    def test_albite_only(self):
        s = Sample(name="albite", composition=OxideComposition(
            sio2=68.7, al2o3=19.5, na2o=11.8))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.ab > 50.0

    def test_orthoclase_only(self):
        s = Sample(name="orthoclase", composition=OxideComposition(
            sio2=64.7, al2o3=18.4, k2o=16.9))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.or_ > 50.0

    def test_input_preserved(self):
        s = Sample(name="test", composition=OxideComposition(sio2=52.5, al2o3=23.41))
        r = self.calc.calculate_single(s)
        assert r.input_composition.sio2 == 52.5
        assert r.input_composition.al2o3 == 23.41

    def test_result_has_all_fields(self):
        s = Sample(name="test", composition=OxideComposition(sio2=52.5, al2o3=23.41))
        r = self.calc.calculate_single(s)
        assert r.sample_name == "test"
        assert r.rock_type is not None
        assert r.coefficients is not None
        assert r.minerals_weight is not None
        assert r.defect is not None
        assert isinstance(r.warnings, list)


class TestCalculatorCoefficients:
    def setup_method(self):
        self.calc = Calculator()

    def test_F_positive(self):
        s = Sample(name="test", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45))
        r = self.calc.calculate_single(s)
        assert r.coefficients.F > 0

    def test_A_nonnegative(self):
        s = Sample(name="test", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45))
        r = self.calc.calculate_single(s)
        assert r.coefficients.A >= 0

    def test_k_values(self):
        s = Sample(name="test", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45))
        r = self.calc.calculate_single(s)
        assert r.coefficients.k1 > 0
        assert r.coefficients.k2 > 0


class TestCalculatorMinerals:
    def setup_method(self):
        self.calc = Calculator()

    def test_negative_minerals_allowed(self):
        """Negative minerals (e.g. Kn) are valid artifacts."""
        s = Sample(name="test", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45))
        r = self.calc.calculate_single(s)
        assert isinstance(r.minerals_weight.kn, float)

    def test_zero_composition(self):
        s = Sample(name="empty", composition=OxideComposition())
        r = self.calc.calculate_single(s)
        assert r.defect is not None

    def test_feldspar_fields(self):
        s = Sample(name="test", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.ab >= 0
        assert r.minerals_weight.an >= 0
        assert r.minerals_weight.or_ >= 0
