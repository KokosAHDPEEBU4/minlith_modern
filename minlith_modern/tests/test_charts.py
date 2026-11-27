"""Tests for all matplotlib chart plugins (render without errors)."""

from __future__ import annotations

import numpy as np
import pytest

from src.charts.base import ChartData
from src.charts.built_in import BUILTIN_CHARTS


@pytest.fixture(scope="module")
def chart_data() -> ChartData:
    """Shared ChartData with 5 synthetic samples for all chart tests."""
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
        "feo": np.array([0.02, -0.15, 0.08, -0.01, 0.0]),
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


# ── All 8 built-in charts (минимальный рабочий набор) ──

CHART_TEST_PARAMS = [
    ("BarChart", True, False),
    ("PieChart", True, False),
    ("DefectChart", True, True),
    ("ACNKChart", False, True),
    ("HeatmapChart", True, False),
    ("RockTypeChart", False, False),
    ("BoxPlotChart", True, False),
    ("PCABiplot", True, False),
]


def _find_plugin(name: str):
    for c in BUILTIN_CHARTS:
        if type(c).__name__ == name:
            return c
    pytest.fail(f"Chart plugin '{name}' not found in BUILTIN_CHARTS")


@pytest.mark.parametrize("cls_name,needs_minerals,needs_oxides", CHART_TEST_PARAMS)
def test_chart_renders(
    cls_name: str, needs_minerals: bool, needs_oxides: bool, chart_data: ChartData
):
    plugin = _find_plugin(cls_name)
    fig = plugin.render(chart_data)
    assert fig is not None, f"{cls_name}.render() returned None"
    assert hasattr(fig, "savefig"), f"{cls_name}.render() did not return a matplotlib Figure"
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_bar_chart_stacked_normalized(chart_data: ChartData):
    plugin = _find_plugin("BarChart")
    fig = plugin.render(chart_data, stacked=True, normalized=True)
    assert fig is not None
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_bar_chart_grouped(chart_data: ChartData):
    plugin = _find_plugin("BarChart")
    fig = plugin.render(chart_data, stacked=False, normalized=False)
    assert fig is not None
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_pie_chart_sample_idx(chart_data: ChartData):
    plugin = _find_plugin("PieChart")
    fig = plugin.render(chart_data, sample_idx=2)
    assert fig is not None
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_defect_chart_stacked(chart_data: ChartData):
    plugin = _find_plugin("DefectChart")
    fig = plugin.render(chart_data, stacked=True, sample_idx=1)
    assert fig is not None
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_empty_chart_data():
    empty = ChartData()
    for plugin in BUILTIN_CHARTS:
        fig = plugin.render(empty)
        assert fig is not None, f"{type(plugin).__name__}.render(empty) returned None"
        import matplotlib.pyplot as plt
        plt.close(fig)


def test_builtin_charts_registry_lazy_and_stable():
    """Ленивый реестр: тот же список объектов при повторном доступе.

    Регрессия на PEP 562 __getattr__ в src/charts(/built_in)/__init__:
    порядок BUILTIN_CHARTS позиционный (индекс = type_id в GUI),
    повторный импорт обязан возвращать те же экземпляры.
    """
    import importlib

    import src.charts as charts_pkg
    import src.charts.built_in as built_in_pkg

    again = importlib.reload(built_in_pkg)  # reload сбрасывает ленивый кэш
    charts_pkg.BUILTIN_CHARTS  # noqa: B018 — доступ через __getattr__ родителя
    assert len(again.BUILTIN_CHARTS) == len(BUILTIN_CHARTS) == 8
    assert [type(p) for p in again.BUILTIN_CHARTS] == [type(p) for p in BUILTIN_CHARTS]
    assert len({p.get_name() for p in BUILTIN_CHARTS}) == 8
