"""Страница диаграмм — вывод нескольких диаграмм сеткой."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.charts import ChartData
from src.gui.widgets.chart_grid import MultiChartView

logger = logging.getLogger(__name__)


class SampleSelectorDialog(QDialog):
    """Диалог выбора образцов для построения диаграмм."""

    def __init__(self, names: list[str], selected: set[int], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор образцов для диаграмм")
        self.setMinimumSize(360, 420)

        self._names = names
        self._selected: set[int] = set(selected)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QLabel(
            f"Отметьте образцы, которые будут участвовать в диаграммах. "
            f"Всего: {len(names)}.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

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
        btn_ok = QPushButton("Применить")
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

    dataChanged = pyqtSignal(object)  # ChartData

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None
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

        self._lbl_selection = QLabel("")
        self._lbl_selection.setStyleSheet("color: #888;")
        toolbar.addWidget(self._lbl_selection)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._view = MultiChartView()
        layout.addWidget(self._view, stretch=1)

    def set_data(self, data: Optional[ChartData]) -> None:
        self._data = data
        self._view.set_data(data)

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

    def build_data_from_results(self, results: list) -> ChartData:
        """Построить ChartData из списка CalculationResult."""
        import numpy as np
        from src.charts import ChartData

        data = ChartData()
        data.sample_names = [r.sample_name for r in results]

        mineral_fields = ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                          "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]
        for field in mineral_fields:
            arr = np.array([getattr(r.minerals_weight, field, 0.0) for r in results])
            data.minerals_wt[field] = arr

        oxide_fields = ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]
        for field in oxide_fields:
            arr = np.array([getattr(r.input_composition, field, 0.0) for r in results])
            data.oxides[field] = arr

        data.rock_types = [int(r.rock_type) for r in results]

        if results and results[0].defect:
            for oxide in results[0].defect:
                arr = np.array([r.defect.get(oxide, 0.0) for r in results])
                data.defect[oxide] = arr

        data.F_values = [r.coefficients.F for r in results]
        data.A_values = [r.coefficients.A for r in results]

        return data