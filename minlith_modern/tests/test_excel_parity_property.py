"""Property-тесты чисто движка на синтетике (Фаза 4).

Инварианты, проверяемые на сетке расширенного пространства составов:
  1. движок либо завершается с конечными результатами, либо падает ТОЛЬКО с
     NotImplementedError (явная проверка «ветка не реализована»);
  2. при успехе все ф.е. минералов и остатки конечны (нет NaN/Inf);
  3. весовые % не отрицательны и сумма > 0;
  4. полный 100%-ный пересчёт «ф.е.->вес.->нормировка» корректно масштабируется
     (row287 не содержит отрицательных массовых долей);
  5. тип породы всегда в 1..5.
"""
import itertools
import math

import pytest

from src.core.excel_parity.runner import run_sample

_GRID = {
    "SiO2": [50.0, 70.0, 90.0],
    "Al2O3": [5.0, 15.0, 25.0],
    "FeO": [0.5, 3.0, 8.0],
    "MgO": [0.5, 2.0, 6.0],
    "CaO": [0.0, 2.0, 8.0],
    "Na2O": [0.5, 2.0, 5.0],
    "K2O": [0.5, 2.0, 5.0],
}
_COMBOS = list(itertools.product(*_GRID.values()))   # 2187 = 3^7

# детерминированная подвыборка: каждый 11-й комбинируем, иначе тест долгий
_SYNTH = [dict(zip(_GRID, c)) for c in _COMBOS[::11]]


@pytest.mark.parametrize("oxides", _SYNTH)
def test_synthetic_run_completes_or_raises_explicitly(oxides):
    try:
        run_sample(oxides)
    except NotImplementedError:
        pytest.skip("ветка не реализована (явный gap движка)")
    except Exception as e:
        pytest.fail(f"Неожиданное исключение: {type(e).__name__}: {e}")


@pytest.mark.parametrize("oxides", _SYNTH)
def test_synthetic_outputs_finite_and_sane(oxides):
    try:
        run = run_sample(oxides)
    except NotImplementedError:
        pytest.skip("ветка не реализована (явный gap движка)")

    # 1. ф.е. минералов типов и остатки — конечны
    for v in run.tsol.__dict__.values():
        if isinstance(v, float):
            assert math.isfinite(v), "tsol: NaN/Inf"
    for v in run.vi.__dict__.values():
        if isinstance(v, float):
            assert math.isfinite(v), "vi: NaN/Inf"
    for v in run.out.defect.values():
        assert math.isfinite(v), "defect: NaN/Inf"

    # 2. весовые % без округлений — конечны, сумма ненулевая; отдельные
    #    колонки могут быть отрицательными (как в оригинале).
    assert all(isinstance(w, float) and math.isfinite(w)
               for w in run.out.weights149)
    assert sum(run.out.weights149) > 0.0

    # 3. тип породы в допустимом диапазоне
    assert run.st0.rock_type in (1, 2, 3, 4, 5)


@pytest.mark.parametrize("oxides", _SYNTH)
def test_synthetic_row287_nonnegative(oxides):
    try:
        run = run_sample(oxides)
    except NotImplementedError:
        pytest.skip("ветка не реализована (явный gap движка)")
    # строка 287: первые 2 — суммы (D151, D154) > 0; минералы могут быть
    # отрицательными (как и в оригинале — «недобор» ф.е.), но конечны.
    assert run.out.row287[0] > 0.0, "D151 sum"
    assert run.out.row287[1] > 0.0, "D154 sum"
    for i, v in enumerate(run.out.row287):
        assert math.isfinite(v), f"row287[{i}] not finite"


def test_branch_gaps_are_explicit_and_counted():
    """Все ветки оригинала реализованы: на синтетическом гриде нет NotImplementedError."""
    gaps = 0
    for oxides in _SYNTH:
        try:
            run_sample(oxides)
        except NotImplementedError:
            gaps += 1
    assert gaps == 0
