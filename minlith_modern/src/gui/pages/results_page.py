"""Страница результатов — таблица результатов расчёта."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import CalculationResult
from src.gui.widgets.mineral_table import MineralTable

logger = logging.getLogger(__name__)


class ResultsPage(QWidget):
    """Страница отображения результатов расчёта."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[CalculationResult] = []

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Результаты"))
        header.addStretch()

        self._btn_export_all = QPushButton("Экспорт всех в .xlsx")
        self._btn_export_all.clicked.connect(self._on_export_all)
        header.addWidget(self._btn_export_all)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._summary_table = QTableWidget()
        self._summary_table.setAlternatingRowColors(True)
        self._summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._summary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._summary_table.verticalHeader().setVisible(False)
        self._summary_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._summary_table)

        self._detail = MineralTable()
        splitter.addWidget(self._detail)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def add_result(self, result: CalculationResult) -> None:
        self._results.append(result)
        self._rebuild_summary()

    def set_results(self, results: list[CalculationResult]) -> None:
        self._results = list(results)
        self._rebuild_summary()

    def clear(self) -> None:
        self._results.clear()
        self._summary_table.setRowCount(0)
        self._detail.clear()

    def _rebuild_summary(self) -> None:
        minerals = ["Ab", "An", "Or", "Q", "Ill", "Chl", "Kn", "Mm", "Gb", "Ap", "Cc", "Dl"]
        fields = ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb", "ap", "cc", "dl"]

        cols = ["Образец", "Тип", "F", "A", "CIA", "ICV", "PIA", "ASI", "AI"] + minerals
        self._summary_table.setColumnCount(len(cols))
        self._summary_table.setHorizontalHeaderLabels(cols)
        h = self._summary_table.horizontalHeader()
        for c in range(len(cols)):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        self._summary_table.setRowCount(len(self._results))
        for i, r in enumerate(self._results):
            self._summary_table.setItem(i, 0, QTableWidgetItem(r.sample_name))
            self._summary_table.setItem(i, 1, QTableWidgetItem(r.rock_type.name))

            f_item = QTableWidgetItem(f"{r.coefficients.F:.3f}")
            f_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._summary_table.setItem(i, 2, f_item)

            a_item = QTableWidgetItem(f"{r.coefficients.A:.3f}")
            a_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._summary_table.setItem(i, 3, a_item)

            # Geo parameters
            geo = r.geo_params
            for j, attr in enumerate(["CIA", "ICV", "PIA", "ASI", "AI"], start=4):
                val = getattr(geo, attr, 0.0) if geo else 0.0
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._summary_table.setItem(i, j, item)

            for j, field in enumerate(fields, start=9):
                val = getattr(r.minerals_weight, field, 0.0)
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._summary_table.setItem(i, j, item)

    def _on_selection_changed(self) -> None:
        rows = self._summary_table.selectionModel().selectedRows()
        if rows:
            idx = rows[0].row()
            if idx < len(self._results):
                r = self._results[idx]
                self._detail.set_minerals(r.minerals_weight, r.minerals_formula)

    def _on_export_all(self) -> None:
        if not self._results:
            QMessageBox.information(self, "Экспорт", "Нет результатов для экспорта.")
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт результатов", "minlith_results.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        from src.io.excel import save_results
        try:
            save_results(path, self._results)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
