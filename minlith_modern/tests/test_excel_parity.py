"""Тесты чистого движка excel_parity (Phase 3).

Сверяют явные float-вычисления движка с полным графом excel_port в режиме
без округлений (rounding=False): имена переменных, финальную строку 287
и невязки (дефект) должны совпадать с плавающей точностью (~1e-9).
"""
import json
from pathlib import Path

import pytest

from src.core.excel_parity.runner import run_sample as parity_run
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
    cr = parity_run(oxides[name])
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
    cr = parity_run(oxides[name])
    ref = excel_cells(oxides[name], _COLS287)
    assert len(cr.out.row287) == 34
    for i, (a, b) in enumerate(zip(cr.out.row287, ref)):
        assert abs(a - b) <= 1e-9, f"{name}:{_COLS287[i]} = {a}, excel = {b}"


@pytest.mark.parametrize("name", NAMES)
def test_defect_matches_excel(name, oxides):
    cr = parity_run(oxides[name])
    ref = excel_cells(oxides[name], list(DEFECT_MAP))
    for cell, oxide in DEFECT_MAP.items():
        a = cr.out.defect[oxide]
        b = ref[list(DEFECT_MAP).index(cell)]
        assert abs(a - b) <= 1e-9, f"{name}:{cell}({oxide}) = {a}, excel = {b}"


@pytest.mark.parametrize("name", NAMES)
def test_rock_type_classification(name, oxides):
    """Подтверждение: тип породы согласован с исполнением оригинала."""
    cr = parity_run(oxides[name])
    assert cr.st0.rock_type in (1, 2, 3, 4, 5)


def test_default_oxides_merge():
    """Отсутствующие оксиды берутся из DEFAULT_OXIDES (принцип оригинала)."""
    from src.core.excel_parity.stage0 import DEFAULT_OXIDES
    cr = parity_run({"SiO2": 92.0})
    assert cr.st0.fe["S"] > 0          # демо-сера из defaults
    assert cr.st0.s == DEFAULT_OXIDES["S"] * 10000.0 / 32.066


# Тип 3, редкая ветка p_196 (si3_3<0 → p_253/p_81): ранее был NotImplementedError.
_P196_TYPE3_INPUT = {
    "SiO2": 15.0849, "TiO2": 5.05, "Al2O3": 4.4239, "Fe2O3": 1.2161,
    "FeO": 12.765, "MgO": 2.1706, "CaO": 10.0395, "Na2O": 1.8124,
    "K2O": 0.6485, "P2O5": 7.6136, "MnO": 2.4228, "C": 0.0, "SO3": 8.2219,
    "F": 0.0, "Cl": 6.339, "S": 6.3683, "CO2": 0.4194, "SO": 9.0133,
}


# Тип 4/5, путь m_418t: Excel вызывает p_201 напрямую, и формула C422
# пересчитывается дважды (копипаст в al4_1, затем в al3_2) — двойной вычет.
_M418T_INPUT = {
    "SiO2": 58.409, "TiO2": 6.509, "Al2O3": 7.481, "Fe2O3": 8.596,
    "FeO": 6.124, "MgO": 2.473, "CaO": 8.537, "MnO": 6.995, "C": 0.132,
    "F": 9.441, "Cl": 11.869, "S": 6.009, "SO": 1.294,
}


# Тип 5, ветка m_322t: C322/C324 читают отдельную ячейку mg0 (J272), которая
# для типа 5 остаётся 0 (её пишет только aType_4 / коридор m_528).
_M322T_MG0_INPUT = {
    "SiO2": 27.068, "Al2O3": 20.828, "Fe2O3": 0.58, "FeO": 0.825,
    "MgO": 1.537, "CaO": 12.736, "Na2O": 1.238, "K2O": 6.274, "MnO": 3.967,
    "SO3": 8.585, "F": 1.443, "Cl": 3.085, "CO2": 5.816,
}


def test_type5_m322t_mg0_matches_excel():
    """mg0 (J272) для типа 5 = 0: ветка m_322t совпадает с эталоном."""
    cr = parity_run(_M322T_MG0_INPUT)
    assert cr.st0.rock_type == 5
    assert "m_322t->p81" in cr.tsol.trace
    er = excel_run(_M322T_MG0_INPUT, rounding=False)
    for k, a in cr.names.items():
        b = er.get(k)
        if isinstance(a, str) or not isinstance(b, (int, float)):
            continue
        assert abs(a - b) <= 1e-9, f"{k} = {a!r}, excel = {b!r}"


