"""Страница диаграмм — выбор и отображение диаграмм."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.charts import BUILTIN_CHARTS, ChartData, ChartPlugin

logger = logging.getLogger(__name__)


class ChartsPage(QWidget):
    """Страница просмотра и экспорта диаграмм."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Диаграммы"))
        header.addStretch()

        self._chart_combo = QComboBox()
        for chart in BUILTIN_CHARTS:
            self._chart_combo.addItem(chart.get_name())
        self._chart_combo.currentIndexChanged.connect(self._on_chart_changed)
        header.addWidget(self._chart_combo)

        self._btn_render = QPushButton("Построить")
        self._btn_render.clicked.connect(self._on_render)
        header.addWidget(self._btn_render)

        self._btn_export = QPushButton("Экспорт PNG")
        self._btn_export.clicked.connect(self._on_export)
        header.addWidget(self._btn_export)
        layout.addLayout(header)

        self._desc_label = QLabel()
        self._desc_label.setStyleSheet("color: #a6adc8; padding: 4px;")
        layout.addWidget(self._desc_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._chart_label = QLabel("Выберите диаграмму и нажмите «Построить»")
        self._chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self._chart_label)
        layout.addWidget(scroll)

        self._current_fig = None

    def set_data(self, data: ChartData) -> None:
        self._data = data

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

    def _on_chart_changed(self, idx: int) -> None:
        if 0 <= idx < len(BUILTIN_CHARTS):
            chart = BUILTIN_CHARTS[idx]
            self._desc_label.setText(chart.get_description())

    def _on_render(self) -> None:
        if self._data is None:
            QMessageBox.information(self, "Диаграммы", "Данные не загружены. Сначала выполните расчёт.")
            return

        idx = self._chart_combo.currentIndex()
        if idx < 0 or idx >= len(BUILTIN_CHARTS):
            return

        chart = BUILTIN_CHARTS[idx]
        try:
            fig = chart.render(self._data)
            import io
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            import matplotlib.pyplot as plt
            plt.close(fig)
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            scaled = pixmap.scaled(
                self._chart_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._chart_label.setPixmap(scaled)
            self._current_fig = chart
        except Exception as e:
            QMessageBox.critical(self, "Ошибка диаграммы", str(e))
            logger.error("Ошибка построения диаграммы: %s", e)

    def _on_export(self) -> None:
        if self._data is None:
            return
        idx = self._chart_combo.currentIndex()
        if idx < 0 or idx >= len(BUILTIN_CHARTS):
            return

        chart = BUILTIN_CHARTS[idx]
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы", f"{chart.get_name().lower().replace(' ', '_')}.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )
        if not path:
            return
        try:
            chart.export(self._data, path)
            self._chart_label.setText(f"Экспортировано: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
