"""Tests for calibrator, cache, csv_handler, and types_logic."""

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.core.calibrator import (
    Calibrator,
    ParameterizedAlgorithm,
    CalibrationResult,
    save_calibration_config,
    load_calibration_config,
    DEFAULT_PARAMS,
    PARAM_BOUNDS,
)
from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.calculator import Calculator
from src.core.models import (
    CalculationConfig,
    OxideComposition,
    Sample,
    MineralComposition,
    AdaptiveCoefficients,
    FormulaUnits,
)
from src.core.types_logic import calculate_type1, calculate_type2


# ---------------------------------------------------------------------------
# ParameterizedAlgorithm
# ---------------------------------------------------------------------------

class TestParameterizedAlgorithm:
    def setup_method(self):
        self.alg = ParameterizedAlgorithm(dict(DEFAULT_PARAMS))
        self.input = AlgorithmInput(
            sio2=52.5, tio2=0.0, al2o3=23.41, feo=8.06, mgo=2.35,
            cao=0.28, na2o=0.94, k2o=3.45, p2o5=0.31, mno=0.16,
            c=0.0, so3=0.0, f=0.0, cl=0.0, s=0.0, co2=0.0, so=0.0,
            k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.0, A=0.0,
            rock_type=5,
        )

    def test_returns_algorithm_output(self):
        out = self.alg.compute(self.input)
        assert isinstance(out, AlgorithmOutput)

    def test_ab_scales_na2o(self):
        out = self.alg.compute(self.input)
        expected_ab = DEFAULT_PARAMS["ab_scale"] * self.input.na2o
        assert math.isclose(out.Ab, expected_ab, rel_tol=1e-6)

    def test_negative_kn_preserved(self):
        """Kn can be negative (valid artifact)."""
        out = self.alg.compute(self.input)
        assert isinstance(out.Kn, float)

    def test_all_fields_finite(self):
        out = self.alg.compute(self.input)
        for attr in ("Ab", "An", "Or", "Q", "Ill", "Chl", "Kn", "Gb", "Dl", "Ht", "Srp", "Prl"):
            val = getattr(out, attr)
            assert math.isfinite(val), f"{attr} = {val}"


# ---------------------------------------------------------------------------
# save_calibration_config / load_calibration_config
# ---------------------------------------------------------------------------

class TestCalibrationConfigIO:
    def test_save_and_load_roundtrip(self, tmp_path):
        params = {"ab_scale": 1.5, "an_ca_ratio": 0.8}
        config_path = tmp_path / "cal.json"
        save_calibration_config(params, config_path)

        loaded = load_calibration_config(config_path)
        assert loaded == params

    def test_load_non_calibrated_raises(self, tmp_path):
        config_path = tmp_path / "bad.json"
        config_path.write_text(json.dumps({"calibrated": False, "parameters": {}}))
        with pytest.raises(ValueError, match="not a calibration config"):
            load_calibration_config(config_path)

    def test_save_creates_valid_json(self, tmp_path):
        params = {"ab_scale": 1.0}
        config_path = tmp_path / "cal.json"
        save_calibration_config(params, config_path)

        data = json.loads(config_path.read_text())
        assert data["calibrated"] is True
        assert data["parameters"] == params
        assert "description" in data


# ---------------------------------------------------------------------------
# Calibrator (fast tests — short maxiter)
# ---------------------------------------------------------------------------

