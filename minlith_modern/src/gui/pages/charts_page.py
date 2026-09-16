"""Страница диаграмм — вывод нескольких диаграмм сеткой."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.charts import ChartData
from src.gui.widgets.chart_grid import MultiChartView

logger = logging.getLogger(__name__)


class ChartsPage(QWidget):
    """Страница просмотра и экспорта диаграмм (несколько графиков сразу)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Диаграммы")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        self._view = MultiChartView()
        layout.addWidget(self._view, stretch=1)

    def set_data(self, data: Optional[ChartData]) -> None:
        self._data = data
        self._view.set_data(data)

    def build_data_from_results(self, results: list) -> ChartData:
        """Построить ChartData из списка CalculationResult."""
        import numpy as np
        from src.charts import ChartData

        data = ChartData()
        data.sample_names = [r.sample_name for r in results]

        mineral_fields = ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                          "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]
        for field in mineral_fields:
            arr = np.array([getattr(r.minerals_weight, field, 0.0) for r in results])
            data.minerals_wt[field] = arr

        oxide_fields = ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]
        for field in oxide_fields:
            arr = np.array([getattr(r.input_composition, field, 0.0) for r in results])
            data.oxides[field] = arr

        data.rock_types = [int(r.rock_type) for r in results]

        if results and results[0].defect:
            for oxide in results[0].defect:
                arr = np.array([r.defect.get(oxide, 0.0) for r in results])
                data.defect[oxide] = arr

        data.F_values = [r.coefficients.F for r in results]
        data.A_values = [r.coefficients.A for r in results]

        return data