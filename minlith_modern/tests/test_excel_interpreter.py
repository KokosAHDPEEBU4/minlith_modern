"""Тесты мини-интерпретатора Excel-формул (src/core/excel_port/interpreter.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.excel_port.interpreter import (
    FormulaEvaluator,
    xround,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"


class TestXround:
    """Excel ROUND — half away from zero (не как Python round)."""

    def test_half_up_positive(self):
        assert xround(2.5, 0) == 3.0
        assert xround(3.5, 0) == 4.0

    def test_half_away_negative(self):
        assert xround(-2.5, 0) == -3.0
        assert xround(-3.5, 0) == -4.0

    def test_decimals(self):
        assert xround(2.567, 2) == 2.57
        assert xround(-2.567, 2) == -2.57
        assert xround(2.567, 1) == 2.6

    def test_not_bankers(self):
        # Python round(0.5)=0 (banker's), Excel ROUND(0.5)=1
        assert xround(0.5, 0) == 1.0
        assert round(0.5) == 0  # sanity: python отличается


class _Resolver:
    def __init__(self, values=None):
        self.values = values or {}

    def resolve(self, name):
        return self.values.get(name)

    def resolve_range(self, start, end):
        return self.values.get(f"range:{start}:{end}", [])


def _eval(formula, values):
    return FormulaEvaluator(_Resolver(values)).eval_formula(formula)


class TestArithmetic:
    def test_basic(self):
        assert _eval("=1+2*3", {}) == 7.0

    def test_parens(self):
        assert _eval("=(1+2)*3", {}) == 9.0

    def test_unary_minus(self):
        assert _eval("=-5.18*0.1+4.42", {}) == pytest.approx(3.902)

    def test_slash(self):
        assert _eval("=10/4", {}) == 2.5

    def test_division_by_zero_returns_none(self):
        assert _eval("=5/0", {}) is None


class TestComparisons:
    def test_le(self):
        assert _eval("=IF(TRUE,5<=3)", {}) is False

    def test_eq(self):
        assert _eval("=IF(TRUE,C271=0)", {"C271": 0}) is True

    def test_ge(self):
        assert _eval("=IF(TRUE,3>=3)", {}) is True


class TestFunctions:
    def test_if(self):
        assert _eval("=IF(TRUE,1,2)", {}) == 1.0
        assert _eval("=IF(FALSE,1,2)", {}) == 2.0

    def test_and(self):
        assert _eval("=AND(TRUE,1>0,2<5)", {}) is True
        assert _eval("=AND(TRUE,1<0)", {}) is False

    def test_or(self):
        assert _eval("=OR(TRUE,1<0,2<0)", {}) is True

    def test_round(self):
        assert _eval("=ROUND(52.5/60.09*10000,0)", {}) == 8737.0

    def test_sum_range(self):
        v = _eval("=SUM(E149:AC149)", {"range:E149:AC149": [1.0, 2.0, 3.0]})
        assert v == 6.0

    def test_counta_range(self):
        v = _eval("=COUNTA(A290:A601)", {"range:A290:A601": [1.0, None, "", 2.0]})
        assert v == 2.0


class TestRefs:
    def test_a1_ref(self):
        assert _eval("=B2*2", {"B2": 21.0}) == 42.0

    def test_abs_ref(self):
        assert _eval("=E149*100/$D$151", {"E149": 1.0, "D151": 4.0}) == 25.0

    def test_named(self):
        assert _eval("=na+k", {"na": 1.0, "k": 2.0}) == 3.0


class TestRealFormulas:
    """Реальные формулы из листов — парсятся и считаются."""

    def test_fe_conversion(self):
        # FeO_total ф.е. из T-O2: (1.71*0.9 + 8.06)/71.85*10000
        v = _eval("=ROUND((B5*0.9+B6)*10000/C6,0)",
                  {"B5": 1.71, "B6": 8.06, "C6": 71.85})
        assert v == 1336.0

    def test_ca_correction(self):
        # D8 = CaO_ф.е. - (апатит 3.33*P2O5 + F/2), T-O2 -> 50 - 73 = -23
        v = _eval(
            "=ROUND(B8*10000/C8,0)-ROUND(3.33*B11/C11*10000+B15/C15*10000/2,0)",
            {"B8": 0.28, "C8": 56.08, "B11": 0.31, "C11": 141.95,
             "B15": 0.0, "C15": 19.0})
        assert v == -23.0

    def test_k_coefficient(self):
        # k1 для F=0.696 (диапазон 3): ROUND(5.13-5.32*0.696,3)
        v = _eval("=ROUND(5.13-5.32*G2,3)", {"G2": 0.696})
        assert v == pytest.approx(1.427)


@pytest.mark.skipif(not (DATA_DIR / "workbook_raw.json").exists(),
                    reason="workbook_raw.json не извлечён")
class TestAllWorkbookFormulas:
    """Все 931 формула из .xlsm должны парситься без ошибок."""

    def test_all_formulas_parse(self):
        data = json.loads((DATA_DIR / "workbook_raw.json").read_text(encoding="utf-8"))
        ev = FormulaEvaluator(_Resolver())
        total = 0
        errors = []
        for sn in ["Нач+Type 12", "Нач+Type 3"]:
            for coord, c in data["sheets"][sn]["cells"].items():
                f = c.get("formula")
                if not f:
                    continue
                total += 1
                try:
                    ev.eval_formula(f)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"[{sn}] {coord}: {f} -> {e}")
        assert total == 931
        assert not errors, "\n".join(errors[:20])
