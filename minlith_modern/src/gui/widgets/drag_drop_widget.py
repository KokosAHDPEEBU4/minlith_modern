"""Drag-and-drop file widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DragDropWidget(QWidget):
    """Widget that accepts file drops (xlsx, csv)."""

    files_dropped = pyqtSignal(list)  # list of file paths

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("Перетащите файлы .xlsx или .csv сюда\nили используйте кнопку Импорт")
        self._label.setObjectName("dropHint")
        self._label.setProperty("dragging", False)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

    def _set_dragging(self, active: bool) -> None:
        self._label.setProperty("dragging", active)
        style = self._label.style()
        if style is not None:
            style.unpolish(self._label)
            style.polish(self._label)
        self._label.update()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_dragging(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_dragging(False)

    def dropEvent(self, event) -> None:
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith((".xlsx", ".csv")):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)
        self._set_dragging(False)
