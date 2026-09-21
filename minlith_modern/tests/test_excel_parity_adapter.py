"""Интеграционные тесты: excel_parity в интерфейсе MineralAlgorithm.

1. Адаптер — структурно совместим с :class:`MineralAlgorithm`;
2. round-trip: AlgorithmInput (ф.е. движка) -> адаптер -> одинаковые ф.е.
   минералов и остатков для всех 7 образцов;
3. smoke-тест через Calculator: движок подключается как replaceable-алгоритм.
"""
import json
import math
from pathlib import Path

import pytest

from src.core.algorithm import AlgorithmInput, MineralAlgorithm
from src.core.calculator import Calculator
from src.core.excel_parity.algorithm import ExcelParityAlgorithm
from src.core.excel_parity.runner import run_sample as excel_run
from src.core.models import OxideComposition, Sample

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"
NAMES = ["BK-1", "T-O2",
         "arkose_t1", "granite_t2", "basalt_t3", "quartzite_t4", "highal_t5"]

# attr в AlgorithmOutput -> поле в типе/VI-этапе excel_parity
_TYPED = [("Ab", "ab"), ("An", "an"), ("Or", "or_"), ("Ill", "ill"),
          ("Chl", "chl"), ("Kn", "kn"), ("Mm", "mm"), ("Gb", "gb")]
_VIED = [("Q", "q"), ("Dl", "dl"), ("Ank", "ank"), ("Cc", "cc"),
         ("Rch", "rch"), ("Sd", "sd"), ("Srp", "srp"), ("Mst", "mst"),
         ("Ht", "ht"), ("Prl", "prl")]


@pytest.fixture(scope="module")
def oxides():
    multi = json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))
    one = json.loads((DATA / "reference.json").read_text(encoding="utf-8"))
    ox = {name: rec["input"] for name, rec in multi.items()}
    ox["BK-1"] = one["BK-1"]["input"]
    ox["T-O2"] = one["T-O2"]["input"]
    return ox


def _input_from_run(name, oxides):
    """Собирает AlgorithmInput из результата чистого движка (ф.е. + k + тип)."""
    cr = excel_run(oxides[name])
    st0 = cr.st0
    raw_f = oxides[name].get("F", 0.0) * 10000.0 / 19.0
    return AlgorithmInput(
        sio2=st0.fe["SiO2"], tio2=st0.fe["TiO2"], al2o3=st0.fe["Al2O3"],
        feo=st0.fe["FeO"], mgo=st0.fe["MgO"], cao=st0.fe["CaO"],
        na2o=st0.fe["Na2O"], k2o=st0.fe["K2O"], p2o5=st0.fe["P2O5"],
        mno=st0.fe["MnO"], c=st0.fe["C"], so3=st0.fe["SO3"],
        f=raw_f, cl=st0.fe["Cl"], s=st0.fe["S"],
        co2=st0.fe["CO2"], so=st0.fe["SO"],
        k1=st0.k1, k2=st0.k2, k3=st0.k3, k4=st0.k4,
        F=st0.F, A=st0.A, rock_type=st0.rock_type,
    )


def test_adapter_is_mineral_algorithm_protocol():
    assert isinstance(ExcelParityAlgorithm(), MineralAlgorithm)


def test_calculator_resolves_engine_excel_parity():
    """Calculator(config.calculation_engine="excel_parity") подключает excel_parity."""
    from src.core.models import CalculationConfig
    calc = Calculator(config=CalculationConfig(calculation_engine="excel_parity"))
    assert isinstance(calc.algorithm, ExcelParityAlgorithm)


def test_calculator_keeps_geological_theory_default():
    """Без явного алгоритма Calculator остаётся на GeologicalTheoryAlgorithm."""
    from src.core.geological_theory import GeologicalTheoryAlgorithm
    calc = Calculator()
    assert isinstance(calc.algorithm, GeologicalTheoryAlgorithm)


@pytest.mark.parametrize("name", NAMES)
def test_adapter_round_trip(name, oxides):
    """Адаптер идемпотентен: ф.е. из движка -> AlgorithmOutput == движок."""
    cr = excel_run(oxides[name])
    out = ExcelParityAlgorithm().compute(_input_from_run(name, oxides))
    assert out.residuals is not None
    for attr, field in _TYPED + _VIED:
        expect = (getattr(cr.tsol, field) if (attr, field) in _TYPED
                  else getattr(cr.vi, field))
        assert getattr(out, attr) == pytest.approx(expect, abs=0.0, rel=1e-12), \
            f"{name}:{attr}"
    for key, field in [("ca_n", "ca_n"), ("mg_n", "mg_n"),
                       ("fe_n", "fe_n"), ("si_n", "si_n")]:
        assert out.residuals[key] == pytest.approx(getattr(cr.tsol, field),
                                                   abs=0.0, rel=1e-12), \
            f"{name}:residual {key}"


@pytest.mark.parametrize("name", NAMES)
def test_calculator_with_excel_parity(name, oxides):
    """Calculator + ExcelParityAlgorithm: полный pipeline даёт состав."""
    calc = Calculator(algorithm=ExcelParityAlgorithm())
    clean_input = {k: (v or 0.0) for k, v in oxides[name].items()}
    sample = Sample(name=name, composition=OxideComposition.from_dict(clean_input))
    result = calc.calculate_single(sample)
    m = result.minerals_weight
    total = (m.ab + m.an + m.pl + m.or_ + m.ill + m.chl + m.kn + m.mm + m.gb
             + m.q + m.cc + m.dl + m.ank + m.rch + m.sd + m.srp + m.mst
             + m.ht + m.prl + m.ap + m.c + m.pr + m.rt + m.hl + m.gy)
    assert result is not None
    assert total > 0.0          # состав посчитан, а не пустой
    assert result.rock_type.value in (1, 2, 3, 4, 5)


def test_adapter_survives_minimal_formula_units():
    """Почти пустой вход (чистый кварц ф.е.): без падений, тривиальный состав."""
    q = 100.0 * 10000.0 / 60.09          # 100% SiO2 -> ф.е.
    inp = AlgorithmInput(sio2=q, tio2=0, al2o3=0, feo=0, mgo=0, cao=0,
                         na2o=0, k2o=0, p2o5=0, mno=0, c=0, so3=0,
                         f=0, cl=0, s=0, co2=0, so=0,
                         k1=0, k2=0, k3=0, k4=0, F=0, A=0, rock_type=1)
    algo = ExcelParityAlgorithm()
    out = algo.compute(inp)
    assert math.isfinite(out.Q)
    assert out.Q == pytest.approx(q, abs=0.0, rel=1e-12)
    assert out.residuals is not None
