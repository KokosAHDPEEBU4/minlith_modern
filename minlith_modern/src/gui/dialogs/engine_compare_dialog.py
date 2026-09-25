"""Диалог «Сравнение движков»: excel_parity vs excel_exact бок о бок."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.engine_compare import compare_engines, max_abs_delta, to_csv

if TYPE_CHECKING:
    from src.core.models import CalculationResult

# Поля OxideComposition -> имена оксидов в Excel (как в Calculator).
_OXIDE_EXCEL_KEYS = {
    "sio2": "SiO2", "tio2": "TiO2", "al2o3": "Al2O3", "fe2o3": "Fe2O3",
    "feo": "FeO", "mgo": "MgO", "cao": "CaO", "na2o": "Na2O", "k2o": "K2O",
    "p2o5": "P2O5", "mno": "MnO", "c": "C", "so3": "SO3", "f": "F",
    "cl": "Cl", "s": "S", "co2": "CO2", "so": "SO",
}


def _oxide_dict(result: CalculationResult) -> dict[str, float]:
    composition = result.input_composition
    return {excel: float(getattr(composition, attr))
            for attr, excel in _OXIDE_EXCEL_KEYS.items()}


class EngineCompareDialog(QDialog):
    """Показывает по-минеральные расхождения двух Excel-движков."""

    def __init__(self, results: list, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сравнение движков: excel_parity vs excel_exact")
        self.setMinimumSize(620, 480)
        self._results = list(results)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Образец:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(220)
        for result in self._results:
            self._combo.addItem(getattr(result, "sample_name", "?"))
        top.addWidget(self._combo)

        self._btn = QPushButton("Сравнить")
        self._btn.clicked.connect(self._on_compare)
        top.addWidget(self._btn)
        top.addStretch()
        layout.addLayout(top)

        self._summary = QLabel("Выберите образец и нажмите «Сравнить».")
        self._summary.setStyleSheet("color: #888;")
        layout.addWidget(self._summary)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Минерал", "excel_parity (ф.е.)", "excel_exact (ф.е.)", "Δ"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vheader = self._table.verticalHeader()
        if vheader is not None:
            vheader.setVisible(False)
        header = self._table.horizontalHeader()
        if header is not None:
            for c in range(4):
                header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, stretch=1)

        # Диаграмма |Δ| по минералам — наглядное «бок о бок».
        self._fig = Figure(figsize=(6, 2.4), tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setMinimumHeight(180)
        layout.addWidget(self._canvas)

        btn_row = QHBoxLayout()
        self._btn_report = QPushButton("Экспорт отчёта (CSV, все образцы)")
        self._btn_report.clicked.connect(self._on_export_report)
        btn_row.addWidget(self._btn_report)
        btn_row.addStretch()
        self._btn_copy = QPushButton("Копировать")
        self._btn_copy.setEnabled(False)
        self._btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(self._btn_copy)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_compare(self) -> None:
        index = self._combo.currentIndex()
        if index < 0 or index >= len(self._results):
            return
        result = self._results[index]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            rows = compare_engines(_oxide_dict(result))
        except Exception as exc:  # noqa: BLE001 - показать пользователю
            self._summary.setText(f"Ошибка расчёта: {exc}")
            self._table.setRowCount(0)
            return
        finally:
            QApplication.restoreOverrideCursor()

        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(row.name))
            for col, value in ((1, row.parity), (2, row.exact), (3, row.delta)):
                item = QTableWidgetItem(f"{value:.4f}")
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(i, col, item)
        worst, worst_name = max_abs_delta(rows)
        self._summary.setText(
            f"Максимальное |Δ| = {worst:.4f} ф.е. ({worst_name})  "
            f"[{getattr(result, 'sample_name', '')}]")
        self._btn_copy.setEnabled(True)
        self._rows = rows
        self._draw_chart(rows, getattr(result, "sample_name", ""))

    def _draw_chart(self, rows: list, sample: str) -> None:
        """Столбики |Δ| по минералам (ф.е.)."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)
        deltas = [abs(r.delta) for r in rows]
        ax.bar(range(len(rows)), deltas, color="#89b4fa")
        ax.set_xticks(range(len(rows)))
        ax.set_xticklabels([r.name for r in rows], rotation=60,
                           ha="right", fontsize=7)
        ax.set_ylabel("|Δ|, ф.е.", fontsize=8)
        ax.set_title(f"Различия движков: {sample}", fontsize=9)
        try:
            self._canvas.draw_idle()
        except Exception:  # noqa: BLE001 - отрисовка не критична
            pass

    def _on_export_report(self) -> None:
        """Пакетный отчёт: сравнение движков по всем образцам → CSV."""
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт отчёта сравнения движков",
            "engine_compare.csv", "CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        compositions = {
            getattr(r, "sample_name", f"sample{i}"): _oxide_dict(r)
            for i, r in enumerate(self._results)
        }
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            text = to_csv(compositions)
        except Exception as exc:  # noqa: BLE001 - показать пользователю
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))
            return
        QMessageBox.information(self, "Готово", f"Отчёт сохранён:\n{path}")

    def _on_copy(self) -> None:
        lines = ["Минерал\tparity\texact\tΔ"]
        for row in getattr(self, "_rows", []):
            lines.append(f"{row.name}\t{row.parity:.4f}\t{row.exact:.4f}\t{row.delta:.4f}")
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText("\n".join(lines))
