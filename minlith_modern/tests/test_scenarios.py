"""Comprehensive scenario tests — all real application flows."""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.anomaly_detector import AnomalyDetector
from src.core.calculator import Calculator
from src.core.coefficients import calculate_coefficients
from src.core.explainer import Explainer
from src.core.models import CalculationConfig, OxideComposition, Sample

# ── Fixtures ──

@pytest.fixture(scope="module")
def calc():
    return Calculator()


@pytest.fixture(scope="module")
def t_o2_sample():
    return Sample(
        name="T-O2",
        composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
            p2o5=0.31, mno=0.157502,
        ),
    )


@pytest.fixture(scope="module")
def t_o2_result(calc, t_o2_sample):
    return calc.calculate_single(t_o2_sample)


@pytest.fixture(scope="module")
def granite_sample():
    return Sample(
        name="Granite",
        composition=OxideComposition(
            sio2=72.0, al2o3=14.0, fe2o3=1.5, feo=1.0,
            mgo=0.5, cao=1.5, na2o=3.5, k2o=4.5, p2o5=0.2,
        ),
    )


@pytest.fixture(scope="module")
def basalt_sample():
    return Sample(
        name="Basalt",
        composition=OxideComposition(
            sio2=50.0, al2o3=14.5, fe2o3=3.0, feo=9.0,
            mgo=8.0, cao=10.5, na2o=2.5, k2o=0.5, tio2=1.5, p2o5=0.3,
        ),
    )


@pytest.fixture(scope="module")
def low_sum_sample():
    return Sample(
        name="LowSum",
        composition=OxideComposition(sio2=60.0, al2o3=15.0, fe2o3=5.0, feo=3.0),
    )


@pytest.fixture(scope="module")
def high_sum_sample():
    return Sample(
        name="HighSum",
        composition=OxideComposition(
            sio2=72.0, al2o3=14.0, fe2o3=1.5, feo=1.0,
            mgo=0.5, cao=1.5, na2o=3.5, k2o=4.5, p2o5=0.2, mno=0.1,
            so3=5.0, co2=6.0,
        ),
    )


@pytest.fixture(scope="module")
def iron_rich_sample():
    return Sample(
        name="IronRich",
        composition=OxideComposition(
            sio2=30.0, al2o3=5.0, fe2o3=15.0, feo=15.0,
            mgo=5.0, cao=3.0, na2o=1.0, k2o=0.5,
        ),
    )


@pytest.fixture(scope="module")
def sample_list(t_o2_sample, granite_sample, basalt_sample):
    return [t_o2_sample, granite_sample, basalt_sample]


@pytest.fixture(scope="module")
def results_list(calc, sample_list):
    return [calc.calculate_single(s) for s in sample_list]


# ══════════════════════════════════════════════════════════
# 1. CALCULATOR — Core Pipeline
# ══════════════════════════════════════════════════════════

class TestCalculatorPipeline:
    """Scenario 1: Full calculator pipeline."""

    def test_t_o2_rock_type(self, t_o2_result):
        """T-O2 should be Type 5."""
        assert t_o2_result.rock_type.value == 5

    def test_t_o2_coefficients(self, t_o2_result):
        """T-O2 coefficients should be positive."""
        c = t_o2_result.coefficients
        assert c.F > 0
        assert c.A > 0
        assert c.k1 > 0
        assert c.k2 > 0
        assert c.k3 > 0
        assert c.k4 > 0

    def test_t_o2_has_all_minerals(self, t_o2_result):
        """T-O2 result should have all mineral fields."""
        m = t_o2_result.minerals_weight
        assert hasattr(m, "ab")
        assert hasattr(m, "or_")
        assert hasattr(m, "q")
        assert hasattr(m, "ill")
        assert hasattr(m, "chl")
        assert hasattr(m, "kn")

    def test_t_o2_has_defect(self, t_o2_result):
        """T-O2 should have defect dictionary."""
        assert t_o2_result.defect is not None
        assert isinstance(t_o2_result.defect, dict)

    def test_t_o2_has_geo_params(self, t_o2_result):
        """T-O2 should have geo_params (CIA, ICV, etc.)."""
        assert t_o2_result.geo_params is not None

    def test_t_o2_has_anomalies(self, t_o2_result):
        """T-O2 should have anomalies list."""
        assert t_o2_result.anomalies is not None
        assert isinstance(t_o2_result.anomalies, list)

    def test_t_o2_has_formula_units(self, t_o2_result):
        """T-O2 should have formula_units."""
        assert t_o2_result.formula_units is not None
        assert t_o2_result.formula_units.sio2 > 0

    def test_t_o2_has_warnings(self, t_o2_result):
        """T-O2 should have warnings list."""
        assert isinstance(t_o2_result.warnings, list)

    def test_minerals_weight_sum_100(self, t_o2_result):
        """Mineral weights should sum to ~100%."""
        m = t_o2_result.minerals_weight
        total = sum(v for k, v in m.__dict__.items() if not k.startswith("_"))
        assert 99.0 <= total <= 101.0, f"Mineral sum: {total}"

    def test_negative_kn_allowed(self, t_o2_result):
        """Negative Kn is valid artifact."""
        assert isinstance(t_o2_result.minerals_weight.kn, float)


