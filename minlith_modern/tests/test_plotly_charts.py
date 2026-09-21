"""Tests for Plotly interactive chart generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.charts.base import ChartData


@pytest.fixture(scope="module")
def chart_data() -> ChartData:
    names = ["Granite", "Basalt", "Shale", "Sandstone", "Quartzite"]

    minerals_wt = {
        "ab": np.array([15.0, 8.0, 10.0, 6.0, 2.0]),
        "an": np.array([5.0, 12.0, 8.0, 4.0, 1.0]),
        "or_": np.array([20.0, 3.0, 15.0, 8.0, 5.0]),
        "q": np.array([30.0, 5.0, 20.0, 35.0, 60.0]),
        "ill": np.array([8.0, 5.0, 18.0, 10.0, 3.0]),
        "chl": np.array([5.0, 15.0, 12.0, 6.0, 2.0]),
        "kn": np.array([3.0, 8.0, 6.0, 4.0, 1.0]),
        "mm": np.array([2.0, 4.0, 3.0, 2.0, 1.0]),
        "gb": np.array([1.0, 3.0, 2.0, 1.0, 0.5]),
        "ap": np.array([0.5, 1.0, 0.8, 0.3, 0.1]),
        "cc": np.array([0.0, 0.5, 0.3, 0.2, 0.1]),
        "dl": np.array([0.0, 0.3, 0.2, 0.1, 0.0]),
        "ank": np.array([0.0, 0.2, 0.1, 0.0, 0.0]),
        "rch": np.array([0.0, 0.1, 0.0, 0.0, 0.0]),
        "sd": np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
        "srp": np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
        "mst": np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
        "ht": np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
        "prl": np.array([1.0, 2.0, 3.0, 2.0, 1.0]),
    }

    oxides = {
        "sio2": np.array([72.0, 50.0, 58.0, 88.0, 95.0]),
        "al2o3": np.array([14.0, 14.5, 18.0, 5.0, 2.5]),
        "fe2o3": np.array([1.5, 3.0, 5.0, 1.0, 0.5]),
        "feo": np.array([1.0, 9.0, 4.0, 0.8, 0.3]),
        "mgo": np.array([0.5, 8.0, 2.5, 0.5, 0.2]),
        "cao": np.array([1.5, 10.5, 3.0, 1.5, 0.1]),
        "na2o": np.array([3.5, 2.5, 1.5, 0.8, 0.2]),
        "k2o": np.array([4.5, 0.5, 3.5, 1.2, 0.5]),
        "p2o5": np.array([0.2, 0.3, 0.2, 0.0, 0.0]),
        "mno": np.array([0.05, 0.18, 0.08, 0.02, 0.01]),
    }

    defect = {
        "sio2": np.array([0.1, -0.2, 0.05, 0.15, -0.05]),
        "al2o3": np.array([-0.05, 0.1, -0.08, 0.02, 0.01]),
    }

    return ChartData(
        sample_names=names,
        oxides=oxides,
        minerals_wt=minerals_wt,
        defect=defect,
        rock_types=[1, 5, 3, 2, 4],
        F_values=[0.4, 0.7, 0.55, 0.45, 0.35],
        A_values=[0.15, 0.08, 0.12, 0.10, 0.05],
        metadata={
            "k_values": {
                "k1": [1.0, 1.5, 1.2, 1.1, 0.8],
                "k2": [2.0, 3.0, 2.5, 2.2, 1.6],
                "k3": [0.5, 0.8, 0.6, 0.55, 0.4],
                "k4": [3.0, 4.5, 3.8, 3.3, 2.5],
            },
        },
    )


@pytest.fixture
def tmp_html(tmp_path):
    return tmp_path / "chart.html"


PLOTLY_CHARTS = [
    ("bar", {}),
    ("pie", {"sample_idx": 0}),
    ("defect", {"sample_idx": 1}),
    ("heatmap", {}),
    ("correlation", {}),
    ("boxplot", {}),
    ("violin", {}),
    ("parallel", {}),
    ("rock_type", {}),
    ("kf", {}),
    ("qapf", {}),
    ("acnk", {}),
    ("afm", {}),
]


@pytest.mark.parametrize("chart_key,kwargs", PLOTLY_CHARTS)
def test_plotly_chart_creates_html(
    chart_key: str, kwargs: dict, chart_data: ChartData, tmp_html: Path
):
    from src.charts.engines.plotly_charts import PLOTLY_CHARTS
    func = PLOTLY_CHARTS.get(chart_key)
    if func is None:
        pytest.skip(f"{chart_key} not in PLOTLY_CHARTS")
    func(chart_data, tmp_html, **kwargs)
    assert tmp_html.exists(), f"{chart_key} did not create {tmp_html}"
    content = tmp_html.read_text(encoding="utf-8")
    assert len(content) > 100, f"{chart_key} produced empty HTML"
    assert ("plotly" in content.lower() or "<html" in content.lower()), (
        f"{chart_key} HTML missing plotly content"
    )


def test_empty_data_plotly(chart_data, tmp_html):
    from src.charts.engines.plotly_charts import PLOTLY_CHARTS
    func = PLOTLY_CHARTS.get("bar")
    empty = ChartData()
    func(empty, tmp_html)
    # should not crash, file may or may not be created
