"""Logging setup with optional GUI handler."""

from __future__ import annotations

import logging
import sys
from collections import deque
from logging import Handler, LogRecord
from typing import Optional


class GUILogHandler(Handler):
    """Logging handler that stores messages for display in GUI."""

    def __init__(self, max_records: int = 1000) -> None:
        super().__init__()
        self.records: deque[LogRecord] = deque(maxlen=max_records)
        self._callback: Optional[callable] = None

    def set_callback(self, callback: callable) -> None:
        self._callback = callback

    def emit(self, record: LogRecord) -> None:
        self.records.append(record)
        if self._callback:
            self._callback(record)

    def get_records(self, level: int = logging.NOTSET) -> list[LogRecord]:
        if level == logging.NOTSET:
            return list(self.records)
        return [r for r in self.records if r.levelno >= level]


_gui_handler: Optional[GUILogHandler] = None


def setup_logging(level: int = logging.INFO) -> GUILogHandler:
    """Configure application logging. Returns the GUI handler for attachment."""
    global _gui_handler

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(console)

    # GUI handler (buffers messages for the logs page)
    _gui_handler = GUILogHandler()
    _gui_handler.setLevel(logging.DEBUG)
    _gui_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(_gui_handler)

    return _gui_handler


def get_gui_handler() -> Optional[GUILogHandler]:
    return _gui_handler