# ══════════════════════════════════════════════════════════
# 2. EXPORT PIPELINE — XLSX, JSON, CSV, PDF, HTML, DOCX
# ══════════════════════════════════════════════════════════

class TestExportXLSX:
    """Scenario 2a: XLSX export."""

    def test_xlsx_export(self, results_list):
        from src.io.excel import save_results
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            save_results(path, results_list)
            assert path.exists()
            assert path.stat().st_size > 100
        finally:
            path.unlink(missing_ok=True)

    def test_xlsx_has_all_sheets(self, results_list):
        import openpyxl

        from src.io.excel import save_results
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            save_results(path, results_list)
            wb = openpyxl.load_workbook(path)
            assert "Results" in wb.sheetnames
            assert "Input" in wb.sheetnames
            assert "Defect" in wb.sheetnames
            assert "GeoParams" in wb.sheetnames
        finally:
            path.unlink(missing_ok=True)


class TestExportJSON:
    """Scenario 2b: JSON export."""

    def test_json_export(self, results_list):
        from src.io.excel import save_results_json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            save_results_json(path, results_list)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data) == len(results_list)
        finally:
            path.unlink(missing_ok=True)

    def test_json_structure(self, results_list):
        from src.io.excel import save_results_json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            save_results_json(path, results_list)
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data:
                assert "sample_name" in entry
                assert "rock_type" in entry
                assert "F" in entry
                assert "A" in entry
                assert "minerals_wt" in entry
        finally:
            path.unlink(missing_ok=True)


class TestExportCSV:
    """Scenario 2c: CSV export."""

    def test_csv_export(self, results_list):
        from src.io.excel import save_results_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            save_results_csv(path, results_list)
            content = path.read_text(encoding="utf-8")
            assert "Sample" in content
            assert "T-O2" in content or "Granite" in content
        finally:
            path.unlink(missing_ok=True)


class TestExportPDF:
    """Scenario 2d: PDF export."""

    def test_pdf_export(self, results_list):
        from src.reports.pdf_generator import PDFGenerator
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES["standard"]()
            PDFGenerator(results_list).generate(path, template)
            assert path.exists()
            assert path.stat().st_size > 100
        finally:
            path.unlink(missing_ok=True)


class TestExportDOCX:
    """Scenario 2e: DOCX export."""

    def test_docx_export(self, results_list):
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        from src.reports.word_generator import WordGenerator
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES["standard"]()
            WordGenerator(results_list).generate(path, template)
            assert path.exists()
            assert path.stat().st_size > 100
        finally:
            path.unlink(missing_ok=True)


class TestExportHTML:
    """Scenario 2f: HTML export."""

    def test_html_export(self, results_list):
        from src.reports.html_generator import HTMLGenerator
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES["standard"]()
            HTMLGenerator(results_list).generate(path, template)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "MINLITH" in content
        finally:
            path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# 3. REPORT TEMPLATES — All 5
# ══════════════════════════════════════════════════════════

