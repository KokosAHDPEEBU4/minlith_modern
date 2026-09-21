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


def test_main_window_constructs_and_applies_zoom(qapp):
    """Главное окно создаётся, а _apply_zoom_step не падает (регрессия)."""
    from src.gui.main_window import MainWindow

    window = MainWindow()
    window._apply_zoom_step()
    assert window._charts_page is not None
    assert window._output_page is not None
