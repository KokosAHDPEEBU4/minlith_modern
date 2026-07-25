"""Страница настроек — параметры расчёта и интерфейса."""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
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
    """Страница настроек приложения."""

    settings_changed = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)

        header = QLabel("Настройки")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # Расчёт
        calc_group = QGroupBox("Расчёт")
        calc_form = QFormLayout(calc_group)

        self._molar_mass = QComboBox()
        self._molar_mass.addItems(["iupac", "minlith"])
        self._molar_mass.setCurrentText(config.get("molar_mass_source", "iupac"))
        calc_form.addRow("Источник молярных масс:", self._molar_mass)

        self._sum_lo = QLineEdit(str(config.get("sum_tolerance", [98, 102])[0]))
        self._sum_lo.setFixedWidth(80)
        self._sum_hi = QLineEdit(str(config.get("sum_tolerance", [98, 102])[1]))
        self._sum_hi.setFixedWidth(80)
        sum_row = QHBoxLayout()
        sum_row.addWidget(self._sum_lo)
        sum_row.addWidget(QLabel("—"))
        sum_row.addWidget(self._sum_hi)
        sum_row.addStretch()
        calc_form.addRow("Допустимая сумма (%):", sum_row)

        self._warn_negative = QCheckBox("Предупреждать об отрицательных значениях")
        self._warn_negative.setChecked(config.get("warn_negative", True))
        calc_form.addRow(self._warn_negative)

        self._auto_correct = QCheckBox("Автокоррекция суммы до 100%")
        self._auto_correct.setChecked(config.get("auto_correct_sum", False))
        calc_form.addRow(self._auto_correct)

        self._decimal_places = QSpinBox()
        self._decimal_places.setRange(0, 6)
        self._decimal_places.setValue(config.get("decimal_places", 2))
        calc_form.addRow("Знаков после запятой:", self._decimal_places)

        self._timeout = QSpinBox()
        self._timeout.setRange(10, 600)
        self._timeout.setValue(config.get("timeout_seconds", 120))
        self._timeout.setSuffix(" сек")
        calc_form.addRow("Таймаут:", self._timeout)

        self._algorithm_mode = QComboBox()
        self._algorithm_mode.addItems(["stub", "custom"])
        self._algorithm_mode.setCurrentText(config.get("algorithm_mode", "stub"))
        self._algorithm_mode.setToolTip(
            "stub — заглушка (ожидает перенос VBA-макроса)\n"
            "custom — пользовательская реализация алгоритма"
        )
        calc_form.addRow("Режим алгоритма:", self._algorithm_mode)

        layout.addWidget(calc_group)

        # Интерфейс
        ui_group = QGroupBox("Интерфейс")
        ui_form = QFormLayout(ui_group)

        self._theme = QComboBox()
        self._theme.addItems(["dark", "light"])
        self._theme.setCurrentText(config.get("theme", "dark"))
        ui_form.addRow("Тема интерфейса:", self._theme)

        self._chart_theme = QComboBox()
        self._chart_theme.addItems(["dark", "light"])
        self._chart_theme.setCurrentText(config.get("chart_theme", "dark"))
        self._chart_theme.setToolTip("Фон диаграмм: тёмный (Catppuccin) или белый")
        ui_form.addRow("Фон диаграмм:", self._chart_theme)

        self._language = QComboBox()
        self._language.addItems(["ru", "en"])
        self._language.setCurrentText(config.get("language", "ru"))
        ui_form.addRow("Язык:", self._language)

        layout.addWidget(ui_group)

        # Кнопки
        btn_row = QHBoxLayout()
        self._btn_reset = QPushButton("Сбросить настройки")
        self._btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(self._btn_reset)
        btn_row.addStretch()
        self._btn_save = QPushButton("Сохранить настройки")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _on_save(self) -> None:
        self._config["molar_mass_source"] = self._molar_mass.currentText()
        try:
            lo = float(self._sum_lo.text())
            hi = float(self._sum_hi.text())
            self._config["sum_tolerance"] = [lo, hi]
        except ValueError:
            pass
        self._config["warn_negative"] = self._warn_negative.isChecked()
        self._config["auto_correct_sum"] = self._auto_correct.isChecked()
        self._config["decimal_places"] = self._decimal_places.value()
        self._config["timeout_seconds"] = self._timeout.value()
        self._config["algorithm_mode"] = self._algorithm_mode.currentText()
        self._config["theme"] = self._theme.currentText()
        self._config["chart_theme"] = self._chart_theme.currentText()
        self._config["language"] = self._language.currentText()
        self._config.save()

        # Apply chart theme immediately
        from src.charts.engines.matplotlib_engine import set_chart_theme
        set_chart_theme(self._chart_theme.currentText())

        self.settings_changed.emit()
        logger.info("Настройки сохранены")

    def _on_reset(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Сброс настроек",
            "Вернуть все настройки по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._config.reset()
        self._reload_widgets()
        self.settings_changed.emit()
        logger.info("Настройки сброшены до умолчаний")

    def _reload_widgets(self) -> None:
        """Reload widget values from config (after reset)."""
        self._molar_mass.setCurrentText(self._config.get("molar_mass_source", "iupac"))
        tol = self._config.get("sum_tolerance", [98.0, 102.0])
        self._sum_lo.setText(str(tol[0]))
        self._sum_hi.setText(str(tol[1]))
        self._warn_negative.setChecked(self._config.get("warn_negative", True))
        self._auto_correct.setChecked(self._config.get("auto_correct_sum", False))
        self._decimal_places.setValue(self._config.get("decimal_places", 2))
        self._timeout.setValue(self._config.get("timeout_seconds", 120))
        self._algorithm_mode.setCurrentText(self._config.get("algorithm_mode", "stub"))
        self._theme.setCurrentText(self._config.get("theme", "dark"))
        self._chart_theme.setCurrentText(self._config.get("chart_theme", "dark"))
        self._language.setCurrentText(self._config.get("language", "ru"))
