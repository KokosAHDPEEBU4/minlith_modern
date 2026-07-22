"""Results table — right side of the main window."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import CalculationResult, MineralComposition

# Minerals to display, in order (matches Excel row 286)
DISPLAY_MINERALS: list[tuple[str, str, str]] = [
    ("Ab", "ab", "Albite"),
    ("An", "an", "Anorthite"),
    ("Or", "or_", "Orthoclase"),
    ("Q", "q", "Quartz"),
    ("Ill", "ill", "Illite"),
    ("Chl", "chl", "Chlorite"),
    ("Kn", "kn", "Kaolinite"),
    ("Mm", "mm", "Montmorillonite"),
    ("Gb", "gb", "Gibbsite"),
    ("Ap", "ap", "Apatite"),
    ("Cc", "cc", "Calcite"),
    ("Dl", "dl", "Dolomite"),
    ("Ank", "ank", "Ankerite"),
    ("Rch", "rch", "Rhodochrosite"),
    ("Sd", "sd", "Siderite"),
    ("Srp", "srp", "Serpentine"),
    ("Mst", "mst", "Magnesite"),
    ("Ht", "ht", "Hematite"),
    ("Prl", "prl", "Pyrolusite"),
    ("Pr", "pr", "Pyrite"),
    ("Hl", "hl", "Halite"),
    ("Fl", "fl", "Fluorite"),
]


class ResultsTable(QWidget):
    """Table showing calculation results."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._header = QLabel("Results")
        self._header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px; color: #e0e0e0; background: transparent;")
        layout.addWidget(self._header)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Set column headers
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Mineral", "FU", "wt%", "Full name"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    def set_result(self, result: CalculationResult) -> None:
        """Populate table from a CalculationResult."""
        minerals = result.minerals_weight
        fu = result.minerals_formula

        self._header.setText(
            f"{result.sample_name}  —  {result.rock_type.name}  "
            f"(F={result.coefficients.F:.3f}, A={result.coefficients.A:.3f})"
        )

        rows = []
        for display, field, full_name in DISPLAY_MINERALS:
            wt = getattr(minerals, field, 0.0)
            fu_val = getattr(fu, field, 0.0)
            rows.append((display, fu_val, wt, full_name))

        self._table.setRowCount(len(rows))
        for i, (name, fu_val, wt_val, full_name) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(name))

            fu_item = QTableWidgetItem(f"{fu_val:.2f}")
            fu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 1, fu_item)

            wt_item = QTableWidgetItem(f"{wt_val:.2f}")
            wt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if wt_val < 0:
                wt_item.setForeground(QColor(200, 0, 0))
            self._table.setItem(i, 2, wt_item)

            self._table.setItem(i, 3, QTableWidgetItem(full_name))

        # Add defect section
        defect_start = len(rows)
        self._table.setRowCount(defect_start + len(result.defect))
        for i, (oxide, val) in enumerate(result.defect.items()):
            row = defect_start + i
            label = QTableWidgetItem(f"\u0394 {oxide}")
            self._table.setItem(row, 0, label)
            d_item = QTableWidgetItem(f"{val:.2f}")
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if val < 0:
                d_item.setForeground(QColor(200, 0, 0))
            self._table.setItem(row, 1, d_item)

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._header.setText("Results")