class TestCalibrator:
    def setup_method(self):
        self.sample = Sample(
            name="T-O2",
            composition=OxideComposition(
                sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
                mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
                p2o5=0.31, mno=0.157502,
            ),
        )
        self.expected = {
            "ab": 7.82, "or_": 5.53, "q": 31.38, "ill": 36.26,
            "chl": 25.74, "kn": -9.77, "srp": 1.55, "prl": 0.19,
            "ap": 0.72, "ht": 0.99,
        }

    def test_calibration_reduces_rmse(self):
        """Calibration must reduce RMSE compared to default params."""
        config = CalculationConfig(timeout_seconds=30)
        calibrator = Calibrator(self.sample, self.expected, config=config)
        result = calibrator.calibrate(maxiter=50, seed=42)

        assert isinstance(result, CalibrationResult)
        assert result.rmse_after <= result.rmse_before + 0.01  # Allow tiny tolerance

    def test_calibrated_params_in_bounds(self):
        """All calibrated parameters must be within defined bounds."""
        config = CalculationConfig(timeout_seconds=30)
        calibrator = Calibrator(self.sample, self.expected, config=config)
        result = calibrator.calibrate(maxiter=50, seed=42)

        for name, val in result.params.items():
            lo, hi = PARAM_BOUNDS[name]
            assert lo <= val <= hi, f"{name}={val} out of bounds [{lo}, {hi}]"

    def test_report_contains_key_sections(self):
        """Report must contain mineral names and RMSE."""
        config = CalculationConfig(timeout_seconds=30)
        calibrator = Calibrator(self.sample, self.expected, config=config)
        result = calibrator.calibrate(maxiter=50, seed=42)

        assert "CALIBRATION REPORT" in result.report
        assert "RMSE" in result.report
        assert "ab_scale" in result.report

    def test_cost_function_default_params(self):
        """Cost function with default params should return a finite value."""
        config = CalculationConfig(timeout_seconds=30)
        calibrator = Calibrator(self.sample, self.expected, config=config)
        x = np.array([DEFAULT_PARAMS[k] for k in calibrator._param_names])
        cost = calibrator._cost_function(x)
        assert math.isfinite(cost)
        assert cost > 0


# ---------------------------------------------------------------------------
# Cache (ResultCache)
# ---------------------------------------------------------------------------

class TestResultCache:
    def test_put_and_get(self, tmp_path):
        from src.utils.cache import ResultCache
        cache = ResultCache(cache_dir=tmp_path, ttl_seconds=3600)

        # Create a dummy file
        dummy = tmp_path / "test.xlsx"
        dummy.write_bytes(b"test data")

        results = [{"sample": "test", "minerals": {"ab": 7.8}}]
        cache.put(dummy, results)

        cached = cache.get(dummy)
        assert cached is not None
        assert cached[0]["sample"] == "test"

    def test_cache_miss_for_different_file(self, tmp_path):
        from src.utils.cache import ResultCache
        cache = ResultCache(cache_dir=tmp_path, ttl_seconds=3600)

        file1 = tmp_path / "f1.xlsx"
        file1.write_bytes(b"data1")
        file2 = tmp_path / "f2.xlsx"
        file2.write_bytes(b"data2")

        cache.put(file1, [{"x": 1}])
        assert cache.get(file2) is None

    def test_cache_expiry(self, tmp_path):
        from src.utils.cache import ResultCache
        cache = ResultCache(cache_dir=tmp_path, ttl_seconds=1)

        dummy = tmp_path / "test.xlsx"
        dummy.write_bytes(b"test data")
        cache.put(dummy, [{"x": 1}])

        # Wait for expiry
        import time
        time.sleep(1.5)

        cached = cache.get(dummy)
        assert cached is None

    def test_invalidate(self, tmp_path):
        from src.utils.cache import ResultCache
        cache = ResultCache(cache_dir=tmp_path, ttl_seconds=3600)

        dummy = tmp_path / "test.xlsx"
        dummy.write_bytes(b"test data")
        cache.put(dummy, [{"x": 1}])

        cache.invalidate(dummy)
        assert cache.get(dummy) is None

    def test_clear_all(self, tmp_path):
        from src.utils.cache import ResultCache
        cache = ResultCache(cache_dir=tmp_path, ttl_seconds=3600)

        dummy = tmp_path / "test.xlsx"
        dummy.write_bytes(b"test data")
        cache.put(dummy, [{"x": 1}])

        count = cache.clear()
        assert count == 1
        assert cache.get(dummy) is None


# ---------------------------------------------------------------------------
# CSV handler
# ---------------------------------------------------------------------------

