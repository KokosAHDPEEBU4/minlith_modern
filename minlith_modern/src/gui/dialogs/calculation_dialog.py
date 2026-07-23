"""Calculation dialog — progress bar for batch calculations with elapsed time."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from src.core.calculator import Calculator
from src.core.models import Sample
from src.workers.calculation_worker import CalculationWorker


class CalculationDialog(QDialog):
    """Dialog showing progress of a batch calculation."""

    def __init__(self, calculator: Calculator, samples: list[Sample], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Расчёт...")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self._label = QLabel("Подготовка...")
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setRange(0, len(samples))
        layout.addWidget(self._progress)

        info_layout = QHBoxLayout()
        self._elapsed_label = QLabel("Время: 0с")
        self._saved_label = QLabel("Рассчитано: 0")
        info_layout.addWidget(self._elapsed_label)
        info_layout.addStretch()
        info_layout.addWidget(self._saved_label)
        layout.addLayout(info_layout)

        self._btn_cancel = QPushButton("Отмена")
        self._btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self._btn_cancel)

        self._start_time = time.time()
        self._saved_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)
        self._timer.start(1000)

        self._worker = CalculationWorker(calculator, samples, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self.results = []
        self._worker.start()

    def _update_elapsed(self) -> None:
        elapsed = int(time.time() - self._start_time)
        self._elapsed_label.setText(f"Время: {elapsed}с")

    def _on_progress(self, current: int, total: int, name: str) -> None:
        self._progress.setValue(current)
        self._label.setText(f"Расчёт {name} ({current}/{total})")
        self._saved_count = current
        self._saved_label.setText(f"Рассчитано: {current}/{total}")

    def _on_finished(self, results: list) -> None:
        self._timer.stop()
        elapsed = int(time.time() - self._start_time)
        self.results = results
        self._label.setText(f"Готово — {len(results)} образцов за {elapsed}с")
        self._saved_label.setText(f"Итого: {len(results)}")
        self._btn_cancel.setText("Закрыть")
        self._btn_cancel.clicked.disconnect()
        self._btn_cancel.clicked.connect(self.accept)

    def _on_error(self, msg: str) -> None:
        self._timer.stop()
        self._label.setText(f"Ошибка: {msg}")
        self._btn_cancel.setText("Закрыть")
        self._btn_cancel.clicked.disconnect()
        self._btn_cancel.clicked.connect(self.reject)

    def _on_cancel(self) -> None:
        self._worker.cancel()
        self._timer.stop()
        if self.results:
            self.accept()
        else:
            self.reject()
