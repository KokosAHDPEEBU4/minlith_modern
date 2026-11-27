"""Logs page — view application log output."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.gui.widgets.log_widget import LogWidget
from src.utils.logger import get_gui_handler


class LogsPage(QWidget):
    """Page for viewing application logs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._log_widget = LogWidget()
        layout.addWidget(self._log_widget)

        # Attach to GUI handler
        handler = get_gui_handler()
        if handler:
            handler.set_callback(self._log_widget.append)

    def refresh_from_handler(self) -> None:
        """Reload all buffered records from the handler (idempotent)."""
        handler = get_gui_handler()
        if handler:
            self._log_widget.clear()
            for record in handler.get_records():
                self._log_widget.append(record)
