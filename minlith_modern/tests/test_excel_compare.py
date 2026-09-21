"""Тесты сравнения режимов округления (Phase 4)."""
import json
from pathlib import Path

import pytest

from src.core.excel_port.compare import compare_sample, write_csv

DATA = Path(__file__).resolve().parent.parent / "src" / "core" / "excel_port" / "data"


@pytest.fixture(scope="module")
def samples():
    return json.loads((DATA / "samples.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def multi():
    return json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["BK-1", "T-O2",
                                   "arkose_t1", "granite_t2", "basalt_t3",
                                   "quartzite_t4", "highal_t5"])
def test_compare_runs(samples, multi, name, tmp_path):
    comp = samples[name] if name in samples else multi[name]["input"]
    res = compare_sample(name, comp)
    assert res.name == name
    assert res.assignments
    assert all(d > 1e-9 for d, _, _, _ in res.errors)
    # отклонения упорядочены по убыванию
    ds = [d for d, _, _, _ in res.errors]
    assert ds == sorted(ds, reverse=True)


def test_compare_csv_written(samples, tmp_path):
    res = compare_sample("BK-1", samples["BK-1"])
    out = tmp_path / "cmp.csv"
    write_csv([res], out)
    content = out.read_text(encoding="utf-8")
    assert content.startswith("sample,variable,")
    assert "BK-1" in content
