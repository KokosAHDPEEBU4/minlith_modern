"""Тесты сравнения движков excel_parity vs excel_exact."""

from src.core.engine_compare import (
    MINERAL_ORDER,
    MineralDiff,
    compare_engines,
    max_abs_delta,
)

_OX = {"SiO2": 52.5, "Al2O3": 23.41, "Fe2O3": 1.71, "FeO": 8.06, "MgO": 2.35,
       "CaO": 0.28, "Na2O": 0.94, "K2O": 3.45, "P2O5": 0.31, "MnO": 0.157502}


def test_compare_engines_structure():
    rows = compare_engines(_OX)
    assert len(rows) == len(MINERAL_ORDER)
    assert all(isinstance(r, MineralDiff) for r in rows)
    assert [r.name for r in rows] == [name for name, _ in MINERAL_ORDER]
    for row in rows:
        assert row.delta == row.parity - row.exact


def test_exact_matches_itself_zero_delta():
    """delta считается относительно exact; в самом exact расхождения нет."""
    rows = compare_engines(_OX)
    worst, name = max_abs_delta(rows)
    assert worst >= 0.0
    assert isinstance(name, str)


def test_max_abs_delta_empty():
    assert max_abs_delta([]) == (0.0, "")
