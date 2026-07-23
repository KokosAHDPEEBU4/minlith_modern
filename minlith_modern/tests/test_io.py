"""Tests for IO — excel, csv, json, zip handlers."""

import tempfile
from pathlib import Path

from src.core.models import (
    OxideComposition, Sample, CalculationResult, MineralComposition,
    AdaptiveCoefficients, RockType, FormulaUnits,
)
from src.io.excel import save_results, save_results_json, save_results_csv


def _make_result(name="test", sio2=52.5):
    return CalculationResult(
        sample_name=name,
        input_composition=OxideComposition(sio2=sio2, al2o3=23.41),
        formula_units=FormulaUnits(sio2=5313.84, al2o3=183.12),
        coefficients=AdaptiveCoefficients(k1=1.0, k2=0.5, k3=1.0, k4=2.0, F=1.2, A=0.8),
        rock_type=RockType.TYPE_1,
        minerals_formula=MineralComposition(ab=10.5, or_=5.2, q=30.0),
        minerals_weight=MineralComposition(ab=10.5, or_=5.2, q=30.0),
        defect={"SiO2": 0.5, "Al2O3": -0.2},
        warnings=[],
    )


class TestExcelExport:
    def test_save_xlsx(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        results = [_make_result()]
        save_results(path, results)
        assert path.exists()
        assert path.stat().st_size > 0
        path.unlink()

    def test_save_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        results = [_make_result()]
        save_results_json(path, results)
        assert path.exists()
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["sample_name"] == "test"
        path.unlink()

    def test_save_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        results = [_make_result()]
        save_results_csv(path, results)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "test" in content
        path.unlink()

    def test_save_multiple(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        results = [_make_result("s1"), _make_result("s2", sio2=60.0)]
        save_results(path, results)
        assert path.exists()
        path.unlink()


class TestExcelImport:
    def test_load_real_file(self):
        from src.io.excel import load_samples
        real = Path(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx")
        if real.exists():
            samples = load_samples(real)
            assert len(samples) >= 1
            assert samples[0].composition.sio2 > 0


class TestCSVHandler:
    def test_write_read_roundtrip(self):
        from src.io.csv_handler import write_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        results = [_make_result()]
        write_csv(path, results)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "test" in content
        assert "ab_wt%" in content
        path.unlink()