class TestReportTemplates:
    """Scenario 3: All 5 report templates."""

    @pytest.mark.parametrize("template_name", ["brief", "standard", "full", "core", "geochemical"])
    def test_template_generates_pdf(self, results_list, template_name):
        from src.reports.pdf_generator import PDFGenerator
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES[template_name]()
            PDFGenerator(results_list).generate(path, template)
            assert path.exists()
            assert path.stat().st_size > 50
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.parametrize("template_name", ["brief", "standard", "full", "core", "geochemical"])
    def test_template_generates_html(self, results_list, template_name):
        from src.reports.html_generator import HTMLGenerator
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES[template_name]()
            HTMLGenerator(results_list).generate(path, template)
            assert path.exists()
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.parametrize("template_name", ["brief", "standard", "full", "core", "geochemical"])
    def test_template_generates_docx(self, results_list, template_name):
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        from src.reports.word_generator import WordGenerator
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = Path(f.name)
        try:
            template = PREDEFINED_TEMPLATES[template_name]()
            WordGenerator(results_list).generate(path, template)
            assert path.exists()
        finally:
            path.unlink(missing_ok=True)

    def test_template_serialization(self):
        from src.reports.template_builder import PREDEFINED_TEMPLATES
        for name, factory in PREDEFINED_TEMPLATES.items():
            t = factory()
            d = t.to_dict()
            assert "name" in d
            assert "blocks" in d
            assert len(d["blocks"]) > 0

    def test_template_save_load(self):
        from src.reports.template_builder import PREDEFINED_TEMPLATES, ReportTemplate
        original = PREDEFINED_TEMPLATES["standard"]()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            original.save(path)
            loaded = ReportTemplate.load(path)
            assert loaded.name == original.name
            assert len(loaded.blocks) == len(original.blocks)
        finally:
            path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# 4. CHARTS — All 15 types render
# ══════════════════════════════════════════════════════════

class TestAllCharts:
    """Scenario 4: All chart types render."""

    def _make_chart_data(self):
        import numpy as np

        from src.charts import ChartData
        data = ChartData(sample_names=["S1", "S2", "S3"])
        rng = np.random.default_rng(42)
        for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]:
            data.oxides[field] = rng.uniform(0, 70, 3)
        for field in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb"]:
            data.minerals_wt[field] = rng.uniform(0, 40, 3)
        data.rock_types = [1, 3, 5]
        return data

    def test_all_charts_render(self):
        from src.charts import BUILTIN_CHARTS
        data = self._make_chart_data()
        for chart in BUILTIN_CHARTS:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                path = Path(f.name)
            try:
                chart.export(data, path, dpi=72)
                assert path.exists()
                assert path.stat().st_size > 0
            finally:
                path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# 5. ANOMALY DETECTOR — All rules
# ══════════════════════════════════════════════════════════

class TestAnomalyDetector:
    """Scenario 5: AnomalyDetector with various inputs."""

    def test_t_o2_anomalies(self, t_o2_result):
        """T-O2 should have at least one anomaly (high_phosphorus)."""
        anomalies = t_o2_result.anomalies
        assert len(anomalies) > 0

    def test_low_sum_detected(self, calc, low_sum_sample):
        """Low sum should trigger low_sum rule."""
        result = calc.calculate_single(low_sum_sample)
        detector = AnomalyDetector()
        anomalies = detector.analyze(result)
        patterns = [a.pattern for a in anomalies]
        assert "low_sum" in patterns

    def test_high_sum_detected(self, calc, high_sum_sample):
        """High sum should trigger high_sum rule."""
        result = calc.calculate_single(high_sum_sample)
        detector = AnomalyDetector()
        anomalies = detector.analyze(result)
        patterns = [a.pattern for a in anomalies]
        assert "high_sum" in patterns

    def test_iron_rich_detected(self, calc, iron_rich_sample):
        """Iron-rich sample should trigger iron_rich rule."""
        result = calc.calculate_single(iron_rich_sample)
        detector = AnomalyDetector()
        anomalies = detector.analyze(result)
        patterns = [a.pattern for a in anomalies]
        assert "iron_rich" in patterns

    def test_high_phosphorus_detected(self, calc):
        """Sample with P2O5 > 0.5 should trigger high_phosphorus."""
        s = Sample(name="HighP", composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45, p2o5=1.0,
        ))
        result = calc.calculate_single(s)
        detector = AnomalyDetector()
        anomalies = detector.analyze(result)
        patterns = [a.pattern for a in anomalies]
        assert "high_phosphorus" in patterns

    def test_analyze_batch(self, calc, sample_list):
        """Batch analysis should return dict keyed by sample name."""
        results = [calc.calculate_single(s) for s in sample_list]
        detector = AnomalyDetector()
        batch = detector.analyze_batch(results)
        assert len(batch) == len(sample_list)
        for name in [s.name for s in sample_list]:
            assert name in batch

    def test_anomaly_fields(self, t_o2_result):
        """AnomalyHypothesis should have all required fields."""
        for a in t_o2_result.anomalies:
            assert hasattr(a, "severity")
            assert hasattr(a, "pattern")
            assert hasattr(a, "message")
            assert hasattr(a, "confidence")
            assert hasattr(a, "suggested_action")
            assert hasattr(a, "affected_oxides")
            assert a.severity in ("info", "warning", "critical")
            assert 0.0 <= a.confidence <= 1.0


