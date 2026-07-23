"""Таблица оксидов — редактируемая таблица для состава оксидов."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import OxideComposition

# Valid characters for numeric input
_VALID_CHARS = set("0123456789.,-+eE")

OXIDE_COLUMNS: list[tuple[str, str]] = [
    ("SiO\u2082", "sio2"),
    ("TiO\u2082", "tio2"),
    ("Al\u2082O\u2083", "al2o3"),
    ("Fe\u2082O\u2083", "fe2o3"),
    ("FeO", "feo"),
    ("MgO", "mgo"),
    ("CaO", "cao"),
    ("Na\u2082O", "na2o"),
    ("K\u2082O", "k2o"),
    ("P\u2085O\u2085", "p2o5"),
    ("MnO", "mno"),
    ("C", "c"),
    ("SO\u2083", "so3"),
    ("F", "f"),
    ("Cl", "cl"),
    ("S", "s"),
    ("CO\u2082", "co2"),
    ("SO", "so"),
]


class OxideTable(QWidget):
    """Редактируемая таблица оксидов (один образец)."""

    value_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Оксид", "Значение (%)"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setRowCount(len(OXIDE_COLUMNS))

        for i, (label, field) in enumerate(OXIDE_COLUMNS):
            self._table.setItem(i, 0, QTableWidgetItem(label))
            edit = QTableWidgetItem("0.0")
            edit.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 1, edit)

        self._table.itemChanged.connect(self._on_change)
        layout.addWidget(self._table)

    def _on_change(self, item) -> None:
        if item.column() == 1:
            text = item.text().replace(",", ".")
            # Strip leading/trailing whitespace
            text = text.strip()
            if text and not all(c in _VALID_CHARS for c in text):
                # Revert to previous valid value
                try:
                    float(text)
                except ValueError:
                    item.setText("0.0")
                    return
            self.value_changed.emit()

    def get_composition(self) -> OxideComposition:
        values: dict[str, float] = {}
        for i, (_, field) in enumerate(OXIDE_COLUMNS):
            item = self._table.item(i, 1)
            try:
                values[field] = float(item.text().replace(",", ".")) if item else 0.0
            except ValueError:
                values[field] = 0.0
        return OxideComposition(**values)

    def set_composition(self, comp: OxideComposition) -> None:
        self._table.blockSignals(True)
        for i, (_, field) in enumerate(OXIDE_COLUMNS):
            val = getattr(comp, field, 0.0)
            self._table.item(i, 1).setText(str(round(val, 4)) if val else "0")
        self._table.blockSignals(False)

    def get_sum(self) -> float:
        return self.get_composition().sum()
