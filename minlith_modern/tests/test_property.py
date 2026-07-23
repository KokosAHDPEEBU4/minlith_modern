"""Property-based tests using Hypothesis.

Properties verified:
- OxideComposition invariants (sum, array length, round-trip)
- Coefficient constraint: k1+k2+k3+k4+2*k3=10
- Calculator output: normalization ~100%, no NaN/inf, input preserved
- Validation: negative/NaN detection, sum warnings
- MineralComposition: sum_formula_units consistency
"""

import math

import hypothesis
import numpy as np
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.core.models import (
    OxideComposition,
    MineralComposition,
    Sample,
    CalculationConfig,
    RockType,
)
from src.core.calculator import Calculator, CalculationTimeoutError
from src.core.coefficients import calculate_coefficients
from src.core.validation import validate_sample


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Realistic oxide values: 0–100 wt%, most samples have SiO2 30–80
oxide_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
small_oxide = st.floats(min_value=0.0, max_value=15.0, allow_nan=False, allow_infinity=False)
tiny_oxide = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)

@st.composite
def oxide_composition_strategy(draw):
    """Generate a realistic oxide composition."""
    sio2 = draw(st.floats(min_value=30.0, max_value=80.0, allow_nan=False, allow_infinity=False))
    al2o3 = draw(st.floats(min_value=5.0, max_value=35.0, allow_nan=False, allow_infinity=False))
    fe2o3 = draw(tiny_oxide)
    feo = draw(small_oxide)
    mgo = draw(small_oxide)
    cao = draw(small_oxide)
    na2o = draw(small_oxide)
    k2o = draw(small_oxide)
    p2o5 = draw(tiny_oxide)
    mno = draw(tiny_oxide)
    tio2 = draw(tiny_oxide)
    return OxideComposition(
        sio2=sio2, tio2=tio2, al2o3=al2o3, fe2o3=fe2o3, feo=feo,
        mgo=mgo, cao=cao, na2o=na2o, k2o=k2o, p2o5=p2o5, mno=mno,
    )


@st.composite
def valid_sample_strategy(draw):
    """Generate a sample that passes validation (sum ~100%)."""
    comp = draw(oxide_composition_strategy())
    # Scale to sum ~100
    total = comp.sum()
    if total == 0:
        total = 1.0
    scale = 100.0 / total
    comp = OxideComposition(
        sio2=comp.sio2 * scale, tio2=comp.tio2 * scale, al2o3=comp.al2o3 * scale,
        fe2o3=comp.fe2o3 * scale, feo=comp.feo * scale, mgo=comp.mgo * scale,
        cao=comp.cao * scale, na2o=comp.na2o * scale, k2o=comp.k2o * scale,
        p2o5=comp.p2o5 * scale, mno=comp.mno * scale,
    )
    return Sample(name="test", composition=comp)


@st.composite
def f_strategy(draw):
    """Generate F in [0, 1]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def a_strategy(draw):
    """Generate A in [0, 1]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


# ---------------------------------------------------------------------------
# 1. OxideComposition properties
# ---------------------------------------------------------------------------

