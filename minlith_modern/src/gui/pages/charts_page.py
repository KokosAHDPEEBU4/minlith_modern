"""Страница диаграмм — вывод нескольких диаграмм сеткой."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.charts import ChartData
from src.charts.data_builder import build_chart_data
from src.charts.engines.plotly_engine import PLOTLY_LABELS, export_plotly_html
from src.gui.widgets.chart_grid import MultiChartView

logger = logging.getLogger(__name__)


class SampleSelectorDialog(QDialog):
    """Диалог выбора элементов (минералы, диаграммы, образцы) из списка."""

    def __init__(self, names: list[str], selected: set[int], parent=None,
                 title: str = "Выбор образцов для диаграмм",
                 hint: str | None = None,
                 accept_label: str = "Применить") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(380, 420)

        self._names = names
        self._selected: set[int] = set(selected)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        if hint is None:
            hint = (f"Отметьте элементы, которые будут использованы. "
                    f"Всего: {len(names)}.")
        hint_lbl = QLabel(hint)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint_lbl)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for i, name in enumerate(names):
            item = QListWidgetItem(name)
            self._list.addItem(item)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if i in self._selected
                else Qt.CheckState.Unchecked)
        layout.addWidget(self._list, stretch=1)

        quick_row = QHBoxLayout()
        for label, handler in (
            ("Выбрать все", self._select_all),
            ("Снять все", self._select_none),
            ("Инверсия", self._invert),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton(accept_label)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _apply_state(self, state: Qt.CheckState) -> None:
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(state)

    def _select_all(self) -> None:
        self._apply_state(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        self._apply_state(Qt.CheckState.Unchecked)

    def _invert(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setCheckState(
                Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked)

    def selected_indexes(self) -> set[int]:
        return {i for i in range(self._list.count())
                if self._list.item(i).checkState() == Qt.CheckState.Checked}


class ChartsPage(QWidget):
    """Страница просмотра и экспорта диаграмм (несколько графиков сразу)."""

    dataChanged = pyqtSignal(object)  # noqa: N815 - PyQt сигнал (convention)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: ChartData | None = None
        self._results: list = []
        self._selected: set[int] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("Диаграммы")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        toolbar = QHBoxLayout()
        self._btn_select = QPushButton("Выбор образцов…")
        self._btn_select.setEnabled(False)
        self._btn_select.clicked.connect(self._open_sample_selector)
        toolbar.addWidget(self._btn_select)

        self._btn_plotly = QPushButton("Интерактивный HTML…")
        self._btn_plotly.setEnabled(False)
        self._btn_plotly.clicked.connect(self._export_plotly_html)
        toolbar.addWidget(self._btn_plotly)

        self._lbl_selection = QLabel("")
        self._lbl_selection.setStyleSheet("color: #888;")
        toolbar.addWidget(self._lbl_selection)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.tabBarClicked.connect(self._on_tab_bar_clicked)
        self._tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self._plus_widget: QWidget | None = None
        self._moving_plus = False
        self._add_plus_tab()   # «＋» — всегда последняя, как в браузере
        self._add_tab()
        layout.addWidget(self._tabs, stretch=1)

    def _current_view(self) -> MultiChartView:
        return self._tabs.currentWidget()

    def _add_plus_tab(self) -> None:
        """Добавить в конец вкладку-кнопку «＋» (без кнопки закрытия)."""
        holder = QWidget()
        index = self._tabs.addTab(holder, "＋")
        self._plus_widget = holder
        self._tabs.tabBar().setTabButton(
            index, QTabBar.ButtonPosition.RightSide, None)

    def _real_tab_count(self) -> int:
        return sum(1 for i in range(self._tabs.count())
                   if self._tabs.widget(i) is not self._plus_widget)

    def _on_tab_bar_clicked(self, index: int) -> None:
        if self._tabs.widget(index) is self._plus_widget:
            self._add_tab()

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        """Держать «＋» последней вкладкой при перетаскивании."""
        if self._moving_plus or self._plus_widget is None:
            return
        plus = self._tabs.indexOf(self._plus_widget)
        if 0 <= plus < self._tabs.count() - 1:
            self._moving_plus = True
            try:
                self._tabs.tabBar().moveTab(plus, self._tabs.count() - 1)
            finally:
                self._moving_plus = False

    def _add_tab(self, name: str | None = None) -> MultiChartView:
        view = MultiChartView()
        if name is None:
            name = f"Вкладка {self._real_tab_count() + 1}"
        plus = self._tabs.indexOf(self._plus_widget) if self._plus_widget else -1
        if plus >= 0:
            self._tabs.insertTab(plus, view, name)
        else:
            self._tabs.addTab(view, name)
        self._tabs.setCurrentWidget(view)
        if self._data is not None:
            view.set_data(self._data)
        return view

    def _close_tab(self, index: int) -> None:
        widget = self._tabs.widget(index)
        if widget is self._plus_widget or self._real_tab_count() <= 1:
            return
        if hasattr(widget, "_release_tiles"):
            widget._release_tiles()
        self._tabs.removeTab(index)

    def set_data(self, data: ChartData | None) -> None:
        self._data = data
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if hasattr(widget, "set_data"):
                widget.set_data(data)

    def set_zoom_step(self, step: float) -> None:
        """Применить шаг зума ``chart.zoom_step`` ко всем вкладкам."""
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if hasattr(widget, "set_zoom_step"):
                widget.set_zoom_step(step)

    def set_results(self, results: list) -> None:
        """Принять результаты, сбросить выбор на все образцы и построить."""
        self._results = list(results)
        self._selected = set(range(len(self._results)))
        self._rebuild()

    def _open_sample_selector(self) -> None:
        if not self._results:
            return
        names = [getattr(r, "sample_name", f"Образец {i+1}")
                 for i, r in enumerate(self._results)]
        dlg = SampleSelectorDialog(names, self._selected, self)
        if dlg.exec():
            self._selected = dlg.selected_indexes() or set(range(len(self._results)))
            self._rebuild()

    def _rebuild(self) -> None:
        self._btn_select.setEnabled(bool(self._results))
        self._btn_plotly.setEnabled(bool(self._results))
        if not self._results:
            self._lbl_selection.setText("")
            self.set_data(None)
            return
        indexes = sorted(self._selected)
        filtered = [self._results[i] for i in indexes]
        data = self.build_data_from_results(filtered)
        self._lbl_selection.setText(
            f"Образцы: {len(filtered)}/{len(self._results)}")
        self.set_data(data)
        self.dataChanged.emit(data)

    def _selected_results(self) -> list:
        """Список результатов по текущему выбору образцов."""
        return [self._results[i] for i in sorted(self._selected)]

    def _export_plotly_html(self) -> None:
        results = self._selected_results()
        if not results:
            return

        labels = sorted(PLOTLY_LABELS.values())
        label_by_title = {v: k for k, v in PLOTLY_LABELS.items()}
        dlg = SampleSelectorDialog(
            labels, set(range(len(labels))), self,
            title="Интерактивный HTML (Plotly)",
            hint=("Отметьте диаграммы, которые войдут в HTML-файл. "
                  "При выборе нескольких они будут объединены в один отчёт "
                  "со сводкой (минералы, дата/время, список диаграмм)."),
            accept_label="Сохранить",
        )
        if not dlg.exec():
            return
        chosen = sorted(dlg.selected_indexes())
        if not chosen:
            QMessageBox.warning(
                self, "Интерактивный HTML", "Выберите хотя бы одну диаграмму.")
            return
        chart_types = [label_by_title[labels[i]] for i in chosen]

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить интерактивный HTML-отчёт", "diagrams.html",
            "HTML-файл (*.html)")
        if not path:
            return
        if not path.lower().endswith(".html"):
            path += ".html"

        try:
            ok = export_plotly_html(chart_types, results, Path(path))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Plotly export failed")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить HTML:\n{exc}")
            return
        if not ok:
            QMessageBox.warning(
                self, "Ошибка", "Не удалось построить ни одной из выбранных диаграмм.")
            return

        QMessageBox.information(
            self, "Готово",
            f"Интерактивный отчёт сохранён:\n{path}\n\n"
            f"Откройте файл в браузере для взаимодействия.")

    def build_data_from_results(self, results: list) -> ChartData:
        """Построить ChartData из списка CalculationResult."""
        return build_chart_data(results)
