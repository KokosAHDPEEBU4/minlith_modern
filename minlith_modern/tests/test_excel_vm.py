"""Сверка excel_port (формулы + VBA VM) с эталоном Excel.

Полный прогон: вход -> VM (aDefin и вся цепочка веток) -> финальный результат.
Сравниваем row287 (вес.% минералов), defect и все именованные переменные.

Известные безобидные расхождения:
  - n_1, n_2, n_3 — счётчики веток (COUNTA), не влияют на минералы;
  - al_1 для образцов Type 3 — боковой регистр Type 12, не участвует в
    результате Type 3 (для Type 1 совпадает).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.excel_port.runner import load_structure, load_workbook, run_sample
from src.core.excel_port.vm import VbaVM

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"

pytestmark = pytest.mark.skipif(
    not (DATA / "reference.json").exists(),
    reason="reference.json не захвачен (нужен Excel)",
)

# Переменные, которые не влияют на результат и известны как расходящиеся.
IGNORE_NAMES = {"n_1", "n_2", "n_3", "al_1"}

COL_MINERALS = list(range(2, 36))  # B287..AI287


def _col(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


@pytest.fixture(scope="module")
def samples():
    return json.loads((DATA / "samples.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reference():
    return json.loads((DATA / "reference.json").read_text(encoding="utf-8"))


def _run(name, samples):
    wb = load_workbook()
    structure = load_structure()
    wb.set_input("Нач+Type 3", samples[name])
    vm = VbaVM(wb, structure)
    vm.active_sheet = "Нач+Type 3"
    vm.run("aDefin")
    return wb, vm


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_row287_matches_excel(samples, reference, name):
    """Финальный результат (вес.% минералов, строка 287) совпадает с Excel."""
    wb, _ = _run(name, samples)
    ref = reference[name]["row287"]
    for i, col in enumerate(COL_MINERALS):
        p = wb.eval_cell("Нач+Type 12", f"{_col(col)}287")
        e = ref[i]
        if e is None:
            continue
        assert p == pytest.approx(float(e), abs=1e-6), f"col{col}: {p} != {e}"


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_defect_matches_excel(samples, reference, name):
    wb, _ = _run(name, samples)
    ref = reference[name]["defect"]
    for i, r in enumerate(range(164, 172)):
        p = wb.eval_cell("Нач+Type 12", f"D{r}")
        e = ref[i]
        if e is None:
            continue
        assert p == pytest.approx(float(e), abs=1e-6), f"D{r}: {p} != {e}"


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_named_variables_match_excel(samples, reference, name):
    """Все именованные переменные (кроме известных n_*/al_1) совпадают."""
    wb, _ = _run(name, samples)
    ref_names = reference[name]["names"]
    bad = []
    for key, exp in ref_names.items():
        if key in IGNORE_NAMES:
            continue
        got = wb.eval_cell(*wb.names[key]) if key in wb.names else None
        if exp is None:
            continue
        try:
            ok = got is not None and abs(float(exp) - float(got)) < 0.01
        except (TypeError, ValueError):
            ok = (exp == got)
        if not ok:
            bad.append((key, exp, got))
    assert not bad, "\n".join(f"{k}: excel={e!r} python={g!r}" for k, e, g in bad)


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_runner_api(samples, reference, name):
    """Высокоуровневый run_sample() работает и даёт верные минералы."""
    res = run_sample(samples[name])
    ref_names = reference[name]["names"]
    for key in ["ab", "an", "ill", "chl", "or", "q", "kn", "gb"]:
        if key not in ref_names or ref_names[key] is None:
            continue
        assert res[key] == pytest.approx(float(ref_names[key]), abs=0.01)


# ---------------------------------------------------------------------------
# Все 5 типов пород (reference_multi.json)
# ---------------------------------------------------------------------------

MULTI = DATA / "reference_multi.json"


@pytest.fixture(scope="module")
def reference_multi():
    if not MULTI.exists():
        pytest.skip("reference_multi.json не захвачен")
    return json.loads(MULTI.read_text(encoding="utf-8"))


def _run_comp(comp):
    wb = load_workbook()
    structure = load_structure()
    wb.set_input("Нач+Type 3", comp)
    vm = VbaVM(wb, structure)
    vm.active_sheet = "Нач+Type 3"
    vm.run("aDefin")
    return wb


@pytest.mark.parametrize("name", ["arkose_t1", "granite_t2", "basalt_t3",
                                   "quartzite_t4", "highal_t5"])
def test_all_types_row287(reference_multi, name):
    """Финальный результат совпадает с Excel для всех типов 1-5."""
    data = reference_multi[name]
    wb = _run_comp(data["input"])
    for i, col in enumerate(COL_MINERALS):
        e = data["row287"][i]
        if e is None:
            continue
        p = wb.eval_cell("Нач+Type 12", f"{_col(col)}287")
        assert p == pytest.approx(float(e), abs=1e-6), f"{name} col{col}"


@pytest.mark.parametrize("name", ["arkose_t1", "granite_t2", "basalt_t3",
                                   "quartzite_t4", "highal_t5"])
def test_all_types_defect(reference_multi, name):
    data = reference_multi[name]
    wb = _run_comp(data["input"])
    for i, r in enumerate(range(164, 172)):
        e = data["defect"][i]
        if e is None:
            continue
        p = wb.eval_cell("Нач+Type 12", f"D{r}")
        assert p == pytest.approx(float(e), abs=1e-6), f"{name} D{r}"


@pytest.mark.parametrize("name", ["arkose_t1", "granite_t2", "basalt_t3",
                                   "quartzite_t4", "highal_t5"])
def test_all_types_named_vars(reference_multi, name):
    data = reference_multi[name]
    wb = _run_comp(data["input"])
    bad = []
    for key, exp in data["names"].items():
        if key in IGNORE_NAMES or exp is None:
            continue
        got = wb.eval_cell(*wb.names[key]) if key in wb.names else None
        try:
            ok = got is not None and abs(float(exp) - float(got)) < 0.01
        except (TypeError, ValueError):
            ok = (exp == got)
        if not ok:
            bad.append((key, exp, got))
    assert not bad, f"{name}: " + "; ".join(f"{k}: {e!r}!={g!r}" for k, e, g in bad)
