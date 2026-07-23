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
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 8px;
                padding: 20px;
                color: #888;
                font-size: 13px;
            }
        """)
        layout.addWidget(self._label)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._label.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4a9eff;
                    border-radius: 8px;
                    padding: 20px;
                    color: #4a9eff;
                    font-size: 13px;
                }
            """)

    def dragLeaveEvent(self, event) -> None:
        self._label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 8px;
                padding: 20px;
                color: #888;
                font-size: 13px;
            }
        """)

    def dropEvent(self, event) -> None:
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith((".xlsx", ".csv")):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)
        self._label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 8px;
                padding: 20px;
                color: #888;
                font-size: 13px;
            }
        """)
