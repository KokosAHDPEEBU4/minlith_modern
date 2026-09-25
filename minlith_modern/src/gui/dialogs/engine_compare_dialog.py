"""Диалог «Сравнение движков»: excel_parity vs excel_exact бок о бок."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.engine_compare import compare_engines, max_abs_delta

# Поля OxideComposition -> имена оксидов в Excel (как в Calculator).
_OXIDE_EXCEL_KEYS = {
    "sio2": "SiO2", "tio2": "TiO2", "al2o3": "Al2O3", "fe2o3": "Fe2O3",
    "feo": "FeO", "mgo": "MgO", "cao": "CaO", "na2o": "Na2O", "k2o": "K2O",
    "p2o5": "P2O5", "mno": "MnO", "c": "C", "so3": "SO3", "f": "F",
    "cl": "Cl", "s": "S", "co2": "CO2", "so": "SO",
}


def _oxide_dict(result) -> dict[str, float]:
    composition = result.input_composition
    return {excel: float(getattr(composition, attr))
            for attr, excel in _OXIDE_EXCEL_KEYS.items()}


class EngineCompareDialog(QDialog):
    """Показывает по-минеральные расхождения двух Excel-движков."""

    def __init__(self, results, parent=None) -> None:
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
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        for c in range(4):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
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

    def _on_copy(self) -> None:
        lines = ["Минерал\tparity\texact\tΔ"]
        for row in getattr(self, "_rows", []):
            lines.append(f"{row.name}\t{row.parity:.4f}\t{row.exact:.4f}\t{row.delta:.4f}")
        QApplication.clipboard().setText("\n".join(lines))