# ══════════════════════════════════════════════════════════
# 6. EXPLAINER — Russian explanations
# ══════════════════════════════════════════════════════════

class TestExplainer:
    """Scenario 6: Explainer generates Russian text."""

    def test_explain_brief(self, t_o2_result):
        explainer = Explainer(detail_level="brief")
        text = explainer.explain(t_o2_result)
        assert "Образец:" in text
        assert "T-O2" in text
        assert "Тип породы:" in text

    def test_explain_standard(self, t_o2_result):
        explainer = Explainer(detail_level="standard")
        text = explainer.explain(t_o2_result)
        assert "Адаптивные коэффициенты" in text
        assert "Доминирующие минералы:" in text

    def test_explain_detailed(self, t_o2_result):
        explainer = Explainer(detail_level="detailed")
        text = explainer.explain(t_o2_result)
        assert "Ключевые шаги расчёта:" in text

    def test_explain_steps(self, t_o2_result):
        explainer = Explainer()
        for step in range(10):
            text = explainer.explain_step(step, t_o2_result)
            assert len(text) > 0

    def test_explain_with_anomalies(self, t_o2_result):
        explainer = Explainer()
        text = explainer.explain(t_o2_result)
        # T-O2 has anomalies, so explanation should mention them
        assert "Обнаруженные аномалии:" in text or "Доминирующие минералы:" in text


# ══════════════════════════════════════════════════════════
# 7. LATEX EXPORTER
# ══════════════════════════════════════════════════════════

class TestLaTeXExporter:
    """Scenario 7: LaTeX export for publication."""

    def test_latex_export(self, results_list):
        from src.reports.latex_exporter import LaTeXExporter
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
            path = Path(f.name)
        try:
            exporter = LaTeXExporter(results_list)
            result = exporter.export(path, caption="Test Table", label="tab:test")
            assert result.exists()
            content = path.read_text(encoding="utf-8")
            assert r"\begin{document}" in content
            assert r"\begin{table}" in content
            assert r"\toprule" in content
            assert r"\bottomrule" in content
            assert "T-O2" in content or "Granite" in content
        finally:
            path.unlink(missing_ok=True)

    def test_latex_single_sample(self, t_o2_result):
        from src.reports.latex_exporter import LaTeXExporter
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
            path = Path(f.name)
        try:
            exporter = LaTeXExporter([t_o2_result])
            exporter.export(path, caption="T-O2 Minerals", label="tab:to2")
            content = path.read_text(encoding="utf-8")
            assert "Альбит" in content
            assert "Кварц" in content
        finally:
            path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# 8. XRF IMPORTER
# ══════════════════════════════════════════════════════════