class TestOxideCompositionProperties:
    @given(comp=oxide_composition_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_sum_equals_individual_fields(self, comp):
        """sum() must equal the sum of all 18 fields."""
        expected = (
            comp.sio2 + comp.tio2 + comp.al2o3 + comp.fe2o3 + comp.feo +
            comp.mgo + comp.cao + comp.na2o + comp.k2o + comp.p2o5 +
            comp.mno + comp.c + comp.so3 + comp.f + comp.cl +
            comp.s + comp.co2 + comp.so
        )
        assert math.isclose(comp.sum(), expected, rel_tol=1e-10)

    @given(comp=oxide_composition_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_to_array_length(self, comp):
        """to_array() must always return exactly 18 values."""
        arr = comp.to_array()
        assert arr.shape == (18,)
        assert arr.dtype == np.float64

    @given(comp=oxide_composition_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_to_array_matches_fields(self, comp):
        """to_array() values must match the dataclass fields in OXIDE_ORDER."""
        arr = comp.to_array()
        fields = [
            comp.sio2, comp.tio2, comp.al2o3, comp.fe2o3, comp.feo,
            comp.mgo, comp.cao, comp.na2o, comp.k2o, comp.p2o5,
            comp.mno, comp.c, comp.so3, comp.f, comp.cl,
            comp.s, comp.co2, comp.so,
        ]
        np.testing.assert_array_equal(arr, fields)

    @given(data=st.data())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
    def test_from_dict_roundtrip(self, data):
        """from_dict(dict) should recover the original OxideComposition."""
        comp = data.draw(oxide_composition_strategy())
        d = comp.__dict__
        reconstructed = OxideComposition.from_dict(d)
        for field_name in d:
            assert math.isclose(
                getattr(comp, field_name),
                getattr(reconstructed, field_name),
                rel_tol=1e-10,
            ), f"Mismatch in field {field_name}"


# ---------------------------------------------------------------------------
# 2. Coefficient properties
# ---------------------------------------------------------------------------

class TestCoefficientProperties:
    @given(F=f_strategy(), A=a_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=500)
    def test_k_constraint(self, F, A):
        """k1 + k2 + k3 + k4 + 2*k3 = 10 → k1 + k2 + 2*k3 + k4 = 10."""
        coeff = calculate_coefficients(F, A)
        total = coeff.k1 + coeff.k2 + 2 * coeff.k3 + coeff.k4
        assert math.isclose(total, 10.0, abs_tol=0.02), (
            f"k1+k2+2*k3+k4 = {total}, expected 10.0 "
            f"(k1={coeff.k1}, k2={coeff.k2}, k3={coeff.k3}, k4={coeff.k4})"
        )

    @given(F=f_strategy(), A=a_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=500)
    def test_F_and_A_clamped(self, F, A):
        """Output F and A must be rounded to 3 decimals and within [0,1]."""
        coeff = calculate_coefficients(F, A)
        assert 0.0 <= coeff.F <= 1.0
        assert 0.0 <= coeff.A <= 1.0
        # Verify rounding
        assert coeff.F == round(F, 3)
        assert coeff.A == round(A, 3)

    @given(F=f_strategy(), A=a_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=500)
    def test_k1_nonnegative(self, F, A):
        """k1 must be non-negative (clamped via max(0, ...))."""
        coeff = calculate_coefficients(F, A)
        assert coeff.k1 >= -0.001  # small tolerance for rounding

    @given(F=f_strategy(), A=a_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=500)
    def test_k2_nonnegative(self, F, A):
        """k2 must be non-negative."""
        coeff = calculate_coefficients(F, A)
        assert coeff.k2 >= -0.001

    def test_F_out_of_range_raises(self):
        """F < 0 or F > 1 must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_coefficients(-0.1, 0.5)
        with pytest.raises(ValueError):
            calculate_coefficients(1.5, 0.5)

    @given(F=f_strategy(), A=a_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_coefficients_are_frozen(self, F, A):
        """AdaptiveCoefficients is a frozen dataclass."""
        coeff = calculate_coefficients(F, A)
        with pytest.raises(AttributeError):
            coeff.k1 = 999


# ---------------------------------------------------------------------------
# 3. Calculator properties
# ---------------------------------------------------------------------------

class TestCalculatorProperties:
    def setup_method(self):
        self.calc = Calculator()

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_output_weights_are_finite(self, sample):
        """All mineral weight percentages must be finite (no NaN/inf)."""
        result = self.calc.calculate_single(sample)
        minerals = result.minerals_weight
        for field_name in minerals.__dict__:
            if field_name.startswith("_"):
                continue
            val = getattr(minerals, field_name)
            assert math.isfinite(val), f"minerals_weight.{field_name} = {val}"

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_normalized_to_100(self, sample):
        """After normalization, sum of weight% must be ~100."""
        result = self.calc.calculate_single(sample)
        minerals = result.minerals_weight
        total = sum(
            v for k, v in minerals.__dict__.items()
            if not k.startswith("_")
        )
        assert math.isclose(total, 100.0, abs_tol=0.5), f"Sum = {total}"

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_input_composition_preserved(self, sample):
        """Input composition must not be mutated by calculation."""
        orig_sio2 = sample.composition.sio2
        orig_al2o3 = sample.composition.al2o3
        result = self.calc.calculate_single(sample)
        assert result.input_composition.sio2 == orig_sio2
        assert result.input_composition.al2o3 == orig_al2o3

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_rock_type_valid(self, sample):
        """Rock type must be one of TYPE_1..TYPE_5."""
        result = self.calc.calculate_single(sample)
        assert isinstance(result.rock_type, RockType)
        assert 1 <= result.rock_type <= 5

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_coefficients_populated(self, sample):
        """All coefficient fields must be populated and finite."""
        result = self.calc.calculate_single(sample)
        c = result.coefficients
        for attr in ("k1", "k2", "k3", "k4", "F", "A"):
            val = getattr(c, attr)
            assert math.isfinite(val), f"coefficients.{attr} = {val}"

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_defect_is_dict(self, sample):
        """Defect must be a dict with string keys and finite float values."""
        result = self.calc.calculate_single(sample)
        assert isinstance(result.defect, dict)
        for k, v in result.defect.items():
            assert isinstance(k, str)
            assert math.isfinite(v), f"defect[{k!r}] = {v}"

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_anomalies_is_list(self, sample):
        """Anomalies must be a list (possibly empty)."""
        result = self.calc.calculate_single(sample)
        assert isinstance(result.anomalies, list)

    @given(sample=valid_sample_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
    def test_geo_params_present(self, sample):
        """Geo params must be present (non-None)."""
        result = self.calc.calculate_single(sample)
        assert result.geo_params is not None


# ---------------------------------------------------------------------------
# 4. Validation properties
# ---------------------------------------------------------------------------

class TestValidationProperties:
    def setup_method(self):
        self.config = CalculationConfig()

    @given(comp=oxide_composition_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_no_negative_warning_when_positive(self, comp):
        """If all values >= 0, no negative warning should appear."""
        is_valid, warnings = validate_sample(comp, self.config)
        neg_warnings = [w for w in warnings if "Отрицательное" in w]
        assert len(neg_warnings) == 0

    @given(
        field_name=st.sampled_from([
            "sio2", "al2o3", "feo", "mgo", "cao", "na2o", "k2o"
        ]),
        neg_value=st.floats(min_value=-100.0, max_value=-0.01, allow_nan=False, allow_infinity=False),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    def test_negative_value_detected(self, field_name, neg_value):
        """Negative oxide value should produce is_valid=False."""
        kwargs = {field_name: neg_value}
        comp = OxideComposition(**kwargs)
        is_valid, warnings = validate_sample(comp, self.config)
        assert not is_valid
        assert any("Отрицательное" in w for w in warnings)

    @given(comp=oxide_composition_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_nan_detected(self, comp):
        """NaN value should produce is_valid=False."""
        # Manually inject NaN
        comp = OxideComposition(
            sio2=float("nan"), al2o3=comp.al2o3, feo=comp.feo,
            mgo=comp.mgo, cao=comp.cao, na2o=comp.na2o, k2o=comp.k2o,
        )
        is_valid, warnings = validate_sample(comp, self.config)
        assert not is_valid

    def test_sum_in_range_no_warning(self):
        """Sum = 100% should produce no sum warning."""
        comp = OxideComposition(sio2=70.0, al2o3=15.0, feo=5.0, mgo=3.0, cao=2.0, na2o=2.0, k2o=3.0)
        is_valid, warnings = validate_sample(comp, self.config)
        sum_warnings = [w for w in warnings if "Сумма" in w]
        assert len(sum_warnings) == 0

    def test_sum_below_range_warning(self):
        """Sum < 98% should produce a sum warning."""
        comp = OxideComposition(sio2=50.0)
        is_valid, warnings = validate_sample(comp, self.config)
        sum_warnings = [w for w in warnings if "ниже" in w]
        assert len(sum_warnings) == 1


# ---------------------------------------------------------------------------
# 5. MineralComposition properties
# ---------------------------------------------------------------------------

class TestMineralCompositionProperties:
    @given(
        ab=oxide_strategy, an=oxide_strategy, or_=oxide_strategy,
        ill=oxide_strategy, chl=oxide_strategy, kn=oxide_strategy,
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
    def test_sum_formula_units(self, ab, an, or_, ill, chl, kn):
        """sum_formula_units() must equal the sum of all base mineral fields."""
        m = MineralComposition(ab=ab, an=an, or_=or_, ill=ill, chl=chl, kn=kn)
        expected = ab + an + or_ + ill + chl + kn
        assert math.isclose(m.sum_formula_units(), expected, rel_tol=1e-10)


# ---------------------------------------------------------------------------
# 6. Timeout property
# ---------------------------------------------------------------------------

class TestTimeoutProperties:
    def test_timeout_zero_raises(self):
        """timeout_seconds=0 should raise CalculationTimeoutError."""
        config = CalculationConfig(timeout_seconds=0)
        calc = Calculator(config=config)
        sample = Sample(name="test", composition=OxideComposition(sio2=70.0))
        with pytest.raises(CalculationTimeoutError):
            calc.calculate_single(sample)

    def test_timeout_negative_raises(self):
        """timeout_seconds=-1 should raise CalculationTimeoutError."""
        config = CalculationConfig(timeout_seconds=-1)
        calc = Calculator(config=config)
        sample = Sample(name="test", composition=OxideComposition(sio2=70.0))
        with pytest.raises(CalculationTimeoutError):
            calc.calculate_single(sample)
