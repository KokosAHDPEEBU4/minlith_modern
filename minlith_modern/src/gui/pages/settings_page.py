"""Settings page — configure calculation parameters."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Page for application settings."""

    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)

        header = QLabel("Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # Calculation group
        calc_group = QGroupBox("Calculation")
        calc_form = QFormLayout(calc_group)

        self._molar_mass = QComboBox()
        self._molar_mass.addItems(["iupac", "minlith"])
        self._molar_mass.setCurrentText(config.get("molar_mass_source", "iupac"))
        calc_form.addRow("Molar mass source:", self._molar_mass)

        self._sum_lo = QLineEdit(str(config.get("sum_tolerance", [98, 102])[0]))
        self._sum_lo.setFixedWidth(80)
        self._sum_hi = QLineEdit(str(config.get("sum_tolerance", [98, 102])[1]))
        self._sum_hi.setFixedWidth(80)
        sum_row = QHBoxLayout()
        sum_row.addWidget(self._sum_lo)
        sum_row.addWidget(QLabel("—"))
        sum_row.addWidget(self._sum_hi)
        sum_row.addStretch()
        calc_form.addRow("Sum range (%):", sum_row)

        self._warn_negative = QCheckBox("Warn on negative values")
        self._warn_negative.setChecked(config.get("warn_negative", True))
        calc_form.addRow(self._warn_negative)

        self._auto_correct = QCheckBox("Auto-correct sum to 100%")
        self._auto_correct.setChecked(config.get("auto_correct_sum", False))
        calc_form.addRow(self._auto_correct)

        self._decimal_places = QSpinBox()
        self._decimal_places.setRange(0, 6)
        self._decimal_places.setValue(config.get("decimal_places", 2))
        calc_form.addRow("Decimal places:", self._decimal_places)

        self._timeout = QSpinBox()
        self._timeout.setRange(10, 600)
        self._timeout.setValue(config.get("timeout_seconds", 120))
        self._timeout.setSuffix(" sec")
        calc_form.addRow("Timeout:", self._timeout)

        layout.addWidget(calc_group)

        # UI group
        ui_group = QGroupBox("Interface")
        ui_form = QFormLayout(ui_group)

        self._theme = QComboBox()
        self._theme.addItems(["dark", "light"])
        self._theme.setCurrentText(config.get("theme", "dark"))
        ui_form.addRow("Theme:", self._theme)

        self._language = QComboBox()
        self._language.addItems(["ru", "en"])
        self._language.setCurrentText(config.get("language", "ru"))
        ui_form.addRow("Language:", self._language)

        layout.addWidget(ui_group)

        # Save
        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("Save settings")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _on_save(self) -> None:
        self._config["molar_mass_source"] = self._molar_mass.currentText()
        self._config["sum_tolerance"] = [
            float(self._sum_lo.text()),
            float(self._sum_hi.text()),
        ]
        self._config["warn_negative"] = self._warn_negative.isChecked()
        self._config["auto_correct_sum"] = self._auto_correct.isChecked()
        self._config["decimal_places"] = self._decimal_places.value()
        self._config["timeout_seconds"] = self._timeout.value()
        self._config["theme"] = self._theme.currentText()
        self._config["language"] = self._language.currentText()
        self._config.save()
        logger.info("Settings saved")