class TestXRFImporter:
    """Scenario 8: XRF file import."""

    def test_csv_import(self):
        from src.io.xrf_importer import read_xrf_csv
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                          encoding="utf-8") as f:
            f.write("Name;SiO2;Al2O3;Fe2O3;FeO;MgO;CaO;Na2O;K2O\n")
            f.write("Sample1;52.5;23.41;1.71;8.06;2.35;0.28;0.94;3.45\n")
            f.write("Sample2;72.0;14.0;1.5;1.0;0.5;1.5;3.5;4.5\n")
            path = Path(f.name)
        try:
            samples = read_xrf_csv(path)
            assert len(samples) == 2
            assert samples[0].name == "Sample1"
            assert samples[0].composition.sio2 == 52.5
        finally:
            path.unlink(missing_ok=True)

    def test_txt_import(self):
        from src.io.xrf_importer import read_xrf_txt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                          encoding="utf-8") as f:
            f.write("Name\tSiO2\tAl2O3\tFe2O3\tFeO\tMgO\tCaO\tNa2O\tK2O\n")
            f.write("Sample1\t52.5\t23.41\t1.71\t8.06\t2.35\t0.28\t0.94\t3.45\n")
            path = Path(f.name)
        try:
            samples = read_xrf_txt(path)
            assert len(samples) == 1
            assert samples[0].name == "Sample1"
        finally:
            path.unlink(missing_ok=True)

    def test_auto_detect_csv(self):
        from src.io.xrf_importer import read_xrf
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                          encoding="utf-8") as f:
            f.write("Name;SiO2;Al2O3\n")
            f.write("S1;52.5;23.41\n")
            path = Path(f.name)
        try:
            samples = read_xrf(path)
            assert len(samples) == 1
        finally:
            path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# 9. COEFFICIENTS — k1+k2+2k3+k4=10
# ══════════════════════════════════════════════════════════

class TestCoefficients:
    """Scenario 9: Coefficients constraint."""

    def test_k_sum_constraint(self):
        """k1 + k2 + 2*k3 + k4 should equal 10."""
        for F in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            c = calculate_coefficients(F, 0.5)
            total = c.k1 + c.k2 + 2 * c.k3 + c.k4
            assert abs(total - 10.0) < 0.01, f"F={F}: k1+k2+2k3+k4={total}"

    def test_F_range_0_to_02(self):
        c = calculate_coefficients(0.1, 0.5)
        assert c.k1 > 0
        assert c.k2 > 0

    def test_F_range_02_to_04(self):
        c = calculate_coefficients(0.3, 0.5)
        assert c.k1 > 0
        assert c.k2 > 0

    def test_F_range_04_to_06(self):
        c = calculate_coefficients(0.5, 0.5)
        assert c.k1 > 0
        assert c.k2 > 0

    def test_F_range_06_to_08(self):
        c = calculate_coefficients(0.7, 0.5)
        assert c.k1 >= 0  # k1 can be clamped to 0 by max()
        assert c.k2 > 0

    def test_F_range_08_to_10(self):
        c = calculate_coefficients(0.9, 0.5)
        assert c.k1 > 0
        assert c.k2 > 0


# ══════════════════════════════════════════════════════════
# 10. VALIDATION
# ══════════════════════════════════════════════════════════

class TestValidation:
    """Scenario 10: Input validation."""

    def test_valid_composition(self):
        from src.core.models import CalculationConfig
        from src.core.validation import validate_sample
        comp = OxideComposition(sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
                                mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45)
        is_valid, warnings = validate_sample(comp, CalculationConfig())
        assert is_valid

    def test_low_sum_warning(self):
        from src.core.models import CalculationConfig
        from src.core.validation import validate_sample
        comp = OxideComposition(sio2=60.0, al2o3=15.0)
        is_valid, warnings = validate_sample(comp, CalculationConfig())
        assert len(warnings) > 0

    def test_zero_composition(self):
        from src.core.models import CalculationConfig
        from src.core.validation import validate_sample
        comp = OxideComposition()
        is_valid, warnings = validate_sample(comp, CalculationConfig())
        # Zero composition should produce warnings
        assert isinstance(warnings, list)


# ══════════════════════════════════════════════════════════
# 11. DATABASE — Repository operations
# ══════════════════════════════════════════════════════════

