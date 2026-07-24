"""Output page — multi-chart display with selection."""

from __future__ import annotations

import io
import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.charts import BUILTIN_CHARTS, ChartData

logger = logging.getLogger(__name__)


class _ChartTile(QWidget):
    """A single chart tile: image + title + export button."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._title = QLabel()
        self._title.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        self._image = QLabel()
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image.setMinimumSize(300, 250)
        self._image.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244;")
        layout.addWidget(self._image, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_export = QPushButton("Экспорт PNG")
        self._btn_export.setFixedHeight(28)
        btn_row.addWidget(self._btn_export)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._chart_idx: int = -1
        self._fig = None

    def set_chart(self, idx: int, fig, title: str) -> None:
        self._chart_idx = idx
        self._fig = fig
        self._title.setText(title)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        import matplotlib.pyplot as plt
        plt.close(fig)
        buf.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        scaled = pixmap.scaled(
            self._image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image.setPixmap(scaled)

    def export_png(self, path: str) -> None:
        if self._fig is None:
            return
        chart = BUILTIN_CHARTS[self._chart_idx]
        chart.export(None, path)  # fig already rendered, but we re-export


class OutputPage(QWidget):
    """Page for multi-chart output with selection."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None
        self._tiles: list[_ChartTile] = []
        self._checkboxes: list[QCheckBox] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Header ──
        header = QLabel("Вывод диаграмм")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # ── Top controls ──
        ctrl_row = QHBoxLayout()

        self._btn_select_all = QPushButton("Выбрать все")
        self._btn_select_all.clicked.connect(self._select_all)
        ctrl_row.addWidget(self._btn_select_all)

        self._btn_deselect_all = QPushButton("Снять все")
        self._btn_deselect_all.clicked.connect(self._deselect_all)
        ctrl_row.addWidget(self._btn_deselect_all)

        ctrl_row.addStretch()

        self._btn_render = QPushButton("Построить выбранные")
        self._btn_render.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self._btn_render.clicked.connect(self._on_render)
        ctrl_row.addWidget(self._btn_render)

        self._btn_export_all = QPushButton("Экспорт всех в PNG")
        self._btn_export_all.clicked.connect(self._on_export_all)
        ctrl_row.addWidget(self._btn_export_all)

        layout.addLayout(ctrl_row)

        # ── Main area: checklist (left) + chart grid (right) ──
        splitter_h = QHBoxLayout()

        # Left: checklist
        check_group = QGroupBox("Диаграммы")
        check_layout = QVBoxLayout(check_group)
        check_layout.setContentsMargins(8, 12, 8, 8)

        for i, chart in enumerate(BUILTIN_CHARTS):
            cb = QCheckBox(chart.get_name())
            cb.setToolTip(chart.get_description())
            self._checkboxes.append(cb)
            check_layout.addWidget(cb)

        check_layout.addStretch()

        # Right: scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8)
        scroll.setWidget(self._grid_widget)

        splitter_h.addWidget(check_group, stretch=0)
        splitter_h.addWidget(scroll, stretch=1)

        layout.addLayout(splitter_h, stretch=1)

    def set_data(self, data: Optional[ChartData]) -> None:
        self._data = data

    def _select_all(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(False)

    def _on_render(self) -> None:
        if self._data is None:
            QMessageBox.information(
                self, "Вывод",
                "Данные не загружены. Сначала выполните расчёт.",
            )
            return

        selected = [i for i, cb in enumerate(self._checkboxes) if cb.isChecked()]
        if not selected:
            QMessageBox.information(
                self, "Вывод",
                "Выберите хотя бы одну диаграмму.",
            )
            return

        # Clear previous tiles
        self._clear_grid()
        self._tiles.clear()

        cols = 2
        for pos, chart_idx in enumerate(selected):
            chart = BUILTIN_CHARTS[chart_idx]
            try:
                fig = chart.render(self._data)
                tile = _ChartTile()
                tile.set_chart(chart_idx, fig, chart.get_name())
                tile._btn_export.clicked.connect(lambda checked, t=tile: self._export_tile(t))
                row, col = divmod(pos, cols)
                self._grid_layout.addWidget(tile, row, col)
                self._tiles.append(tile)
            except Exception as e:
                logger.error("Chart '%s' failed: %s", chart.get_name(), e)
                err_label = QLabel(f"Ошибка: {chart.get_name()}\n{e}")
                err_label.setStyleSheet("color: #f38ba8; padding: 8px;")
                row, col = divmod(pos, cols)
                self._grid_layout.addWidget(err_label, row, col)

        logger.info("Rendered %d charts", len(self._tiles))

    def _export_tile(self, tile: _ChartTile) -> None:
        if tile._chart_idx < 0:
            return
        chart = BUILTIN_CHARTS[tile._chart_idx]
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы",
            f"{chart.get_name().lower().replace(' ', '_')}.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )
        if not path:
            return
        try:
            chart.export(self._data, path)
            QMessageBox.information(self, "Экспорт", f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def _on_export_all(self) -> None:
        if not self._tiles:
            QMessageBox.information(self, "Экспорт", "Сначала постройте диаграммы.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Папка для экспорта")
        if not folder:
            return
        from pathlib import Path
        folder_path = Path(folder)
        exported = 0
        for tile in self._tiles:
            if tile._chart_idx < 0:
                continue
            chart = BUILTIN_CHARTS[tile._chart_idx]
            fname = f"{chart.get_name().lower().replace(' ', '_')}.png"
            try:
                chart.export(self._data, str(folder_path / fname))
                exported += 1
            except Exception as e:
                logger.error("Export '%s' failed: %s", chart.get_name(), e)
        QMessageBox.information(
            self, "Экспорт",
            f"Экспортировано {exported} из {len(self._tiles)} диаграмм.",
        )

    def _clear_grid(self) -> None:
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
