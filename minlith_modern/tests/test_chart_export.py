"""Tests for interactive Plotly HTML export used by the GUI."""

from __future__ import annotations

import pytest

from src.charts.engines.plotly_charts import PLOTLY_CHARTS
from src.charts.engines.plotly_engine import PLOTLY_LABELS, export_plotly_html


def test_plotly_labels_cover_all_charts() -> None:
    assert set(PLOTLY_LABELS) == set(PLOTLY_CHARTS)
    assert len(PLOTLY_LABELS) == 6


@pytest.mark.parametrize("chart_type", sorted(PLOTLY_CHARTS))
def test_export_plotly_html(result_list, tmp_path, chart_type) -> None:
    path = tmp_path / f"{chart_type}.html"
    ok = export_plotly_html(chart_type, result_list, path, title="Test")
    assert ok is True
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert len(data) > 500
    assert "<html" in data.lower()


def test_export_plotly_html_unknown_chart(result_list, tmp_path) -> None:
    path = tmp_path / "unknown.html"
    ok = export_plotly_html("nonexistent_chart", result_list, path)
    assert ok is False
    assert not path.exists()


def test_export_plotly_html_multiple_combined(result_list, tmp_path) -> None:
    path = tmp_path / "combined.html"
    ok = export_plotly_html(["bar", "acnk", "heatmap"], result_list, path)
    assert ok is True
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert len(data) > 1000
    assert "<html" in data.lower()
    assert "Дата и время генерации" in data
    assert "<div class=\"chart\">" in data


def test_export_plotly_html_empty_list(result_list, tmp_path) -> None:
    path = tmp_path / "empty.html"
    ok = export_plotly_html([], result_list, path)
    assert ok is False
    assert not path.exists()


def test_export_plotly_html_partial_unknown(result_list, tmp_path) -> None:
    path = tmp_path / "partial.html"
    ok = export_plotly_html(["bar", "nope"], result_list, path)
    assert ok is False
    assert not path.exists()
