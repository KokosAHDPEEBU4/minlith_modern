"""Тесты структурированной траектории веток (excel_parity.branches).

Проверяют, что:
  * зеркальные функции ``coefficient_band``/``classify_conditions`` не
    расходятся с ``coefficients``/``classify``;
  * ``ExcelRun.path`` содержит полосу коэффициентов, тип породы, подписи
    ветки типа и VI этапа;
  * трассировка может принять маршрут (``DebugTraceCollector``).
"""
import json
from pathlib import Path

import pytest

from src.core.excel_parity.branches import (
    COEFFICIENT_BAND_INFO,
    ROCK_TYPE_INFO,
    STAGE_VI_INFO,
    BranchPath,
)
from src.core.excel_parity.runner import run_sample
from src.core.excel_parity.stage0 import (
    classify,
    classify_conditions,
    coefficient_band,
    coefficients,
    f_and_a,
    formula_units,
)

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"
NAMES = ["BK-1", "T-O2",
         "arkose_t1", "granite_t2", "basalt_t3", "quartzite_t4", "highal_t5"]


@pytest.fixture(scope="module")
def oxides():
    multi = json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))
    one = json.loads((DATA / "reference.json").read_text(encoding="utf-8"))
    ox = {name: rec["input"] for name, rec in multi.items()}
    ox["BK-1"] = one["BK-1"]["input"]
    ox["T-O2"] = one["T-O2"]["input"]
    return ox


# ── Зеркальные функции ────────────────────────────────────────────

@pytest.mark.parametrize("f,a,band", [
    (0.10, 0.50, "H5"),
    (0.21, 0.50, "J5"),
    (0.30, 0.50, "J5"),
    (0.60, 0.50, "L5"),
    (0.75, 0.50, "H12"),
    (0.75, 0.45, "J12"),
    (0.90, 0.50, "L12"),
    (0.00, 0.50, "L12"),   # как в coefficients: 0 не попадает в 0<F<0.21
])
def test_coefficient_band_points(f, a, band):
    assert coefficient_band(f, a) == band
    assert band in COEFFICIENT_BAND_INFO


def test_coefficient_band_partition_matches_coefficients():
    """Полоса согласована с значениями coefficients на мелкой сетке."""
    seen = set()
    for i in range(0, 101):
        f = i / 100.0
        for j in range(0, 101):
            a = j / 100.0
            band = coefficient_band(f, a)
            assert band in COEFFICIENT_BAND_INFO
            seen.add(band)
            k1, k2, k3, k4, achl = coefficients(f, a)
            # общие инварианты, которые обязана давать любая полоса
            assert k4 == pytest.approx(10.0 - k1 - k2 - 2.0 * k3)
            assert achl == pytest.approx(
                {"H5": 126.89 * f + 551.81,
                 "J5": 126.89 * f + 555.81,
                 "L5": 126.89 * f + 555.81,
                 "H12": 126.89 + f + 555.81,
                 "J12": 126.89 + f + 555.81,
                 "L12": 561.42 * f + 182.12}[band])
    assert seen == set(COEFFICIENT_BAND_INFO)


def test_classify_conditions_match_classify():
    """Тип, выведенный из условий, совпадает с classify."""
    ox = {"SiO2": 60.0, "Al2O3": 15.0, "FeO": 5.0, "MgO": 3.0,
          "CaO": 4.0, "Na2O": 3.0, "K2O": 2.0, "P2O5": 0.2}
    fe = formula_units(ox)
    f, a = f_and_a(fe)
    k1, k2, k3, k4, achl = coefficients(f, a)
    cond = classify_conditions(fe, k1, k3)
    assert set(cond) == {"e20", "e21", "e22", "e24", "e25"}

    def type_from_cond(c):
        if c["e20"] < 0 or c["e21"] <= 0:
            return 1
        if c["e22"] <= 0:
            return 2
        if c["e24"] <= 0:
            return 3
        if c["e25"] <= 0:
            return 4
        return 5

    assert type_from_cond(cond) == classify(fe, k1, k3)
    assert classify(fe, k1, k3) in ROCK_TYPE_INFO


# ── Маршрут ──────────────────────────────────────────────────────

@pytest.mark.parametrize("name", NAMES)
def test_run_path_structure(name, oxides):
    run = run_sample(oxides[name])
    path = run.path
    assert isinstance(path, BranchPath)
    labels = path.labels()
    assert labels[0].startswith("band_")
    assert labels[1] == f"rock_type_{run.st0.rock_type}"
    assert path.by_stage("stage_vi"), f"{name}: нет ветки VI этапа"
    assert all(d.name in STAGE_VI_INFO or d.name == "" or d.stage != "stage_vi"
               for d in path.by_stage("stage_vi"))
    # все подписи типа либо известны, либо всё равно не пустые
    assert all(d.name for d in path.by_stage("type"))


def test_path_to_dict_roundtrip():
    p = BranchPath()
    p.add("stage0", "band_H5", condition="0<F<0.21")
    p.add("stage_vi", "A", condition="ca_n>=mg_n+fe_n")
    d = p.to_dict()
    assert d["labels"] == ["band_H5", "A"]
    assert d["decisions"][0]["stage"] == "stage0"
    assert len(d["decisions"]) == 2


def test_calculator_debug_exposes_branch_path():
    """Calculator(debug=True) + excel_parity: path в AlgorithmOutput и в trace."""
    from src.core.calculator import Calculator
    from src.core.models import CalculationConfig, OxideComposition, Sample

    calc = Calculator(config=CalculationConfig(calculation_engine="excel_parity"))
    comp = OxideComposition(sio2=70.0, al2o3=12.0, fe2o3=1.0, feo=0.5,
                            mgo=0.3, cao=0.5, na2o=3.0, k2o=6.0)
    result = calc.calculate_single(Sample(name="arkose", composition=comp), debug=True)
    trace = result.debug_trace
    assert trace is not None
    steps = [c for c in trace.conditions if c.step.startswith("branch:")]
    assert steps, "ожидались записи branch:* в trace"
    assert any(c.branch.startswith("rock_type_") for c in steps)


def test_debug_tracer_records_branch_path():
    from src.core.debug_tracer import DebugTraceCollector

    run = run_sample({"SiO2": 70.0, "Al2O3": 12.0, "Fe2O3": 1.0, "FeO": 0.5,
                      "MgO": 0.3, "CaO": 0.5, "Na2O": 3.0, "K2O": 6.0})
    t = DebugTraceCollector("s")
    t.record_branch_path(run.path)
    assert any(c.step.startswith("branch:") for c in t.conditions)
    assert any(c.branch.startswith("rock_type_") for c in t.conditions)
