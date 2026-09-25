"""Тесты применения override в движке excel_parity — этап 3 ТЗ.

Проверяют: полоса коэффициентов, тип породы, ветка этапа VI; метку ``forced``
в маршруте; неизменность авто-поведения при отсутствии override.
"""

import pytest

from src.core.branch_overrides import BranchOverrides, validate_overrides
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


_BASALT = {"SiO2": 50.0, "Al2O3": 14.5, "Fe2O3": 3.0, "FeO": 9.0, "MgO": 8.0,
           "CaO": 10.5, "Na2O": 2.5, "K2O": 0.5, "TiO2": 1.5, "P2O5": 0.3}
_EXT_M418 = {"SiO2": 58.409, "TiO2": 6.509, "Al2O3": 7.481, "Fe2O3": 8.596,
             "FeO": 6.124, "MgO": 2.473, "CaO": 8.537, "MnO": 6.995, "C": 0.132,
             "F": 9.441, "Cl": 11.869, "S": 6.009, "SO": 1.294}


@pytest.mark.parametrize("branch", ["F119+", "F126-"])
def test_type3_p114_override(branch):
    run = run_sample(_BASALT, overrides=BranchOverrides(
        choices={"type3.p_114": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["t45-m418t", "t45-m424->t5"])
def test_type45_d418_override(branch):
    run = run_sample(_EXT_M418, overrides=BranchOverrides(
        choices={"type45.d418": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_ARKOSE = {"SiO2": 70.0, "Al2O3": 12.0, "Fe2O3": 1.0, "FeO": 0.5,
           "MgO": 0.3, "CaO": 0.5, "Na2O": 3.0, "K2O": 6.0}


@pytest.mark.parametrize("branch", ["t_52~53", "t_58", "t_67", "t_83"])
def test_type1_t49_override(branch):
    run = run_sample(_ARKOSE, overrides=BranchOverrides(
        choices={"type1.t_49": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["D61", "D68"])
def test_type3_d61_override(branch):
    run = run_sample(_BASALT, overrides=BranchOverrides(
        choices={"type3.d61": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE3_D200 = {"SiO2": 46.55, "TiO2": 9.39, "Al2O3": 17.243, "Fe2O3": 3.414,
               "FeO": 3.787, "MgO": 12.925, "CaO": 4.772, "Na2O": 7.823,
               "K2O": 3.518, "P2O5": 1.973, "MnO": 5.346, "C": 8.168,
               "SO3": 1.713, "F": 7.917, "Cl": 9.218, "S": 8.061,
               "CO2": 8.235, "SO": 0.075}


@pytest.mark.parametrize("branch", ["3333a", "3333b"])
def test_type3_d200_override(branch):
    run = run_sample(_TYPE3_D200, overrides=BranchOverrides(
        choices={"type3.d200": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE2_FE = {"SiO2": 59.767, "TiO2": 5.855, "Al2O3": 13.703, "Fe2O3": 5.15,
             "FeO": 1.398, "MgO": 5.049, "CaO": 2.554, "Na2O": 2.158,
             "K2O": 7.767, "P2O5": 6.427, "MnO": 2.433, "C": 7.079,
             "SO3": 1.686, "F": 3.154, "Cl": 6.835, "S": 5.135,
             "CO2": 0.803, "SO": 7.914}


@pytest.mark.parametrize("branch", ["an=0.2na", "an=ca", "an=0.2na(I)"])
def test_type2_an_override(branch):
    run = run_sample(_TYPE2_FE, overrides=BranchOverrides(
        choices={"type2.an": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["fe-ill", "fe-ill-mg"])
def test_type2_fe_ill_override(branch):
    run = run_sample(_TYPE2_FE, overrides=BranchOverrides(
        choices={"type2.fe_ill": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE3_D180 = {"SiO2": 49.453, "TiO2": 9.432, "Al2O3": 25.048, "Fe2O3": 8.335,
               "FeO": 11.952, "MgO": 13.673, "CaO": 4.361, "Na2O": 8.454,
               "K2O": 3.37, "P2O5": 5.828, "MnO": 9.237, "C": 8.291,
               "SO3": 3.526, "F": 11.347, "Cl": 7.796, "S": 6.968,
               "CO2": 0.139, "SO": 6.564}


@pytest.mark.parametrize("branch", ["3332a", "no_3332a"])
def test_type3_d180_override(branch):
    run = run_sample(_TYPE3_D180, overrides=BranchOverrides(
        choices={"type3.d180": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["p_142", "no_p_142"])
def test_type3_p142_override(branch):
    run = run_sample(_BASALT, overrides=BranchOverrides(
        choices={"type3.p_142": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


def test_validate_accepts_internal_overrides():
    validate_overrides(BranchOverrides(choices={"type3.p_114": "F119+"}))
    validate_overrides(BranchOverrides(choices={"type45.d418": "t45-m418t"}))
    validate_overrides(BranchOverrides(choices={"type1.t_49": "t_67"}))
    validate_overrides(BranchOverrides(choices={"type3.d61": "D68"}))
    validate_overrides(BranchOverrides(choices={"type3.d200": "3333b"}))
    validate_overrides(BranchOverrides(choices={"type3.p_142": "p_142"}))
    validate_overrides(BranchOverrides(choices={"type2.fe_ill": "fe-ill"}))
    validate_overrides(BranchOverrides(choices={"type3.d180": "3332a"}))
    validate_overrides(BranchOverrides(choices={"type2.an": "an=ca"}))


def test_auto_behavior_unchanged_without_overrides():
    auto = run_sample(_OX).names
    empty = run_sample(_OX, overrides=BranchOverrides()).names
    assert auto == empty
    assert coefficient_band(0.10, 0.5) == "H5"
