"""Oxide input panel — left side of the main window."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.models import OxideComposition

# (display name, field name, default value)
OXIDE_FIELDS: list[tuple[str, str, float]] = [
    ("SiO\u2082", "sio2", 52.5),
    ("TiO\u2082", "tio2", 0.0),
    ("Al\u2082O\u2083", "al2o3", 23.41),
    ("Fe\u2082O\u2083", "fe2o3", 1.71),
    ("FeO", "feo", 8.06),
    ("MgO", "mgo", 2.35),
    ("CaO", "cao", 0.28),
    ("Na\u2082O", "na2o", 0.94),
    ("K\u2082O", "k2o", 3.45),
    ("P\u2085O\u2085", "p2o5", 0.31),
    ("MnO", "mno", 0.16),
    ("C", "c", 0.44),
    ("SO\u2083", "so3", 0.0),
    ("F", "f", 0.0),
    ("Cl", "cl", 0.0),
    ("S", "s", 0.0),
    ("CO\u2082", "co2", 0.0),
    ("SO", "so", 0.0),
]


class InputPanel(QWidget):
    """Widget with editable oxide composition fields."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._editors: dict[str, QLineEdit] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        form = QFormLayout(container)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for display, field, default in OXIDE_FIELDS:
            edit = QLineEdit()
            edit.setPlaceholderText(f"{default}" if default else "0")
            edit.setText(str(default) if default else "")
            edit.setFixedWidth(120)
            self._editors[field] = edit
            form.addRow(display, edit)

        # Sample name
        self._name_edit = QLineEdit("Sample")
        form.insertRow(0, "Name:", self._name_edit)

    def get_composition(self) -> Optional[OxideComposition]:
        """Read composition from editors. Returns None if SiO2 is empty."""
        values: dict[str, float] = {}
        for field, editor in self._editors.items():
            text = editor.text().strip()
            if not text:
                values[field] = 0.0
            else:
                try:
                    values[field] = float(text.replace(",", "."))
                except ValueError:
                    values[field] = 0.0

        if values.get("sio2", 0) == 0:
            return None

        return OxideComposition(**values)

    def get_name(self) -> str:
        return self._name_edit.text().strip() or "Sample"

    def set_composition(self, comp: OxideComposition) -> None:
        """Fill editors from an OxideComposition."""
        for field, editor in self._editors.items():
            val = getattr(comp, field, 0.0)
            editor.setText(str(val) if val else "")
