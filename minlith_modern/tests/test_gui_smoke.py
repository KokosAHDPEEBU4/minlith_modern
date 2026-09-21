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


def test_main_window_constructs_and_applies_zoom(qapp):
    """Главное окно создаётся, а _apply_zoom_step не падает (регрессия)."""
    from src.gui.main_window import MainWindow

    window = MainWindow()
    window._apply_zoom_step()
    assert window._charts_page is not None
    assert window._output_page is not None