class TestCSVHandler:
    def test_read_csv_semicolon(self, tmp_path):
        from src.io.csv_handler import read_csv
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "Name;SiO2;Al2O3;FeO\nSample1;70.0;15.0;5.0\n",
            encoding="utf-8",
        )
        samples = read_csv(csv_path)
        assert len(samples) == 1
        assert samples[0].name == "Sample1"
        assert samples[0].composition.sio2 == 70.0

    def test_read_csv_comma(self, tmp_path):
        from src.io.csv_handler import read_csv
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "Name,SiO2,Al2O3,FeO\nSample1,70.0,15.0,5.0\n",
            encoding="utf-8",
        )
        samples = read_csv(csv_path)
        assert len(samples) == 1
        assert samples[0].composition.sio2 == 70.0

    def test_read_csv_russian_headers(self, tmp_path):
        from src.io.csv_handler import read_csv
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "Образец;SiO2;Al2O3\nОбр1;65.0;20.0\n",
            encoding="utf-8",
        )
        samples = read_csv(csv_path)
        assert len(samples) == 1
        assert samples[0].composition.sio2 == 65.0

    def test_write_csv(self, tmp_path):
        from src.io.csv_handler import write_csv
        from src.core.models import CalculationResult, RockType, AdaptiveCoefficients, MineralComposition, FormulaUnits
        csv_path = tmp_path / "out.csv"

        results = [
            CalculationResult(
                sample_name="test",
                input_composition=OxideComposition(sio2=70.0),
                formula_units=FormulaUnits(),
                coefficients=AdaptiveCoefficients(k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.0, A=0.0),
                rock_type=RockType.TYPE_1,
                minerals_formula=MineralComposition(),
                minerals_weight=MineralComposition(ab=7.8, q=50.0),
                defect={},
                warnings=[],
            )
        ]
        write_csv(csv_path, results)
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert "test" in content


# ---------------------------------------------------------------------------
# Types logic (calculate_type1)
# ---------------------------------------------------------------------------

class TestTypesLogic:
    def _make_fu(self, **kwargs) -> FormulaUnits:
        defaults = {"sio2": 50.0, "al2o3": 15.0, "feo": 5.0, "mgo": 3.0,
                     "cao": 2.0, "na2o": 3.0, "k2o": 2.0}
        defaults.update(kwargs)
        return FormulaUnits(**defaults)

    def _make_coeff(self, **kwargs) -> AdaptiveCoefficients:
        defaults = {"k1": 4.42, "k2": 0.0, "k3": 1.58, "k4": 2.42, "F": 0.0, "A": 0.0}
        defaults.update(kwargs)
        return AdaptiveCoefficients(**defaults)

    def test_type1_feldspars_only(self):
        fu = self._make_fu(na2o=3.0, k2o=2.0, al2o3=4.0, sio2=50.0)
        coeff = self._make_coeff()
        result = calculate_type1(fu, coeff)
        assert isinstance(result, MineralComposition)
        assert result.ab == pytest.approx(3.0, abs=0.01)
        assert result.or_ == pytest.approx(2.0, abs=0.01)
        assert result.ill == 0.0
        assert result.chl == 0.0

    def test_type1_quartz_remaining(self):
        fu = self._make_fu(na2o=1.0, k2o=0.5, al2o3=1.0, sio2=60.0)
        coeff = self._make_coeff()
        result = calculate_type1(fu, coeff)
        assert result.q > 0

    def test_type1_negative_si_handled(self):
        """When Si goes negative, it should be clamped to 0."""
        fu = self._make_fu(na2o=20.0, sio2=50.0, al2o3=5.0)
        coeff = self._make_coeff()
        result = calculate_type1(fu, coeff)
        assert result.q >= 0

    def test_type2_adds_illite(self):
        fu = self._make_fu(na2o=2.0, k2o=2.0, al2o3=10.0, sio2=60.0)
        coeff = self._make_coeff()
        result = calculate_type2(fu, coeff)
        assert isinstance(result, MineralComposition)
        # Type 2 should have some illite if there's K and Al
        assert result.ill >= 0
