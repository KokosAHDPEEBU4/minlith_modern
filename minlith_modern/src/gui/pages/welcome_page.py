"""Welcome page — landing screen with quick start."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WelcomePage(QWidget):
    """Landing page with project info and quick actions."""

    open_files = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("MINLITH Modern")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Нормативный минералогический расчёт")
        subtitle.setStyleSheet("font-size: 14px; color: #a6adc8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # Quick actions
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_files = QPushButton("Открыть файлы")
        btn_files.setFixedWidth(160)
        btn_files.clicked.connect(self.open_files.emit)
        btn_row.addWidget(btn_files)

        btn_row.addSpacing(20)

        btn_calc = QPushButton("Быстрый расчёт")
        btn_calc.setFixedWidth(160)
        btn_calc.clicked.connect(lambda: self.open_files.emit())
        btn_row.addWidget(btn_calc)

        layout.addLayout(btn_row)

        layout.addSpacing(40)

        # Info
        info = QLabel(
            "Перетащите файлы .xlsx/.csv на вкладку «Файлы» для начала работы.\n"
            "Или введите значения оксидов вручную на вкладке «Ввод»."
        )
        info.setStyleSheet("color: #6c7086; font-size: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        layout.addStretch()
