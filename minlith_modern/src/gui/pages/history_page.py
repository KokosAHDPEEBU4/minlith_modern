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
    QFileDialog,
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
        header.addWidget(QLabel("История"))
        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск образцов...")
        self._search.setFixedWidth(200)
        self._search.textChanged.connect(self._on_search)
        header.addWidget(self._search)

        self._btn_refresh = QPushButton("Обновить")
        self._btn_refresh.clicked.connect(self._load_data)
        header.addWidget(self._btn_refresh)

        self._btn_delete = QPushButton("Удалить выбранное")
        self._btn_delete.clicked.connect(self._on_delete)
        header.addWidget(self._btn_delete)

        self._btn_export = QPushButton("Экспорт CSV")
        self._btn_export.clicked.connect(self._on_export)
        header.addWidget(self._btn_export)

        layout.addLayout(header)

        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
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
            self._results = self._repo.get_recent_results(limit=500)
            self._populate_table(self._results)
        except Exception as e:
            logger.warning("Failed to load history: %s", e)
            self._results = []
            self._populate_table([])

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
        self._count_label.setText(f"{len(data)} записей")

    def _on_search(self, text: str) -> None:
        if not text:
            self._populate_table(self._results)
            return
        filtered = [r for r in self._results if text.lower() in r["sample"].lower()]
        self._populate_table(filtered)

    def _on_delete(self) -> None:
        rows = sorted(set(idx.row() for idx in self._table.selectedIndexes()), reverse=True)
        if not rows:
            return
        reply = QMessageBox.question(
            self, "Удаление", f"Удалить {len(rows)} записей?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for row in rows:
                if row < len(self._results):
                    try:
                        self._repo.delete_sample(self._results[row]["sample"])
                    except Exception as e:
                        logger.warning("Delete failed: %s", e)
            self._load_data()

    def _on_export(self) -> None:
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export History", "history.csv", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Sample", "Type", "F", "A", "Ab%", "Q%", "Date"])
            for r in self._results:
                minerals = r.get("minerals", {})
                writer.writerow([
                    r["sample"], r.get("rock_type", ""),
                    f"{r.get('F', 0):.4f}", f"{r.get('A', 0):.4f}",
                    f"{minerals.get('ab', 0):.2f}", f"{minerals.get('q', 0):.2f}",
                    r.get("created_at", "")[:10],
                ])
        QMessageBox.information(self, "Экспорт", f"Экспортировано {len(self._results)} записей")

    def refresh(self) -> None:
        self._load_data()
