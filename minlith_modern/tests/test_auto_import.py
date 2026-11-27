"""Тесты универсального автоимпорта таблиц (auto_table)."""

from pathlib import Path

import openpyxl
import pytest

from src.io.auto_table import (
    detect_layout,
    load_samples_csv,
    load_samples_excel,
    normalize_header,
    parse_grid,
    to_float,
)


@pytest.mark.parametrize("text,field", [
    ("SiO2", "sio2"), ("SiO₂", "sio2"), ("SiO2 (%)", "sio2"),
    ("AL2O3", "al2o3"), ("Al₂O₃", "al2o3"), ("Al2O3 мас.%", "al2o3"),
    ("FeO", "feo"), ("Fe2O3", "fe2o3"), ("S", "s"), ("C", "c"),
    ("Si", "sio2"), ("Ca", "cao"), ("K", "k2o"),
])
def test_normalize_header(text, field):
    assert normalize_header(text) == field


def test_normalize_header_unknown():
    assert normalize_header("Lorem ipsum") is None
    assert normalize_header(None) is None


@pytest.mark.parametrize("raw,value", [
    (70.0, 70.0), ("70,0", 70.0), ("12 %", 12.0), ("<0.01", 0.005),
    ("", None), ("n/a", None), (None, None),
])
def test_to_float(raw, value):
    assert to_float(raw) == value


def test_detect_layout_rows():
    grid = [
        ["Отчёт", None, None, None],
        ["Name", "SiO2", "Al2O3", "FeO"],
        ["S1", 70.0, 12.0, 0.5],
    ]
    assert detect_layout(grid) == "rows"


def test_detect_layout_cols():
    grid = [
        [None, "S1", "S2"],
        ["SiO2", 70.0, 65.5],
        ["Al2O3", 12.0, 14.0],
        ["FeO", 0.5, 0.1],
    ]
    assert detect_layout(grid) == "cols"


def test_parse_grid_samples_in_rows_header_not_first():
    grid = [
        ["Отчёт по образцам", None, None, None],
        [None, None, None, None],
        ["Name", "SiO2", "Al2O3", "FeO"],
        ["S1", 70.0, 12.0, 0.5],
        ["S2", "65,5", "14,0", "<0.1"],
    ]
    samples = parse_grid(grid)
    assert [s.name for s in samples] == ["S1", "S2"]
    assert samples[0].composition.sio2 == pytest.approx(70.0)
    assert samples[1].composition.sio2 == pytest.approx(65.5)
    assert samples[1].composition.feo == pytest.approx(0.05)
    assert samples[1].composition.mgo == 0.0


def test_parse_grid_samples_in_cols():
    grid = [
        [None, "S1", "S2"],
        ["SiO2", 70.0, 65.5],
        ["Al2O3", 12.0, 14.0],
        ["FeO", 0.5, 0.1],
    ]
    samples = parse_grid(grid)
    assert [s.name for s in samples] == ["S1", "S2"]
    assert samples[1].composition.al2o3 == pytest.approx(14.0)


def test_parse_grid_unknown():
    assert parse_grid([["a", "b"], ["c", "d"]]) == []


def test_load_samples_csv_nonstandard(tmp_path: Path):
    path = tmp_path / "odd.csv"
    path.write_text(
        "# комментарий\n"
        "Образец;SiO2;Al2O3;FeO\n"
        "S1;70,0;12,0;0,5\n"
        "S2;65,5;14,0;0,1\n",
        encoding="utf-8",
    )
    samples = load_samples_csv(path)
    assert [s.name for s in samples] == ["S1", "S2"]
    assert samples[0].composition.sio2 == pytest.approx(70.0)


def test_load_samples_excel_nonstandard(tmp_path: Path):
    path = tmp_path / "odd.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Протокол анализа прибором SuperXRF-9000"])
    ws.append([])
    ws.append(["№", "SiO2 (%)", "Al2O3 (%)", "FeO (%)"])
    ws.append(["обр.1", 70.0, 12.0, 0.5])
    ws.append(["обр.2", 65.5, 14.0, 0.1])
    wb.save(str(path))

    samples = load_samples_excel(path)
    assert [s.name for s in samples] == ["обр.1", "обр.2"]
    assert samples[1].composition.al2o3 == pytest.approx(14.0)
