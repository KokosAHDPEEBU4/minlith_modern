"""Регресс: массовые % excel-движков == итоговая строка 287 книги.

Вариант 1: excel_exact/excel_parity отдают ``AlgorithmOutput.weight_percent``
(строка 287), а Calculator использует их напрямую как ``minerals_weight``
(без собственной нормировки). Тесты фиксируют это равенство, включая
патологические ветки (отрицательный иллит и т.п.).

Сравнение идёт с тем же ``oxide_wt``, который Calculator реально передал
движку (spy), т.к. «сырой» неполный вход иначе оставит часть оксидов на
дефолтах книги.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.algorithm import ROW287_FIELDS, AlgorithmInput, AlgorithmOutput
from src.core.calculator import Calculator
from src.core.excel_exact.algorithm import ExcelExactAlgorithm
from src.core.excel_parity.algorithm import ExcelParityAlgorithm
from src.core.excel_port.runner import run_sample_full
from src.core.geological_theory import GeologicalTheoryAlgorithm
from src.core.models import OxideComposition, Sample

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"


def _load_inputs() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for fn in ("reference_multi.json", "reference.json", "samples.json"):
        path = DATA / fn
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, rec in data.items():
            if isinstance(rec, dict) and "input" in rec:
                out[name] = rec["input"]
    return out


INPUTS = _load_inputs()

# Патологические входы (из сверки с новым файлом): высокая SO3/Fe2O3,
# «отрицательный иллит» в книге — выгрузка всё равно должна == row287.
PATHOLOGICAL = {
    "path_7930": {"SiO2": 0.9731, "TiO2": 0.02437, "Al2O3": 0.5569, "Fe2O3": 1.5631,
                  "MnO": 0.13371, "MgO": 14.0125, "CaO": 29.2601, "Na2O": 0.06413,
                  "K2O": 0.04654, "P2O5": 0.04565, "SO3": 28.351},
    "path_7931": {"SiO2": 29.6503, "TiO2": 0.2813, "Al2O3": 3.561, "Fe2O3": 5.4083,
                  "MnO": 0.21335, "MgO": 10.0595, "CaO": 16.9541, "Na2O": 0.15683,
                  "K2O": 1.26277, "P2O5": 0.05773, "SO3": 12.7123},
    "path_7938": {"SiO2": 51.7998, "TiO2": 0.39814, "Al2O3": 4.89133, "Fe2O3": 2.40102,
                  "MnO": 0.04623, "MgO": 5.56936, "CaO": 12.4663, "Na2O": 0.13518,
                  "K2O": 1.9123, "P2O5": 0.25392, "SO3": 15.3181},
}

ALL = dict(INPUTS)
ALL.update(PATHOLOGICAL)


class _Spy:
    """Обёртка движка: запоминает вход и выход последнего compute()."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.inp: AlgorithmInput | None = None
        self.out: AlgorithmOutput | None = None

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        self.inp = inp
        self.out = self.inner.compute(inp)
        return self.out


def _clean(inp: dict) -> dict:
    return {k: (float(v) if isinstance(v, (int, float)) else 0.0) for k, v in inp.items()}


def _sample(name: str, inp: dict) -> Sample:
    return Sample(name=name, composition=OxideComposition.from_dict(_clean(inp)))


def _alg_input(oxide_wt: dict) -> AlgorithmInput:
    return AlgorithmInput(
        sio2=0, tio2=0, al2o3=0, feo=0, mgo=0, cao=0, na2o=0, k2o=0,
        p2o5=0, mno=0, c=0, so3=0, f=0, cl=0, s=0, co2=0, so=0,
        k1=0, k2=0, k3=0, k4=0, F=0, A=0, rock_type=1, oxide_wt=oxide_wt,
    )


@pytest.mark.parametrize("name", list(ALL))
def test_exact_minerals_weight_equals_book_row287(name):
    """excel_exact через Calculator: minerals_weight == строка 287 книги точно."""
    spy = _Spy(ExcelExactAlgorithm())
    result = Calculator(algorithm=spy).calculate_single(_sample(name, ALL[name]))
    _, row287 = run_sample_full(spy.inp.oxide_wt, rounding=True)
    m = result.minerals_weight
    assert row287, f"{name}: пустая row287"
    for i, field in ROW287_FIELDS.items():
        assert getattr(m, field) == pytest.approx(row287[i], abs=0.0), \
            f"{name}:{field} = {getattr(m, field)} != row287[{i}] = {row287[i]}"


@pytest.mark.parametrize("name", list(ALL))
def test_parity_minerals_weight_equals_row287(name):
    """excel_parity через Calculator: minerals_weight == её строка 287."""
    spy = _Spy(ExcelParityAlgorithm())
    result = Calculator(algorithm=spy).calculate_single(_sample(name, ALL[name]))
    wp = spy.out.weight_percent
    assert wp is not None
    m = result.minerals_weight
    for i, field in ROW287_FIELDS.items():
        assert getattr(m, field) == pytest.approx(wp[field], abs=0.0), \
            f"{name}:{field} = {getattr(m, field)} != {wp[field]}"


def test_exact_adapter_weight_percent_equals_port_row287():
    """excel_exact adapter: weight_percent == row287 прямого прогона порта."""
    inp = _clean(INPUTS["arkose_t1"])
    _, row287 = run_sample_full(inp, rounding=True)
    out = ExcelExactAlgorithm().compute(_alg_input(inp))
    assert out.weight_percent is not None
    for i, field in ROW287_FIELDS.items():
        assert out.weight_percent[field] == pytest.approx(row287[i], abs=0.0)


def test_geological_theory_has_no_weight_percent():
    """Теоретический движок по-прежнему без row287 (своя нормировка)."""
    spy = _Spy(GeologicalTheoryAlgorithm())
    Calculator(algorithm=spy).calculate_single(_sample("granite_t2", INPUTS["granite_t2"]))
    assert spy.out.weight_percent is None
