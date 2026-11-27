"""Интеграционные тесты движка excel_exact (полная 1:1 копия Excel).

1. Адаптер структурно совместим с :class:`MineralAlgorithm`;
2. ф.е. минералов совпадают с ``excel_port.run_sample(rounding=True)`` —
   тем самым движок является копией Excel, а не «чистого» варианта;
3. Calculator подключает движок и прокидывает исходные вес.% (``oxide_wt``).
"""
import json
from pathlib import Path

import pytest

from src.core.algorithm import AlgorithmInput, MineralAlgorithm
from src.core.calculator import Calculator
from src.core.excel_exact.algorithm import ExcelExactAlgorithm
from src.core.excel_port.runner import run_sample as port_run
from src.core.models import CalculationConfig, OxideComposition, Sample

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"
NAMES = ["BK-1", "T-O2",
         "arkose_t1", "granite_t2", "basalt_t3", "quartzite_t4", "highal_t5"]

# поле AlgorithmOutput -> имя переменной excel_port
_FIELDS = {
    "Ab": "ab", "An": "an", "Or": "or", "Ill": "ill", "Chl": "chl",
    "Kn": "kn", "Mm": "mm", "Gb": "gb", "Q": "q", "Dl": "dl",
    "Ank": "ank", "Cc": "cc", "Rch": "rch", "Sd": "sd", "Srp": "srp",
    "Mst": "mst", "Ht": "ht", "Prl": "prl",
}
_RESIDUALS = ("ca_n", "mg_n", "fe_n", "si_n")


@pytest.fixture(scope="module")
def oxides():
    multi = json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))
    one = json.loads((DATA / "reference.json").read_text(encoding="utf-8"))
    ox = {name: rec["input"] for name, rec in multi.items()}
    ox["BK-1"] = one["BK-1"]["input"]
    ox["T-O2"] = one["T-O2"]["input"]
    return ox


def test_adapter_is_mineral_algorithm_protocol():
    assert isinstance(ExcelExactAlgorithm(), MineralAlgorithm)


def test_calculator_resolves_engine_excel_exact():
    calc = Calculator(config=CalculationConfig(calculation_engine="excel_exact"))
    assert isinstance(calc.algorithm, ExcelExactAlgorithm)


@pytest.mark.parametrize("name", NAMES)
def test_adapter_matches_excel_rounding(name, oxides):
    """excel_exact == excel_port(rounding=True): ф.е. минералов 1:1 с Excel."""
    inp = AlgorithmInput(
        sio2=0, tio2=0, al2o3=0, feo=0, mgo=0, cao=0, na2o=0, k2o=0,
        p2o5=0, mno=0, c=0, so3=0, f=0, cl=0, s=0, co2=0, so=0,
        k1=0, k2=0, k3=0, k4=0, F=0, A=0, rock_type=1,
        oxide_wt=oxides[name],
    )
    out = ExcelExactAlgorithm().compute(inp)
    ref = port_run(oxides[name], rounding=True)
    for attr, var in _FIELDS.items():
        assert getattr(out, attr) == pytest.approx(float(ref[var]), abs=0.0), \
            f"{name}:{attr}"
    assert out.residuals is not None
    for key in _RESIDUALS:
        assert out.residuals[key] == pytest.approx(float(ref[key]), abs=0.0), \
            f"{name}:residual {key}"


@pytest.mark.parametrize("name", NAMES)
def test_calculator_with_excel_exact(name, oxides):
    """Calculator + ExcelExactAlgorithm: полный pipeline даёт непустой состав."""
    calc = Calculator(config=CalculationConfig(calculation_engine="excel_exact"))
    clean_input = {k: (v or 0.0) for k, v in oxides[name].items()}
    sample = Sample(name=name, composition=OxideComposition.from_dict(clean_input))
    result = calc.calculate_single(sample)
    m = result.minerals_weight
    total = (m.ab + m.an + m.pl + m.or_ + m.ill + m.chl + m.kn + m.mm + m.gb
             + m.q + m.cc + m.dl + m.ank + m.rch + m.sd + m.srp + m.mst
             + m.ht + m.prl + m.ap + m.c + m.pr + m.rt + m.hl + m.gy)
    assert total > 0.0
    assert result.rock_type.value in (1, 2, 3, 4, 5)


def test_calculator_passes_oxide_weight_percent(oxides):
    """Calculator кладёт исходные вес.% в AlgorithmInput.oxide_wt."""
    captured: dict = {}

    class _Spy:
        def compute(self, inp):
            captured["inp"] = inp
            from src.core.algorithm import AlgorithmOutput
            return AlgorithmOutput()

    calc = Calculator(algorithm=_Spy())
    comp = OxideComposition.from_dict(oxides["granite_t2"])
    calc.calculate_single(Sample(name="granite_t2", composition=comp))
    assert captured["inp"].oxide_wt is not None
    assert captured["inp"].oxide_wt["SiO2"] == pytest.approx(comp.sio2)


def test_excel_exact_requires_weight_percent():
    """Без исходных вес.% движок честно падает, а не считает приблизительно."""
    inp = AlgorithmInput(
        sio2=0, tio2=0, al2o3=0, feo=0, mgo=0, cao=0, na2o=0, k2o=0,
        p2o5=0, mno=0, c=0, so3=0, f=0, cl=0, s=0, co2=0, so=0,
        k1=0, k2=0, k3=0, k4=0, F=0, A=0, rock_type=1,
    )
    with pytest.raises(ValueError, match="oxide_wt"):
        ExcelExactAlgorithm().compute(inp)
