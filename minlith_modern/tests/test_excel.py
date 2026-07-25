"""Tests for io/excel.py — Excel import/export."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.core.models import OxideComposition, Sample
from src.io.excel import (
    MINERAL_FIELD_MAP,
    load_samples,
    save_results,
    save_results_csv,
    save_results_json,
)


def _make_sample(name: str = "Test") -> Sample:
    return Sample(
        name=name,
        composition=OxideComposition(
            sio2=52.5, tio2=0.99, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45, p2o5=0.31, mno=0.16,
        ),
    )


class TestMineralFieldMap:
    def test_all_codes_present(self):
        from src.core.constants import MINERAL_CODES
        for code in MINERAL_CODES:
            assert code in MINERAL_FIELD_MAP, f"Missing: {code}"

    def test_known_values(self):
        assert MINERAL_FIELD_MAP["Ab"] == "ab"
        assert MINERAL_FIELD_MAP["Or"] == "or_"
        assert MINERAL_FIELD_MAP["Q"] == "q"


class TestSaveResultsXlsx:
    def test_creates_file(self, tmp_path):
        from src.core.models import CalculationResult, AdaptiveCoefficients, RockType, MineralComposition
        result = CalculationResult(
            sample_name="T-O2",
            input_composition=_make_sample().composition,
            formula_units=None,
            coefficients=AdaptiveCoefficients(k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.5, A=0.5),
            rock_type=RockType.TYPE_5,
            minerals_formula=MineralComposition(),
            minerals_weight=MineralComposition(ab=7.82, q=31.38, ill=36.26, chl=25.74),
            defect={"sio2": 1.0, "al2o3": -0.5},
            warnings=[],
        )
        path = tmp_path / "test.xlsx"
        save_results(path, [result])
        assert path.exists()

    def test_has_all_sheets(self, tmp_path):
        from src.core.models import CalculationResult, AdaptiveCoefficients, RockType, MineralComposition
        result = CalculationResult(
            sample_name="Test",
            input_composition=_make_sample().composition,
            formula_units=None,
            coefficients=AdaptiveCoefficients(k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.5, A=0.5),
            rock_type=RockType.TYPE_5,
            minerals_formula=MineralComposition(),
            minerals_weight=MineralComposition(ab=7.82),
            defect={},
            warnings=[],
        )
        path = tmp_path / "test.xlsx"
        save_results(path, [result])
        import openpyxl
        wb = openpyxl.load_workbook(str(path))
        assert "Results" in wb.sheetnames
        assert "Input" in wb.sheetnames
        assert "Defect" in wb.sheetnames
        assert "GeoParams" in wb.sheetnames


class TestSaveResultsCsv:
    def test_creates_file(self, tmp_path):
        from src.core.models import CalculationResult, AdaptiveCoefficients, RockType, MineralComposition
        result = CalculationResult(
            sample_name="Test",
            input_composition=_make_sample().composition,
            formula_units=None,
            coefficients=AdaptiveCoefficients(k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.5, A=0.5),
            rock_type=RockType.TYPE_5,
            minerals_formula=MineralComposition(),
            minerals_weight=MineralComposition(ab=7.82),
            defect={},
            warnings=[],
        )
        path = tmp_path / "test.csv"
        save_results_csv(path, [result])
        assert path.exists()
        content = path.read_text(encoding="utf-8-sig")
        assert "Test" in content
