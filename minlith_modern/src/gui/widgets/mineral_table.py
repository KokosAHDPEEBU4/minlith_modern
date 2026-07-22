"""Mineral table widget — display-only table for mineral results."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import MineralComposition

# (display, field, full_name)
MINERAL_COLUMNS: list[tuple[str, str, str]] = [
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


class MineralTable(QWidget):
    """Read-only table showing mineral formula units and weight percent."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)

        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Mineral", "FU", "wt%", "Full name"])
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

    def set_minerals(self, minerals: MineralComposition, fu: MineralComposition | None = None) -> None:
        self._table.setRowCount(len(MINERAL_COLUMNS))
        for i, (display, field, full_name) in enumerate(MINERAL_COLUMNS):
            wt = getattr(minerals, field, 0.0)
            fu_val = getattr(fu, field, 0.0) if fu else 0.0

            self._table.setItem(i, 0, QTableWidgetItem(display))

            fu_item = QTableWidgetItem(f"{fu_val:.2f}")
            fu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 1, fu_item)

            wt_item = QTableWidgetItem(f"{wt:.2f}")
            wt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if wt < 0:
                wt_item.setForeground(QColor(200, 0, 0))
            self._table.setItem(i, 2, wt_item)

            self._table.setItem(i, 3, QTableWidgetItem(full_name))

    def clear(self) -> None:
        self._table.setRowCount(0)
