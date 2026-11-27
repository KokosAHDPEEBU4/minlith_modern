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


@pytest.mark.parametrize("branch", ["s208", "s271"])
def test_type2_s204_override(branch):
    run = run_sample(_TYPE2_FE, overrides=BranchOverrides(
        choices={"type2.s204": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["ill+or", "no_ill_or"])
def test_type2_ill_or_override(branch):
    run = run_sample(_TYPE2_FE, overrides=BranchOverrides(
        choices={"type2.ill_or": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["3331", "no_3331"])
def test_type3_d162_override(branch):
    run = run_sample(_TYPE3_D180, overrides=BranchOverrides(
        choices={"type3.d162": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["3332b", "no_3332b"])
def test_type3_d188_override(branch):
    run = run_sample(_TYPE3_D180, overrides=BranchOverrides(
        choices={"type3.d188": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE45_M334 = {"SiO2": 31.344, "TiO2": 4.562, "Al2O3": 26.513, "Fe2O3": 0.4,
                "FeO": 10.363, "MgO": 9.055, "CaO": 10.465, "Na2O": 5.105,
                "K2O": 1.97, "P2O5": 7.102, "MnO": 1.087, "C": 1.147,
                "SO3": 10.764, "F": 6.756, "Cl": 4.224, "S": 2.552,
                "CO2": 1.725, "SO": 4.977}


@pytest.mark.parametrize("branch", ["mm-path", "no_mm"])
def test_type45_d334_override(branch):
    run = run_sample(_TYPE45_M334, overrides=BranchOverrides(
        choices={"type45.d334": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["m_346", "m_360"])
def test_type45_d346_override(branch):
    run = run_sample(_TYPE45_M334, overrides=BranchOverrides(
        choices={"type45.d346": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE1_T73 = {"SiO2": 63.951, "TiO2": 3.911, "Al2O3": 9.936, "Fe2O3": 9.871,
              "FeO": 2.301, "MgO": 9.525, "CaO": 6.695, "Na2O": 7.336,
              "K2O": 1.746, "P2O5": 7.568, "MnO": 6.007, "C": 10.213,
              "SO3": 0.34, "F": 11.486, "Cl": 2.072, "S": 9.76,
              "CO2": 6.088, "SO": 10.028}


@pytest.mark.parametrize("branch", ["t_74t", "t_78"])
def test_type1_t73_override(branch):
    run = run_sample(_TYPE1_T73, overrides=BranchOverrides(
        choices={"type1.t_73": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE45_D287 = {"SiO2": 62.067, "TiO2": 6.877, "Al2O3": 32.57, "Fe2O3": 11.193,
                "FeO": 5.965, "MgO": 13.18, "CaO": 10.735, "Na2O": 3.175,
                "K2O": 3.977, "P2O5": 1.844, "MnO": 0.109, "C": 5.46,
                "SO3": 2.754, "F": 4.759, "Cl": 1.901, "S": 3.715,
                "CO2": 3.479, "SO": 6.051}


@pytest.mark.parametrize("branch", ["m287", "m334"])
def test_type45_d287_override(branch):
    run = run_sample(_TYPE45_D287, overrides=BranchOverrides(
        choices={"type45.d287": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE45_D302 = {"SiO2": 62.162, "TiO2": 10.371, "Al2O3": 27.447, "Fe2O3": 7.069,
                "FeO": 13.191, "MgO": 0.274, "CaO": 5.302, "Na2O": 11.41,
                "K2O": 0.162, "P2O5": 0.475, "MnO": 11.158, "C": 4.154,
                "SO3": 3.022, "F": 1.45, "Cl": 11.799, "S": 9.056,
                "CO2": 2.744, "SO": 2.638}


@pytest.mark.parametrize("branch", ["m302", "m311"])
def test_type45_d302_override(branch):
    run = run_sample(_TYPE45_D302, overrides=BranchOverrides(
        choices={"type45.d302": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE45_D322 = {"SiO2": 73.498, "TiO2": 3.376, "Al2O3": 18.552, "Fe2O3": 1.274,
                "FeO": 14.063, "MgO": 19.264, "CaO": 11.195, "Na2O": 0.175,
                "K2O": 1.488, "P2O5": 11.928, "MnO": 11.186, "C": 8.876,
                "SO3": 9.201, "F": 5.106, "Cl": 7.534, "S": 10.869,
                "CO2": 5.368, "SO": 4.659}


@pytest.mark.parametrize("branch", ["rVI", "m371"])
def test_type45_d294_override(branch):
    run = run_sample(_TYPE45_D287, overrides=BranchOverrides(
        choices={"type45.d294": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["d308-m334", "d308-p81"])
def test_type45_d308_override(branch):
    run = run_sample(_TYPE45_D302, overrides=BranchOverrides(
        choices={"type45.d308": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE45_D317 = {"SiO2": 53.136, "TiO2": 4.418, "Al2O3": 28.503, "Fe2O3": 2.651,
                "FeO": 11.977, "MgO": 0.983, "CaO": 2.355, "Na2O": 10.666,
                "K2O": 2.958, "P2O5": 11.265, "MnO": 7.411, "C": 0.212,
                "SO3": 6.65, "F": 9.79, "Cl": 7.111, "S": 0.653,
                "CO2": 9.499, "SO": 2.489}


@pytest.mark.parametrize("branch", ["d317-m334", "d317-p81"])
def test_type45_d317_override(branch):
    run = run_sample(_TYPE45_D317, overrides=BranchOverrides(
        choices={"type45.d317": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


@pytest.mark.parametrize("branch", ["m322", "m296"])
def test_type45_d322_override(branch):
    run = run_sample(_TYPE45_D322, overrides=BranchOverrides(
        choices={"type45.d322": branch}))
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


@pytest.mark.parametrize("branch", ["p_53t", "no_p_53"])
def test_type3_p53_override(branch):
    run = run_sample(_BASALT, overrides=BranchOverrides(
        choices={"type3.p_53": branch}))
    assert branch in run.tsol.trace
    assert any(d.stage == "type" and d.name == branch and d.forced
               for d in run.path.decisions)


_TYPE3_P97 = {"SiO2": 41.598, "TiO2": 8.277, "Al2O3": 21.97, "Fe2O3": 5.749,
              "FeO": 3.888, "MgO": 14.267, "CaO": 9.694, "Na2O": 6.149,
              "K2O": 6.061, "P2O5": 2.833, "MnO": 0.038, "C": 4.453,
              "SO3": 7.024, "F": 0.831, "Cl": 9.525, "S": 2.787,
              "CO2": 2.792, "SO": 0.508}


@pytest.mark.parametrize("branch", ["D106", "D109-fe", "p253->t5"])
def test_type3_p97_override(branch):
    run = run_sample(_TYPE3_P97, overrides=BranchOverrides(
        choices={"type3.p_97": branch}))
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
    validate_overrides(BranchOverrides(choices={"type2.s204": "s271"}))
    validate_overrides(BranchOverrides(choices={"type2.ill_or": "no_ill_or"}))
    validate_overrides(BranchOverrides(choices={"type3.d162": "no_3331"}))
    validate_overrides(BranchOverrides(choices={"type3.d188": "3332b"}))
    validate_overrides(BranchOverrides(choices={"type3.p_53": "no_p_53"}))
    validate_overrides(BranchOverrides(choices={"type3.p_97": "D106"}))
    validate_overrides(BranchOverrides(choices={"type45.d334": "no_mm"}))
    validate_overrides(BranchOverrides(choices={"type45.d346": "m_360"}))
    validate_overrides(BranchOverrides(choices={"type1.t_73": "t_78"}))
    validate_overrides(BranchOverrides(choices={"type45.d287": "m287"}))
    validate_overrides(BranchOverrides(choices={"type45.d302": "m302"}))
    validate_overrides(BranchOverrides(choices={"type45.d322": "m322"}))
    validate_overrides(BranchOverrides(choices={"type45.d294": "rVI"}))
    validate_overrides(BranchOverrides(choices={"type45.d308": "d308-p81"}))
    validate_overrides(BranchOverrides(choices={"type45.d317": "d317-m334"}))


def test_auto_behavior_unchanged_without_overrides():
    auto = run_sample(_OX).names
    empty = run_sample(_OX, overrides=BranchOverrides()).names
    assert auto == empty
    assert coefficient_band(0.10, 0.5) == "H5"