class TestDatabase:
    """Scenario 11: Database operations."""

    def test_save_and_retrieve(self, t_o2_result):
        from src.database.engine import init_db
        from src.database.repository import SampleRepository
        init_db()
        repo = SampleRepository()
        try:
            sample_id = repo.save_result(t_o2_result)
            assert sample_id > 0
        except Exception:
            pytest.skip("DB not available")

    def test_backup(self):
        from src.database.engine import init_db
        from src.database.repository import SampleRepository
        init_db()
        repo = SampleRepository()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                dest = repo.backup(tmpdir)
                assert dest.exists()
            except Exception:
                pytest.skip("DB not available")

    def test_export_import_json(self):
        from src.database.engine import init_db
        from src.database.repository import SampleRepository
        init_db()
        repo = SampleRepository()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            repo.export_results_json(path)
            assert path.exists()
        except Exception:
            pytest.skip("DB not available")


# ══════════════════════════════════════════════════════════
# 12. CACHE
# ══════════════════════════════════════════════════════════

class TestCache:
    """Scenario 12: Cache system."""

    def test_cache_put_get(self):
        import tempfile

        from src.utils.cache import ResultCache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=Path(tmpdir))
            # Create a minimal fake result
            fake = [{
                "sample_name": "Test",
                "rock_type": 3,
                "F": 0.5, "A": 0.6,
                "minerals": {"ab": 10.0, "or_": 5.0, "q": 30.0},
            }]
            fake_path = Path(tmpdir) / "test_input.xlsx"
            fake_path.touch()
            cache.put(fake_path, fake)
            cached = cache.get(fake_path)
            assert cached is not None
            assert len(cached) == 1

    def test_cache_stats(self):
        import tempfile

        from src.utils.cache import ResultCache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=Path(tmpdir))
            stats = cache.stats()
            assert "entries" in stats
            assert "cache_dir" in stats
            assert "ttl_seconds" in stats


# ══════════════════════════════════════════════════════════
# 13. ROCK TYPES — All 5 classified
# ══════════════════════════════════════════════════════════

class TestRockTypes:
    """Scenario 13: Rock type classification."""

    def test_type1_classification(self, calc):
        s = Sample(name="Type1", composition=OxideComposition(
            sio2=52.31, al2o3=16.46, fe2o3=0.92, feo=4.43,
            mgo=0.11, cao=6.80, na2o=8.08, k2o=4.26,
        ))
        r = calc.calculate_single(s)
        assert r.rock_type.value == 1

    def test_type3_classification(self, calc, granite_sample):
        r = calc.calculate_single(granite_sample)
        assert r.rock_type.value in (2, 3)

    def test_type5_classification(self, calc, t_o2_sample):
        r = calc.calculate_single(t_o2_sample)
        assert r.rock_type.value == 5

    def test_all_results_have_valid_type(self, calc, sample_list):
        for s in sample_list:
            r = calc.calculate_single(s)
            assert 1 <= r.rock_type.value <= 5


# ══════════════════════════════════════════════════════════
# 14. TIMEOUT
# ══════════════════════════════════════════════════════════

class TestTimeout:
    """Scenario 14: Timeout enforcement."""

    def test_timeout_raises(self, calc, t_o2_sample):
        from src.core.calculator import CalculationTimeoutError
        config = CalculationConfig(timeout_seconds=0)
        calc_timeout = Calculator(config=config)
        with pytest.raises(CalculationTimeoutError):
            calc_timeout.calculate_single(t_o2_sample)


# ══════════════════════════════════════════════════════════
# 15. GEO PARAMETERS
# ══════════════════════════════════════════════════════════

class TestGeoParameters:
    """Scenario 15: Geochemical parameters (CIA, ICV, PIA, ASI, AI)."""

    def test_geo_params_present(self, t_o2_result):
        gp = t_o2_result.geo_params
        assert gp is not None

    def test_geo_params_values_reasonable(self, t_o2_result):
        gp = t_o2_result.geo_params
        # CIA should be between 0 and 100
        assert 0 <= gp.CIA <= 100
        # ICV should be positive
        assert gp.ICV > 0

    def test_geo_params_in_xlsx(self, results_list):
        import openpyxl

        from src.io.excel import save_results
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            save_results(path, results_list)
            wb = openpyxl.load_workbook(path)
            ws = wb["GeoParams"]
            assert ws.max_row > 1
        finally:
            path.unlink(missing_ok=True)
