"""Logging setup with optional GUI handler + file rotation."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from collections import deque
from logging import Handler, LogRecord
from pathlib import Path


class GUILogHandler(Handler):
    """Logging handler that stores messages for display in GUI."""

    def __init__(self, max_records: int = 1000) -> None:
        super().__init__()
        self.records: deque[LogRecord] = deque(maxlen=max_records)
        self._callback: callable | None = None

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


_gui_handler: GUILogHandler | None = None


def setup_logging(level: int = logging.INFO, log_dir: Path | str | None = None) -> GUILogHandler:
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

    # File handler with rotation
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "minlith.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(file_handler)

    # GUI handler (buffers messages for the logs page)
    _gui_handler = GUILogHandler()
    _gui_handler.setLevel(logging.DEBUG)
    _gui_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(_gui_handler)

    return _gui_handler


def get_gui_handler() -> GUILogHandler | None:
    return _gui_handler
