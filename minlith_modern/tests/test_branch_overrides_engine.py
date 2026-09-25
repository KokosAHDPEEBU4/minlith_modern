"""Тесты применения override в движке excel_parity — этап 3 ТЗ.

Проверяют: полоса коэффициентов, тип породы, ветка этапа VI; метку ``forced``
в маршруте; неизменность авто-поведения при отсутствии override.
"""

import pytest

from src.core.branch_overrides import BranchOverrides
from src.core.excel_parity.branches import (
    COEFFICIENT_BAND_INFO,
    STAGE_VI_INFO,
)
from src.core.excel_parity.runner import run_sample
from src.core.excel_parity.stage0 import (
    classify,
    coefficient_band,
    coefficients,
    compute_stage0,
    f_and_a,
    formula_units,
)

_OX = {"SiO2": 70.0, "Al2O3": 12.0, "Fe2O3": 1.0, "FeO": 0.5,
       "MgO": 0.3, "CaO": 0.5, "Na2O": 3.0, "K2O": 6.0}


def test_coefficients_override_matches_band_formula():
    f, a = 0.10, 0.50
    k1, k2, k3, k4, achl = coefficients(f, a, override="H5")
    assert k1 == pytest.approx(4.42 - 5.18 * f)
    assert k2 == pytest.approx(4.09 * f)
    assert k3 == pytest.approx((3.16 - 0.41 * f) / 2.0)
    assert k4 == pytest.approx(10.0 - k1 - k2 - 2.0 * k3)
    assert achl == pytest.approx(126.89 * f + 551.81)


@pytest.mark.parametrize("band", list(COEFFICIENT_BAND_INFO))
def test_coefficients_all_bands_invariants(band):
    f, a = 0.75, 0.60
    k1, k2, k3, k4, achl = coefficients(f, a, override=band)
    assert k4 == pytest.approx(10.0 - k1 - k2 - 2.0 * k3)
    assert achl > 0


def test_classify_override_forces_type():
    fe = formula_units(_OX)
    f, a = f_and_a(fe)
    k1, k2, k3, _k4, _achl = coefficients(f, a)
    assert classify(fe, k1, k3, override="4") == 4
    assert classify(fe, k1, k3, override="1") == 1


def test_run_sample_rock_type_override():
    forced = run_sample(_OX, overrides=BranchOverrides(choices={"rock_type": "3"}))
    assert forced.st0.rock_type == 3
    assert any(d.name == "rock_type_3" and d.forced for d in forced.path.decisions)


def test_run_sample_coefficient_band_override():
    auto = compute_stage0(_OX)
    forced = run_sample(_OX, overrides=BranchOverrides(choices={"coefficient_band": "L12"}))
    assert forced.st0.coefficient_band == "L12"
    k1, k2, k3, k4, achl = coefficients(auto.F, auto.A, override="L12")
    assert forced.st0.k1 == pytest.approx(k1)
    assert forced.st0.achl == pytest.approx(achl)
    assert any(d.name == "band_L12" and d.forced for d in forced.path.decisions)


@pytest.mark.parametrize("branch", list(STAGE_VI_INFO))
def test_run_sample_stage_vi_override(branch):
    forced = run_sample(_OX, overrides=BranchOverrides(choices={"stage_vi": branch}))
    assert forced.vi.trace and forced.vi.trace[0] == branch
    assert any(d.stage == "stage_vi" and d.forced and d.name == branch
               for d in forced.path.decisions)


def test_auto_behavior_unchanged_without_overrides():
    auto = run_sample(_OX).names
    empty = run_sample(_OX, overrides=BranchOverrides()).names
    assert auto == empty
    assert coefficient_band(0.10, 0.5) == "H5"
