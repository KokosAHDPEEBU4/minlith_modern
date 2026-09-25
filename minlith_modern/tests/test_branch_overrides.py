"""Тесты ручного выбора веток (override) — этап 2 ТЗ.

Проверяют: валидацию по каталогу; что пустой выбор не меняет результат;
что Calculator проносит override в AlgorithmInput.
"""

import pytest

from src.core.branch_overrides import BranchOverrides, validate_overrides
from src.core.calculator import Calculator
from src.core.excel_parity.runner import run_sample as parity_run
from src.core.models import CalculationConfig, OxideComposition, Sample

_OX = {"SiO2": 70.0, "Al2O3": 12.0, "Fe2O3": 1.0, "FeO": 0.5,
       "MgO": 0.3, "CaO": 0.5, "Na2O": 3.0, "K2O": 6.0}


def test_validate_overrides_accepts_none_and_empty():
    validate_overrides(None)
    validate_overrides(BranchOverrides())


def test_validate_overrides_accepts_known_choices():
    validate_overrides(BranchOverrides(choices={"rock_type": "3"}))
    validate_overrides(BranchOverrides(choices={"coefficient_band": "H12"}))
    validate_overrides(BranchOverrides(choices={"stage_vi": "A"}))


def test_validate_overrides_rejects_unknown_decision():
    with pytest.raises(ValueError, match="Неизвестное решение"):
        validate_overrides(BranchOverrides(choices={"no_such": "1"}))


def test_validate_overrides_rejects_bad_branch():
    with pytest.raises(ValueError, match="Недопустимая ветка"):
        validate_overrides(BranchOverrides(choices={"rock_type": "9"}))


def test_validate_overrides_rejects_non_overridable():
    # Внутренние решения типов — заглушки с overridable=False (этап 6).
    with pytest.raises(ValueError, match="overridable=False"):
        validate_overrides(BranchOverrides(choices={"type3.chlorite": "3331"}))


def test_empty_overrides_do_not_change_result():
    """Пустой override == без override (дефолтное поведение не меняется)."""
    base = parity_run(_OX).names
    with_empty = parity_run(_OX, overrides=BranchOverrides()).names
    assert base == with_empty


class _SpyAlgorithm:
    def __init__(self, capture: dict):
        self._capture = capture

    def compute(self, inp):
        self._capture["overrides"] = inp.overrides
        from src.core.algorithm import AlgorithmOutput
        return AlgorithmOutput()


def test_calculator_passes_overrides_to_algorithm_input():
    captured: dict = {}
    sample = Sample(name="s", composition=OxideComposition.from_dict(_OX))
    calc = Calculator(
        config=CalculationConfig(
            calculation_engine="excel_parity",
            branch_overrides={"rock_type": "3"},
        ),
        algorithm=_SpyAlgorithm(captured),
    )
    calc.calculate_single(sample)
    assert captured["overrides"] is not None
    assert captured["overrides"].get("rock_type") == "3"


def test_calculator_without_overrides_passes_none():
    captured: dict = {}
    sample = Sample(name="s", composition=OxideComposition.from_dict(_OX))
    calc = Calculator(algorithm=_SpyAlgorithm(captured))
    calc.calculate_single(sample)
    assert captured["overrides"] is None


def test_calculator_rejects_invalid_override():
    sample = Sample(name="s", composition=OxideComposition.from_dict(_OX))
    calc = Calculator(config=CalculationConfig(branch_overrides={"rock_type": "9"}))
    with pytest.raises(ValueError):
        calc.calculate_single(sample)
