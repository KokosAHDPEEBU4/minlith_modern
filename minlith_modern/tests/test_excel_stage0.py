"""Сверка стадии 0 (Python) с эталоном Excel (data/reference.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.excel_port.stage0 import compute_stage0
from src.core.excel_port.workbook import Workbook

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"

pytestmark = pytest.mark.skipif(
    not (DATA / "reference.json").exists(),
    reason="reference.json не захвачен (нужен Excel)",
)


@pytest.fixture(scope="module")
def raw():
    return json.loads((DATA / "workbook_raw.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reference():
    return json.loads((DATA / "reference.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def samples():
    return json.loads((DATA / "samples.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_stage0_coefficients(raw, reference, samples, name):
    wb = Workbook(raw)
    s0 = compute_stage0(wb, samples[name])
    ref = reference[name]
    # коэффициенты
    assert s0.k1 == pytest.approx(float(ref["cells"]["F12"]), abs=1e-9)
    assert s0.k2 == pytest.approx(float(ref["cells"]["F13"]), abs=1e-9)
    assert s0.k3 == pytest.approx(float(ref["cells"]["F14"]), abs=1e-9)
    assert s0.k4 == pytest.approx(float(ref["cells"]["F15"]), abs=1e-9)
    assert s0.achl == pytest.approx(float(ref["cells"]["F16"]), abs=1e-9)


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_stage0_F_A(raw, reference, samples, name):
    wb = Workbook(raw)
    s0 = compute_stage0(wb, samples[name])
    ref = reference[name]
    assert s0.F == pytest.approx(float(ref["cells"]["G2"]), abs=1e-9)
    assert s0.A == pytest.approx(float(ref["cells"]["I2"]), abs=1e-9)


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_stage0_fe(raw, reference, samples, name):
    wb = Workbook(raw)
    s0 = compute_stage0(wb, samples[name])
    ref = reference[name]
    # D2..D19 (кроме D15-заглушки)
    order = ["SiO2","TiO2","Al2O3","Fe2O3","FeO","MgO","CaO","Na2O","K2O",
             "P2O5","MnO","C","SO3","F","Cl","S","CO2","SO"]
    ref_fe = [ref["cells"].get(c) for c in
              ["D2","D3","D4","D5","D6","D7","D8","D9","D10",
               "D11","D12","D13","D14","D15","D16","D17","D18","D19"]]
    for ox, rv in zip(order, ref_fe):
        if rv is None or isinstance(rv, str):
            continue
        assert s0.fe[ox] == pytest.approx(float(rv), abs=1e-6), f"{ox}: {s0.fe[ox]} != {rv}"


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_stage0_flags(raw, reference, samples, name):
    wb = Workbook(raw)
    s0 = compute_stage0(wb, samples[name])
    ref = reference[name]
    for r in [20, 21, 22, 24, 25, 26]:
        exp = ref["cells"].get(f"F{r}")
        if exp is None:
            continue
        assert s0.flags[f"F{r}"] == bool(exp), f"F{r}"


@pytest.mark.parametrize("name", ["BK-1", "T-O2"])
def test_stage0_rock_type(raw, reference, samples, name):
    wb = Workbook(raw)
    s0 = compute_stage0(wb, samples[name])
    # по эталонным флагам
    ref = reference[name]["cells"]
    if ref.get("F20") or ref.get("F21"):
        expected = 1
    elif ref.get("F22"):
        expected = 2
    elif ref.get("F24"):
        expected = 3
    elif ref.get("F25"):
        expected = 4
    else:
        expected = 5
    assert s0.rock_type == expected
