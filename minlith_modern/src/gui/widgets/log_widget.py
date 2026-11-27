"""Виджет журнала — вывод логов приложения."""

from __future__ import annotations

import logging
import time

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class LogWidget(QWidget):
    """Виджет для отображения логов приложения."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[logging.LogRecord] = []
        self._filter_level: int = logging.INFO

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._level_label = QLabel("Уровень:")
        toolbar.addWidget(self._level_label)

        self._level_combo = QComboBox()
        self._level_combo.addItems(_LEVELS)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.setToolTip("Минимальный уровень сообщений в журнале")
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        toolbar.addWidget(self._level_combo)

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
        self._records.append(record)
        if len(self._records) > 5000:
            del self._records[:1000]
        if record.levelno >= self._filter_level:
            self._insert(record)

    def _format_record(self, record: logging.LogRecord) -> str:
        stamp = getattr(record, "asctime", None)
        if not stamp:
            stamp = time.strftime("%H:%M:%S", time.localtime(record.created))
        level_name = logging.getLevelName(record.levelno)
        return f"[{stamp}] [{level_name}] {record.name}: {record.getMessage()}\n"

    def _insert(self, record: logging.LogRecord) -> None:
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text.setTextCursor(cursor)
        cursor.insertText(self._format_record(record))
        scrollbar = self._text.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def set_filter_level(self, level: int) -> None:
        self._filter_level = level
        self._rerender()

    def _on_level_changed(self, text: str) -> None:
        self.set_filter_level(logging.getLevelName(text))

    def _rerender(self) -> None:
        self._text.clear()
        for record in self._records:
            if record.levelno >= self._filter_level:
                self._insert(record)

    def clear(self) -> None:
        self._records.clear()
        self._text.clear()

    def _clear(self) -> None:
        self.clear()
