"""Integration tests — charts, export, full pipeline."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.charts import BUILTIN_CHARTS, ChartData
from src.core.calculator import Calculator
from src.core.models import OxideComposition, Sample


def _make_chart_data(n: int = 3) -> ChartData:
    """Build synthetic ChartData for chart tests."""
    names = [f"Sample_{i}" for i in range(n)]
    data = ChartData(sample_names=names)
    rng = np.random.default_rng(42)
    for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]:
        data.oxides[field] = rng.uniform(0, 70, n)
    for field in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb"]:
        data.minerals_wt[field] = rng.uniform(0, 40, n)
    data.rock_types = [1, 3, 5][:n]
    return data


class TestChartRendering:
    """Test that all built-in charts render without errors."""

    @pytest.mark.parametrize("chart", BUILTIN_CHARTS, ids=[c.get_name() for c in BUILTIN_CHARTS])
    def test_chart_renders_to_file(self, chart):
        data = _make_chart_data()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
        try:
            chart.export(data, path, dpi=72)
            assert path.exists()
            assert path.stat().st_size > 0
        finally:
            path.unlink(missing_ok=True)


class TestExportPipeline:
    """Test full export pipeline: calculate → export."""

    def test_xlsx_export(self, sample_xlsx_path):
        if not sample_xlsx_path.exists():
            pytest.skip("MINLITH1.xlsx not found")
        from src.io.excel import load_samples, save_results
        samples = load_samples(sample_xlsx_path)
        calc = Calculator()
        results = [calc.calculate_single(s) for s in samples]
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            save_results(path, results)
            assert path.exists()
            assert path.stat().st_size > 100
        finally:
            path.unlink(missing_ok=True)

    def test_json_export(self, sample_xlsx_path):
        if not sample_xlsx_path.exists():
            pytest.skip("MINLITH1.xlsx not found")
        from src.io.excel import load_samples, save_results_json
        samples = load_samples(sample_xlsx_path)
        calc = Calculator()
        results = [calc.calculate_single(s) for s in samples]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            save_results_json(path, results)
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == len(results)
        finally:
            path.unlink(missing_ok=True)

    def test_csv_export(self, sample_xlsx_path):
        if not sample_xlsx_path.exists():
            pytest.skip("MINLITH1.xlsx not found")
        from src.io.excel import load_samples, save_results_csv
        samples = load_samples(sample_xlsx_path)
        calc = Calculator()
        results = [calc.calculate_single(s) for s in samples]
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            save_results_csv(path, results)
            content = path.read_text(encoding="utf-8")
            assert "Sample" in content
        finally:
            path.unlink(missing_ok=True)

    def test_pdf_report(self, sample_xlsx_path):
        if not sample_xlsx_path.exists():
            pytest.skip("MINLITH1.xlsx not found")
        from src.io.excel import load_samples
        from src.reports.pdf_generator import PDFGenerator
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        samples = load_samples(sample_xlsx_path)
        calc = Calculator()
        results = [calc.calculate_single(s) for s in samples]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES["standard"]()
            PDFGenerator(results).generate(path, template)
            assert path.exists()
            assert path.stat().st_size > 100
        finally:
            path.unlink(missing_ok=True)


class TestCalculationEdgeCases:
    """Test calculator with edge-case inputs."""

    def setup_method(self):
        self.calc = Calculator()

    def test_all_oxides_zero(self):
        s = Sample(name="empty", composition=OxideComposition())
        r = self.calc.calculate_single(s)
        assert r.defect is not None

    def test_only_sio2(self):
        s = Sample(name="pure_q", composition=OxideComposition(sio2=100.0))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.q > 90

    def test_high_k2o(self):
        s = Sample(name="high_k", composition=OxideComposition(
            sio2=55.0, al2o3=20.0, k2o=12.0, na2o=1.0))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.or_ > 30

    def test_high_na2o(self):
        s = Sample(name="high_na", composition=OxideComposition(
            sio2=68.0, al2o3=20.0, na2o=12.0, k2o=0.5))
        r = self.calc.calculate_single(s)
        assert r.minerals_weight.ab > 40

    def test_many_samples(self):
        samples = [
            Sample(name=f"synth_{i}", composition=OxideComposition(
                sio2=50 + i, al2o3=15 + i * 0.5, feo=5 + i, mgo=3 + i * 0.3))
            for i in range(20)
        ]
        results = [self.calc.calculate_single(s) for s in samples]
        assert len(results) == 20
        assert all(r.sample_name.startswith("synth_") for r in results)
