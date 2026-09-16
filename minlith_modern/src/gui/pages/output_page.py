"""Output page — multi-chart display with selection."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.charts import ChartData
from src.gui.widgets.chart_grid import MultiChartView

logger = logging.getLogger(__name__)


class OutputPage(QWidget):
    """Page for multi-chart output — shared grid with the charts page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Вывод диаграмм")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        self._view = MultiChartView()
        layout.addWidget(self._view, stretch=1)

    def set_data(self, data: Optional[ChartData]) -> None:
        self._data = data
        self._view.set_data(data)