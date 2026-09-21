"""Calculation dialog — progress bar for batch calculations with elapsed time."""

from __future__ import annotations

import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.core.calculator import Calculator
from src.core.models import LEGACY_ENGINE_ALIASES, Sample
from src.workers.calculation_worker import CalculationWorker

ENGINE_DESCRIPTIONS = {
    "excel_parity": "Excel (корректные округления) — алгоритм Excel без накопления ROUND",
    "excel_exact": "Excel 1:1 — полная копия книги MINLITH с пошаговыми ROUND",
    "geological_theory": "Геологическая теория — самостоятельный подбор по теории",
    "python_rework": "Python-переработка — пользовательская реализация на Python",
}


class CalculationDialog(QDialog):
    """Dialog — выбор образцов и метода, затем прогресс расчёта."""

    def __init__(self, calculator: Calculator, samples: list[Sample], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Расчёт...")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._samples = samples
        self._calculator = calculator

        layout = QVBoxLayout(self)

        self._label = QLabel("Подготовка...")
        layout.addWidget(self._label)

        # ── Sample selection (choose WHAT to calculate) ──
        layout.addWidget(QLabel("Образцы для расчёта:"))
        self._samples_list = QListWidget()
        self._samples_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
            if hasattr(QListWidget.SelectionMode, "MultiSelection")
            else QListWidget.SelectionMode.ExtendedSelection
        )
        for s in samples:
            self._samples_list.addItem(s.name)
        if samples:
            self._samples_list.item(0).setSelected(True)
        layout.addWidget(self._samples_list)

        # ── Engine selection (choose WITH WHAT to calculate) ──
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Движок расчёта:"))
        self._engine_combo = QComboBox()
        for code, desc in ENGINE_DESCRIPTIONS.items():
            self._engine_combo.addItem(desc, code)
        current = calculator.config.calculation_engine if hasattr(
            calculator.config, "calculation_engine") else "excel_parity"
        current = LEGACY_ENGINE_ALIASES.get(current, current)
        idx = self._engine_combo.findData(current)
        if idx >= 0:
            self._engine_combo.setCurrentIndex(idx)
        engine_row.addWidget(self._engine_combo)
        layout.addLayout(engine_row)

        self._engine_hint = QLabel("")
        self._engine_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._engine_hint)

        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        self._on_engine_changed(self._engine_combo.currentIndex())

        # ── Progress area ──
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        info_layout = QHBoxLayout()
        self._elapsed_label = QLabel("Время: 0с")
        self._saved_label = QLabel("Рассчитано: 0")
        info_layout.addWidget(self._elapsed_label)
        info_layout.addStretch()
        info_layout.addWidget(self._saved_label)
        layout.addLayout(info_layout)

        btn_row = QHBoxLayout()
        self._btn_cancel = QPushButton("Отмена")
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)

        btn_row.addStretch()

        self._btn_start = QPushButton("  Рассчитать  ")
        self._btn_start.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)
        layout.addLayout(btn_row)

        self._start_time = None
        self._saved_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)
        self._worker = None
        self.results = []

    def _on_engine_changed(self, index: int) -> None:
        code = self._engine_combo.itemData(index)
        self._engine_hint.setText(ENGINE_DESCRIPTIONS.get(code, ""))

    def _selected_samples(self, all_samples: list[Sample]) -> list[Sample]:
        selected = [
            self._samples_list.item(i)
            for i in range(self._samples_list.count())
            if self._samples_list.item(i).isSelected()
        ]
        if not selected:
            return []
        rows = {self._samples_list.row(item) for item in selected}
        return [s for i, s in enumerate(all_samples) if i in rows]

    def _configure_calculator(self, calculator: Calculator, engine: str) -> Calculator:
        """Return a Calculator configured for the selected calculation engine."""
        from src.core.models import CalculationConfig

        cfg = calculator.config
        new_config = CalculationConfig(
            molar_mass_source=cfg.molar_mass_source,
            custom_molar_masses=cfg.custom_molar_masses,
            sum_tolerance=cfg.sum_tolerance,
            warn_negative=cfg.warn_negative,
            auto_correct_sum=cfg.auto_correct_sum,
            decimal_places=cfg.decimal_places,
            include_formula_units=cfg.include_formula_units,
            include_defect=cfg.include_defect,
            include_parameters=cfg.include_parameters,
            timeout_seconds=cfg.timeout_seconds,
            batch_size=cfg.batch_size,
            calculation_engine=engine,
        )
        return Calculator(config=new_config)

    def _on_start(self) -> None:
        samples = self._selected_samples(self._samples)
        if not samples:
            # nothing selected → treat all as selected implicitly? No — fall back to all checked
            samples = self._samples

        engine = self._engine_combo.currentData() or "excel_parity"
        calculator = self._configure_calculator(self._calculator, engine)

        self._progress.setRange(0, len(samples))
        self._progress.setVisible(True)
        self._samples_list.setEnabled(False)
        self._engine_combo.setEnabled(False)
        self._btn_start.setEnabled(False)

        self._start_time = time.time()
        self._worker = CalculationWorker(calculator, samples, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._timer.start(1000)
        self._label.setText("Расчёт...")
        self._worker.start()

    def _update_elapsed(self) -> None:
        if self._start_time is not None:
            elapsed = int(time.time() - self._start_time)
            self._elapsed_label.setText(f"Время: {elapsed}с")

    def _on_progress(self, current: int, total: int, name: str) -> None:
        self._progress.setValue(current)
        self._label.setText(f"Расчёт {name} ({current}/{total})")
        self._saved_count = current
        self._saved_label.setText(f"Рассчитано: {current}/{total}")

    def _on_finished(self, results: list) -> None:
        self._timer.stop()
        if self._start_time is not None:
            elapsed = int(time.time() - self._start_time)
        else:
            elapsed = 0
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
        if self._worker is not None:
            self._worker.cancel()
        self._timer.stop()
        if self.results:
            self.accept()
        else:
            self.reject()
