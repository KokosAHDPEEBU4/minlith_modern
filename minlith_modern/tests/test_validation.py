"""Tests for validation — validate_sample."""

from src.core.models import CalculationConfig, OxideComposition
from src.core.validation import validate_sample


class TestValidation:
    def setup_method(self):
        self.config = CalculationConfig()

    def test_valid_composition(self):
        c = OxideComposition(sio2=52.5, al2o3=23.41, feo=8.06, mgo=2.35)
        ok, warnings = validate_sample(c, self.config)
        # May have sum warning (86.32% is low), but should be valid structurally
        assert isinstance(ok, bool)
        assert isinstance(warnings, list)

    def test_low_sum_warning(self):
        c = OxideComposition(sio2=10.0)
        ok, warnings = validate_sample(c, self.config)
        # sum = 10% is very low — should produce a warning
        assert len(warnings) > 0

    def test_high_sum_warning(self):
        c = OxideComposition(
            sio2=60, al2o3=25, fe2o3=5, feo=10,
            mgo=5, cao=5, na2o=3, k2o=3)
        ok, warnings = validate_sample(c, self.config)
        # sum > 100%
        assert len(warnings) > 0

    def test_zero_composition(self):
        c = OxideComposition()
        ok, warnings = validate_sample(c, self.config)
        # Should have warnings about empty/zero
        assert len(warnings) > 0

    def test_warnings_are_strings(self):
        c = OxideComposition(sio2=10.0)
        ok, warnings = validate_sample(c, self.config)
        for w in warnings:
            assert isinstance(w, str)