def test_type45_m418t_matches_excel():
    """m_418t (p_201 напрямую + двойной C422) совпадает с эталоном."""
    cr = parity_run(_M418T_INPUT)
    assert "t45-m418t" in cr.tsol.trace
    er = excel_run(_M418T_INPUT, rounding=False)
    for k, a in cr.names.items():
        b = er.get(k)
        if isinstance(a, str) or not isinstance(b, (int, float)):
            continue
        assert abs(a - b) <= 1e-9, f"{k} = {a!r}, excel = {b!r}"


# Тип 1, t_74t: si_n остаётся = C70 = si_r (t_68t), НЕ обнуляется.
_TYPE1_T74_INPUT = {
    "SiO2": 49.86, "Al2O3": 13.185, "FeO": 9.09, "MgO": 3.01, "CaO": 4.4,
    "Na2O": 5.139, "K2O": 4.794, "C": 2.424, "F": 3.415, "CO2": 5.559,
    "SO": 3.742,
}


def test_type1_t74_si_n_matches_excel():
    cr = parity_run(_TYPE1_T74_INPUT)
    assert cr.st0.rock_type == 1
    er = excel_run(_TYPE1_T74_INPUT, rounding=False)
    assert cr.names["si_n"] == pytest.approx(er["si_n"], abs=1e-9)
    assert cr.names["mst"] == pytest.approx(er["mst"], abs=1e-9)
    assert cr.names["srp"] == pytest.approx(er["srp"], abs=1e-9)


# Тип 4, m_513 → m_279 → m_346t: fe_n берётся из исходного fe3_1 (не fe4_2).
_TYPE45_FE31_INPUT = {
    "SiO2": 19.023, "TiO2": 8.196, "Al2O3": 26.997, "Fe2O3": 3.192,
    "FeO": 11.17, "MgO": 17.837, "CaO": 14.992, "Na2O": 3.685,
    "K2O": 0.255, "P2O5": 1.355, "Cl": 2.59, "SO": 3.552,
}


def test_type45_m346_fe3_1_matches_excel():
    cr = parity_run(_TYPE45_FE31_INPUT)
    assert cr.st0.rock_type == 4
    er = excel_run(_TYPE45_FE31_INPUT, rounding=False)
    assert cr.names["fe_n"] == pytest.approx(er["fe_n"], abs=1e-9)
    assert cr.names["ht"] == pytest.approx(er["ht"], abs=1e-9)


# Тип 5 → коридор m_528/m_531 → aType_3: m_531 пишет al3_3=C534, и это
# значение проносится в type3 (ячейка I51 сохраняется между стадиями).
_TYPE5_TO_TYPE3_AL33_INPUT = {
    "SiO2": 39.303, "TiO2": 4.78, "Al2O3": 35.527, "Fe2O3": 0.744,
    "FeO": 18.716, "MgO": 0.255, "CaO": 15.329, "Na2O": 9.834, "K2O": 5.731,
    "P2O5": 3.036, "SO3": 4.619, "F": 1.646, "Cl": 3.114, "S": 9.533,
    "CO2": 8.927, "SO": 4.674,
}


def test_type5_corridor_to_type3_carries_al3_3():
    """al3_3 из коридора (m_531) проносится в type3 — совпадение с эталоном."""
    cr = parity_run(_TYPE5_TO_TYPE3_AL33_INPUT)
    er = excel_run(_TYPE5_TO_TYPE3_AL33_INPUT, rounding=False)
    for k, a in cr.names.items():
        b = er.get(k)
        if isinstance(a, str) or not isinstance(b, (int, float)):
            continue
        assert abs(a - b) <= 1e-9, f"{k} = {a!r}, excel = {b!r}"


def test_type3_p196_branch_implemented():
    """p_196 (ветка else p_181/p_189) больше не падает и совпадает с эталоном."""
    cr = parity_run(_P196_TYPE3_INPUT)
    assert cr.st0.rock_type == 3
    assert "p196->p81" in cr.tsol.trace
    er = excel_run(_P196_TYPE3_INPUT, rounding=False)
    for k, a in cr.names.items():
        b = er.get(k)
        if isinstance(a, str) or not isinstance(b, (int, float)):
            continue
        assert abs(a - b) <= 1e-9, f"{k} = {a!r}, excel = {b!r}"
