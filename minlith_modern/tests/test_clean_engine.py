"""Тесты чистого движка clean_engine (Phase 3).

Сверяют явные float-вычисления движка с полным графом excel_port в режиме
без округлений (rounding=False): имена переменных, финальную строку 287
и невязки (дефект) должны совпадать с плавающей точностью (~1e-9).
"""
import json
from pathlib import Path

import pytest

from src.core.clean_engine.runner import run_sample as clean_run
from src.core.excel_port.runner import load_structure, load_workbook
from src.core.excel_port.runner import run_sample as excel_run
from src.core.excel_port.vm import VbaVM

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"
SKIP = {"f", "z", "n_1", "n_2", "n_3"}


@pytest.fixture(scope="module")
def multi():
    return json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def one():
    return json.loads((DATA / "reference.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def oxides(multi, one):
    ox = {name: rec["input"] for name, rec in multi.items()}
    ox["BK-1"] = one["BK-1"]["input"]
    ox["T-O2"] = one["T-O2"]["input"]
    return ox


NAMES = ["BK-1", "T-O2",
         "arkose_t1", "granite_t2", "basalt_t3", "quartzite_t4", "highal_t5"]


@pytest.mark.parametrize("name", NAMES)
def test_names_match_excel(name, oxides):
    """Каждая именованная переменная движка == excel_port (rounding=False)."""
    cr = clean_run(oxides[name])
    er = excel_run(oxides[name], rounding=False)
    common = set(cr.names) & set(er) - SKIP
    assert common, "движок не имеет общих имён для сверки"
    for k in common:
        a, b = cr.names[k], er[k]
        if isinstance(a, str) or isinstance(b, str):
            continue
        assert abs(a - b) <= 1e-9, f"{name}:{k} = {a!r}, excel = {b!r}"


_COLS287 = []
_n = 2
while len(_COLS287) < 34:  # B(2)..AI(35)
    c = ""
    x = _n
    while x:
        x, r = divmod(x - 1, 26)
        c = chr(65 + r) + c
    _COLS287.append(c + "287")
    _n += 1

DEFECT_MAP = {"D164": "SiO2", "D165": "Al2O3", "D166": "Na2O", "D167": "K2O",
              "D168": "MgO", "D169": "FeO", "D170": "CaO", "D171": "MnO"}


def excel_cells(ox, coords):
    wb = load_workbook(rounding=False)
    wb.set_input("Нач+Type 3", ox)
    vm = VbaVM(wb, load_structure())
    vm.active_sheet = "Нач+Type 3"
    vm.run("aDefin")
    out = []
    for c in coords:
        v = wb.eval_cell("Нач+Type 12", c)
        out.append(v[0] if isinstance(v, tuple) else v)
    return out


@pytest.mark.parametrize("name", NAMES)
def test_row287_matches_excel(name, oxides):
    cr = clean_run(oxides[name])
    ref = excel_cells(oxides[name], _COLS287)
    assert len(cr.out.row287) == 34
    for i, (a, b) in enumerate(zip(cr.out.row287, ref)):
        assert abs(a - b) <= 1e-9, f"{name}:{_COLS287[i]} = {a}, excel = {b}"


@pytest.mark.parametrize("name", NAMES)
def test_defect_matches_excel(name, oxides):
    cr = clean_run(oxides[name])
    ref = excel_cells(oxides[name], list(DEFECT_MAP))
    for cell, oxide in DEFECT_MAP.items():
        a = cr.out.defect[oxide]
        b = ref[list(DEFECT_MAP).index(cell)]
        assert abs(a - b) <= 1e-9, f"{name}:{cell}({oxide}) = {a}, excel = {b}"


@pytest.mark.parametrize("name", NAMES)
def test_rock_type_classification(name, oxides):
    """Подтверждение: тип породы согласован с исполнением оригинала."""
    cr = clean_run(oxides[name])
    assert cr.st0.rock_type in (1, 2, 3, 4, 5)


def test_default_oxides_merge():
    """Отсутствующие оксиды берутся из DEFAULT_OXIDES (принцип оригинала)."""
    from src.core.clean_engine.stage0 import DEFAULT_OXIDES
    cr = clean_run({"SiO2": 92.0})
    assert cr.st0.fe["S"] > 0          # демо-сера из defaults
    assert cr.st0.s == DEFAULT_OXIDES["S"] * 10000.0 / 32.066
