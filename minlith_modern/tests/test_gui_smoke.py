"""Smoke-тесты GUI: страницы диаграмм и главное окно конструируются (offscreen).

Ловят регрессию вида «атрибут страницы переименован, а main_window всё ещё
обращается к старому» — именно из-за неё приложение не запускалось.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        try:
            app = QApplication([])
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"Qt недоступен: {exc}")
    return app


def test_charts_and_output_pages_zoom(qapp):
    """У страниц диаграмм есть общий метод set_zoom_step (вкладки/сетка)."""
    from src.gui.pages.charts_page import ChartsPage
    from src.gui.pages.output_page import OutputPage

    cp = ChartsPage()
    cp.set_zoom_step(1.3)

    op = OutputPage()
    op.set_zoom_step(1.3)


def test_charts_page_plus_tab_adds_and_stays_last(qapp):
    """«＋» — последняя вкладка; клик по ней добавляет вкладку (регрессия)."""
    from src.gui.pages.charts_page import ChartsPage

    page = ChartsPage()
    assert page._real_tab_count() == 1
    assert page._tabs.widget(page._tabs.count() - 1) is page._plus_widget

    # эмуляция клика по «＋» через сигнал (как это делает пользователь)
    page._tabs.tabBarClicked.emit(page._tabs.indexOf(page._plus_widget))
    assert page._real_tab_count() == 2
    assert page._tabs.widget(page._tabs.count() - 1) is page._plus_widget

    # «＋» нельзя закрыть; set_data/zoom не падают на вкладке-заглушке
    page._close_tab(page._tabs.indexOf(page._plus_widget))
    assert page._tabs.widget(page._tabs.count() - 1) is page._plus_widget
    page.set_data(None)
    page.set_zoom_step(1.2)


def test_calculation_dialog_select_all_samples(qapp):
    """В диалоге расчёта есть выбор всех образцов."""
    from src.core.calculator import Calculator
    from src.core.models import OxideComposition, Sample
    from src.gui.dialogs.calculation_dialog import CalculationDialog

    samples = [Sample(name=f"S{i}", composition=OxideComposition(sio2=50.0))
               for i in range(3)]
    dialog = CalculationDialog(Calculator(), samples)
    dialog._select_all_samples()
    assert all(dialog._samples_list.item(i).isSelected() for i in range(3))
    dialog._clear_sample_selection()
    assert not any(dialog._samples_list.item(i).isSelected() for i in range(3))


def test_hover_math_nearest_point():
    """Наведение на точку: ближайшая в пределах порога, иначе None."""
    import numpy as np

    from src.gui.widgets.hover_math import nearest_point_index

    points = np.array([[0.0, 0.0], [100.0, 0.0], [0.0, 100.0]])
    assert nearest_point_index(3.0, 3.0, points, 12.0) == 0
    assert nearest_point_index(50.0, 50.0, points, 12.0) is None
    assert nearest_point_index(0.0, 0.0, None) is None
    assert nearest_point_index(0.0, 0.0, np.zeros((0, 2))) is None


def test_chart_view_sample_selection_signal(qapp):
    """Уровень выбора образцов в MultiChartView: чекбоксы + сигнал."""
    from src.gui.widgets.chart_grid import MultiChartView

    view = MultiChartView()
    received: list[set] = []
    view.samplesChanged.connect(lambda sel: received.append(set(sel)))

    view.set_sample_names(["A", "B", "C"], {0, 2})
    assert view.selected_sample_indexes() == {0, 2}
    assert received == []  # при построении сигнал не эмитится

    view._sample_checkboxes[1].setChecked(True)
    assert view.selected_sample_indexes() == {0, 1, 2}
    assert received and received[-1] == {0, 1, 2}

    view._set_samples(False)
    assert view.selected_sample_indexes() == set()


def test_charts_page_samples_sync_across_tabs(qapp):
    """Выбор образцов на странице диаграмм синхронизируется между вкладками."""
    from src.core.calculator import Calculator
    from src.core.models import OxideComposition, Sample
    from src.gui.pages.charts_page import ChartsPage

    samples = [
        Sample(name=f"S{i}", composition=OxideComposition(
            sio2=50.0, al2o3=15.0, feo=5.0, mgo=3.0, cao=4.0, na2o=3.0, k2o=2.0))
        for i in range(3)
    ]
    results = Calculator().calculate(samples)

    page = ChartsPage()
    page.set_results(results)
    page._add_tab()   # вторая реальная вкладка (первая — «＋»)

    for i in range(page._tabs.count()):
        widget = page._tabs.widget(i)
        if hasattr(widget, "selected_sample_indexes"):
            assert widget.selected_sample_indexes() == {0, 1, 2}

    first = page._tabs.widget(0)
    second = page._tabs.widget(1)
    first._sample_checkboxes[1].setChecked(False)
    assert page._selected == {0, 2}
    assert second.selected_sample_indexes() == {0, 2}


def test_branch_graph_page_override_and_recalc(qapp):
    """Страница «Граф»: выбор ветки → пересчёт с override, подсветка forced."""
    from src.core.branch_report import forced_branch_ids
    from src.core.calculator import Calculator
    from src.core.models import OxideComposition, Sample
    from src.gui.pages.branch_graph_page import BranchGraphPage

    sample = Sample(name="S", composition=OxideComposition(
        sio2=70.0, al2o3=12.0, fe2o3=1.0, feo=0.5,
        mgo=0.3, cao=0.5, na2o=3.0, k2o=6.0))
    calc = Calculator()
    results = calc.calculate([sample])

    page = BranchGraphPage(calculator=calc)
    page.set_results(results)
    assert page._sample_combo.count() == 1
    assert page._tree.topLevelItemCount() >= 3

    page._overrides["rock_type"] = "3"
    page._on_recalculate()
    assert "rock_type_3" in page._current_result.branch_path["labels"]
    assert "3" in forced_branch_ids(page._current_result.branch_path)


def test_main_window_has_branch_graph_page(qapp):
    """MainWindow содержит страницу «Граф»; переключение не падает."""
    from src.gui.main_window import MainWindow

    window = MainWindow()
    assert window._branch_graph_page is not None
    window._switch_page(9)   # «Граф»
    assert window._stack.currentWidget() is window._branch_graph_page


def test_engine_compare_dialog(qapp):
    """Диалог сравнения движков заполняет таблицу по минералам."""
    from src.core.calculator import Calculator
    from src.core.engine_compare import MINERAL_ORDER
    from src.core.models import OxideComposition, Sample
    from src.gui.dialogs.engine_compare_dialog import EngineCompareDialog

    sample = Sample(name="S", composition=OxideComposition(
        sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06, mgo=2.35,
        cao=0.28, na2o=0.94, k2o=3.45, p2o5=0.31, mno=0.157502))
    results = Calculator().calculate([sample])
    dialog = EngineCompareDialog(results)
    dialog._on_compare()
    assert dialog._table.rowCount() == len(MINERAL_ORDER)


def test_main_window_constructs_and_applies_zoom(qapp):
    """Главное окно создаётся, а _apply_zoom_step не падает (регрессия)."""
    from src.gui.main_window import MainWindow

    window = MainWindow()
    window._apply_zoom_step()
    assert window._charts_page is not None
    assert window._output_page is not None
