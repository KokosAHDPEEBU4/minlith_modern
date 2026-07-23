"""Виджет журнала — вывод логов приложения."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_LEVEL_COLORS = {
    logging.DEBUG: QColor(150, 150, 150),
    logging.INFO: QColor(200, 200, 200),
    logging.WARNING: QColor(255, 200, 50),
    logging.ERROR: QColor(255, 100, 100),
    logging.CRITICAL: QColor(255, 50, 50),
}


class LogWidget(QWidget):
    """Виджет для отображения логов приложения."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._level_label = QLabel("Уровень:")
        toolbar.addWidget(self._level_label)

        self._filter_level = logging.INFO
        toolbar.addStretch()

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.clicked.connect(self._clear)
        toolbar.addWidget(self._btn_clear)

        layout.addLayout(toolbar)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(5000)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

    def append(self, record: logging.LogRecord) -> None:
        if record.levelno < self._filter_level:
            return
        color = _LEVEL_COLORS.get(record.levelno, QColor(200, 200, 200))
        msg = record.getMessage()
        level_name = logging.getLevelName(record.levelno)
        line = f"[{record.asctime}] [{level_name}] {record.name}: {msg}\n"

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text.setTextCursor(cursor)

        self._text.setReadOnly(False)
        cursor.insertText(line)
        self._text.setReadOnly(True)

        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().maximum())

    def set_filter_level(self, level: int) -> None:
        self._filter_level = level

    def _clear(self) -> None:
        self._text.clear()
