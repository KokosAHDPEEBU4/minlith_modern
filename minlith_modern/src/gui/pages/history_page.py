"""History page — browse past calculations from database."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.repository import SampleRepository

logger = logging.getLogger(__name__)


class HistoryPage(QWidget):
    """Page for browsing calculation history from the database."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._repo = SampleRepository()
        self._results: list[dict] = []

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("History"))
        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search samples...")
        self._search.setFixedWidth(200)
        self._search.textChanged.connect(self._on_search)
        header.addWidget(self._search)

        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self._load_data)
        header.addWidget(self._btn_refresh)
        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Sample", "Type", "F", "A", "Ab%", "Q%", "Date",
        ])
        h = self._table.horizontalHeader()
        for c in range(7):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

        self._load_data()

    def _load_data(self) -> None:
        try:
            self._results = self._repo.get_recent_results(limit=200)
            self._populate_table(self._results)
        except Exception as e:
            logger.warning("Failed to load history: %s", e)

    def _populate_table(self, data: list[dict]) -> None:
        self._table.setRowCount(len(data))
        for i, r in enumerate(data):
            self._table.setItem(i, 0, QTableWidgetItem(r["sample"]))
            self._table.setItem(i, 1, QTableWidgetItem(str(r.get("rock_type", ""))))
            self._table.setItem(i, 2, QTableWidgetItem(f"{r.get('F', 0):.3f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"{r.get('A', 0):.3f}"))
            minerals = r.get("minerals", {})
            self._table.setItem(i, 4, QTableWidgetItem(f"{minerals.get('ab', 0):.2f}"))
            self._table.setItem(i, 5, QTableWidgetItem(f"{minerals.get('q', 0):.2f}"))
            self._table.setItem(i, 6, QTableWidgetItem(r.get("created_at", "")[:10]))

    def _on_search(self, text: str) -> None:
        if not text:
            self._populate_table(self._results)
            return
        filtered = [r for r in self._results if text.lower() in r["sample"].lower()]
        self._populate_table(filtered)

    def refresh(self) -> None:
        self._load_data()
