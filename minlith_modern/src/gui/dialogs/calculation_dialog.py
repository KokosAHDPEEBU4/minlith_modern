"""Calculation dialog — progress bar for batch calculations."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.core.calculator import Calculator
from src.core.models import Sample
from src.workers.calculation_worker import CalculationWorker


class CalculationDialog(QDialog):
    """Dialog showing progress of a batch calculation."""

    def __init__(self, calculator: Calculator, samples: list[Sample], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Calculating...")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self._label = QLabel("Preparing...")
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setRange(0, len(samples))
        layout.addWidget(self._progress)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self._btn_cancel)

        self._worker = CalculationWorker(calculator, samples, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self.results = []
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str) -> None:
        self._progress.setValue(current)
        self._label.setText(f"Calculating {name} ({current}/{total})")

    def _on_finished(self, results: list) -> None:
        self.results = results
        self._label.setText(f"Done — {len(results)} sample(s) calculated")
        self._btn_cancel.setText("Close")
        self._btn_cancel.clicked.disconnect()
        self._btn_cancel.clicked.connect(self.accept)

    def _on_error(self, msg: str) -> None:
        self._label.setText(f"Error: {msg}")
        self._btn_cancel.setText("Close")
        self._btn_cancel.clicked.disconnect()
        self._btn_cancel.clicked.connect(self.reject)

    def _on_cancel(self) -> None:
        self._worker.cancel()
        self.reject()
