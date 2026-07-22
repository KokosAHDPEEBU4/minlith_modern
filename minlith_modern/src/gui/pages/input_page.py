"""Input page — oxide composition form + calculate button."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.calculator import Calculator
from src.core.models import CalculationResult, OxideComposition, Sample
from src.gui.widgets.oxide_table import OxideTable

logger = logging.getLogger(__name__)


class InputPage(QWidget):
    """Page for manual oxide input and calculation."""

    calculation_done = pyqtSignal(object)  # emits CalculationResult

    def __init__(self, calculator: Calculator, parent=None) -> None:
        super().__init__(parent)
        self._calculator = calculator
        self._last_result: Optional[CalculationResult] = None

        layout = QVBoxLayout(self)

        header = QLabel("Input")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # Sample name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Sample name:"))
        self._name_edit = QLineEdit("Sample")
        self._name_edit.setFixedWidth(200)
        name_row.addWidget(self._name_edit)
        name_row.addStretch()
        layout.addLayout(name_row)

        # Oxide table
        self._oxide_table = OxideTable()
        layout.addWidget(self._oxide_table)

        # Sum display
        self._sum_label = QLabel("Sum: 0.00%")
        self._sum_label.setStyleSheet("padding: 4px; font-weight: bold;")
        layout.addWidget(self._sum_label)

        self._oxide_table.value_changed.connect(self._update_sum)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_calculate = QPushButton("  Calculate  ")
        self._btn_calculate.clicked.connect(self._on_calculate)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_calculate)

        self._btn_export = QPushButton("Export .xlsx")
        self._btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(self._btn_export)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._update_sum()

    def _update_sum(self) -> None:
        total = self._oxide_table.get_sum()
        self._sum_label.setText(f"Sum: {total:.2f}%")
        if 98 <= total <= 102:
            self._sum_label.setStyleSheet("padding: 4px; font-weight: bold; color: #4a9eff;")
        elif total < 98:
            self._sum_label.setStyleSheet("padding: 4px; font-weight: bold; color: #ff6b6b;")
        else:
            self._sum_label.setStyleSheet("padding: 4px; font-weight: bold; color: #ffa94d;")

    def _on_calculate(self) -> None:
        comp = self._oxide_table.get_composition()
        if comp.sio2 == 0:
            QMessageBox.warning(self, "Input Error", "SiO2 must be non-zero.")
            return

        name = self._name_edit.text().strip() or "Sample"
        sample = Sample(name=name, composition=comp)

        try:
            result = self._calculator.calculate_single(sample)
            self._last_result = result
            self.calculation_done.emit(result)
            logger.info("Calculated %s → %s", name, result.rock_type.name)
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", str(e))
            logger.error("Calculation failed: %s", e)

    def _on_export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export results", "minlith_results.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        from src.io.excel import save_results
        if self._last_result:
            try:
                save_results(path, [self._last_result])
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def set_composition(self, comp: OxideComposition, name: str = "") -> None:
        self._oxide_table.set_composition(comp)
        if name:
            self._name_edit.setText(name)
        self._update_sum()

    def get_composition(self) -> OxideComposition:
        return self._oxide_table.get_composition()

    def get_name(self) -> str:
        return self._name_edit.text().strip() or "Sample"
