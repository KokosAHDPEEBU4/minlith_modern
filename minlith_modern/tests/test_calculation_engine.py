"""Движок расчёта: имена, разрешение режимов и миграция старых значений."""

from __future__ import annotations

import json

from src.core.calculator import Calculator
from src.core.excel_parity.algorithm import ExcelParityAlgorithm
from src.core.geological_theory import GeologicalTheoryAlgorithm
from src.core.models import (
    CALCULATION_ENGINES,
    LEGACY_ENGINE_ALIASES,
    CalculationConfig,
)
from src.utils.config import ConfigManager


def test_engine_names_and_aliases() -> None:
    assert CALCULATION_ENGINES == (
        "excel_parity", "excel_exact", "geological_theory", "python_rework",
    )
    assert LEGACY_ENGINE_ALIASES == {
        "clean": "excel_parity",
        "stub": "geological_theory",
        "custom": "python_rework",
    }


def test_calculator_resolves_new_engine_names() -> None:
    from src.core.excel_exact.algorithm import ExcelExactAlgorithm

    assert isinstance(
        Calculator(
            config=CalculationConfig(calculation_engine="excel_parity")
        ).algorithm,
        ExcelParityAlgorithm,
    )
    assert isinstance(
        Calculator(
            config=CalculationConfig(calculation_engine="excel_exact")
        ).algorithm,
        ExcelExactAlgorithm,
    )
    assert isinstance(
        Calculator(
            config=CalculationConfig(calculation_engine="geological_theory")
        ).algorithm,
        GeologicalTheoryAlgorithm,
    )


def test_calculator_accepts_legacy_engine_names() -> None:
    calc = Calculator(config=CalculationConfig(calculation_engine="clean"))
    assert isinstance(calc.algorithm, ExcelParityAlgorithm)


def test_config_migrates_legacy_key_and_value(tmp_path) -> None:
    cfg_path = tmp_path / "settings.json"
    cfg_path.write_text(json.dumps({"algorithm_mode": "clean"}), encoding="utf-8")
    cfg = ConfigManager(cfg_path)
    assert cfg.get("calculation_engine") == "excel_parity"
    assert cfg.get("algorithm_mode") is None
