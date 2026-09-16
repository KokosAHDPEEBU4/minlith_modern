"""Shared multi-chart grid widget — checklist + tiles, used by chart pages."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.charts import BUILTIN_CHARTS, ChartData
from src.gui.widgets.chart_interactions import (
    InteractionSpec,
    get_spec,
    resolve_type_id,
)

logger = logging.getLogger(__name__)

DEFAULT_COLUMNS = 2


def _noop_scroll_zoom(event) -> None:
    """Заглушка для встроенного scroll-зума matplotlib (отключение)."""
    return None


class _ChartTile(QWidget):
    """A single chart tile: title + interactive canvas + controls.

    The canvas is a live matplotlib QtAgg widget with the standard toolbar
    (box-zoom, pan, home/reset, save) plus explicit zoom in/out buttons.
    """

    ZOOM_STEP = 1.25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._title = QLabel()
        self._title.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px;")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        self._canvas_host = QWidget()
        self._canvas_layout = QVBoxLayout(self._canvas_host)
        self._canvas_layout.setContentsMargins(0, 0, 0, 0)
        self._canvas_layout.setSpacing(0)
        layout.addWidget(self._canvas_host, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_zoom_out = QPushButton("Отдалить")
        self._btn_zoom_out.setFixedHeight(28)
        self._btn_zoom_out.setToolTip("Отдалить (колесо мыши — вниз)")
        self._btn_zoom_out.clicked.connect(lambda: self.zoom(1 / self.ZOOM_STEP))
        btn_row.addWidget(self._btn_zoom_out)

        self._btn_zoom_in = QPushButton("Приблизить")
        self._btn_zoom_in.setFixedHeight(28)
        self._btn_zoom_in.setToolTip("Приблизить (колесо мыши — вверх)")
        self._btn_zoom_in.clicked.connect(lambda: self.zoom(self.ZOOM_STEP))
        btn_row.addWidget(self._btn_zoom_in)

        self._btn_reset = QPushButton("По умолчанию")
        self._btn_reset.setFixedHeight(28)
        self._btn_reset.setToolTip("Сбросить масштаб этой диаграммы к исходному")
        self._btn_reset.clicked.connect(self.reset_view)
        btn_row.addWidget(self._btn_reset)

        btn_row.addStretch()

        self._btn_export = QPushButton("Экспорт")
        self._btn_export.setFixedHeight(28)
        btn_row.addWidget(self._btn_export)
        layout.addLayout(btn_row)

        self._chart_idx: int = -1
        self._fig = None
        self._canvas = None
        self._toolbar = None
        self._spec: InteractionSpec | None = None
        self._cids: dict[str, int] = {}

    @property
    def chart_idx(self) -> int:
        return self._chart_idx

    @property
    def figure(self):
        return self._fig

    @property
    def canvas(self):
        return self._canvas

    @property
    def toolbar(self):
        return self._toolbar

    @property
    def spec(self) -> InteractionSpec | None:
        return self._spec

    def set_figure(
        self,
        idx: int,
        fig,
        title: str,
        chart_type: str | None = None,
    ) -> None:
        self.disconnect_events()
        self._chart_idx = idx
        self._title.setText(title)
        self._fig = fig

        self._spec = get_spec(chart_type) if chart_type else None

        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumSize(320, 260)
        canvas.setStyleSheet("border: none;")
        self._cids["scroll_event"] = canvas.mpl_connect("scroll_event", self._on_scroll)
        self._canvas_layout.addWidget(canvas, stretch=1)

        toolbar = NavigationToolbar2QT(canvas, self)
        toolbar.setStyleSheet(
            "QToolBar { border: none; background: transparent; }"
            "QToolButton { padding: 2px; }"
        )
        self._canvas_layout.addWidget(toolbar)

        self._canvas = canvas
        self._toolbar = toolbar

        self._apply_spec()

    def _apply_spec(self) -> None:
        """Применить спецификацию: скрыть кнопки, отключить тулбарные инструменты."""
        if not self._toolbar:
            return
        self._disable_builtin_scroll_zoom()
        if self._spec is None:
            return
        self._btn_zoom_in.setVisible(self._spec.supports_zoom)
        self._btn_zoom_out.setVisible(self._spec.supports_zoom)
        self._btn_reset.setVisible(self._spec.resettable)
        if not self._spec.pan:
            self._set_toolbar_action_enabled("pan", False)
        if not self._spec.rect_zoom:
            self._set_toolbar_action_enabled("zoom", False)

    def _set_toolbar_action_enabled(self, name: str, enabled: bool) -> None:
        """Включить/выключить кнопку тулбара matplotlib по имени toolitem."""
        actions = getattr(self._toolbar, "_actions", None)
        if not actions:
            return
        action = actions.get(name)
        if action is not None:
            action.setEnabled(enabled)

    def _disable_builtin_scroll_zoom(self) -> None:
        """Отключить встроенный scroll-зум matplotlib (глобально, для плитки).

        Встроенный zoom/pan-tool подключает свой ``scroll_event`` только в
        активном состоянии; подмена ``scroll_zoom`` no-op делает его безопасным.
        """
        toolmanager = getattr(self._toolbar, "toolmanager", None)
        if toolmanager is None:
            return
        for name in ("zoom", "pan"):
            try:
                tool = toolmanager.get_tool(name)
            except KeyError:
                continue
            if hasattr(tool, "scroll_zoom"):
                tool.scroll_zoom = _noop_scroll_zoom

    def disconnect_events(self) -> None:
        """Отвязать обработчики событий канваса (пары к mpl_connect)."""
        if self._canvas is not None:
            for cid in self._cids.values():
                try:
                    self._canvas.mpl_disconnect(cid)
                except (ValueError, KeyError):
                    continue
        self._cids.clear()

    def zoom(self, factor: float, anchor: tuple | None = None) -> None:
        """Изменить масштаб всех осей вокруг ``anchor``.

        ``anchor`` — точка в координатах данных (см. ``event.xdata/ydata``);
        если не задана, используется центр осей. ``factor > 1`` — приблизить,
        ``factor < 1`` — отдалить.
        """
        if self._fig is None or self._canvas is None:
            return
        for ax in self._fig.axes:
            try:
                xlog = ax.get_xscale() == "log"
                ylog = ax.get_yscale() == "log"
                ax_anchor = (float(anchor[0]), float(anchor[1])) if anchor is not None else None
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                cx = (xlim[0] + xlim[1]) / 2.0
                cy = (ylim[0] + ylim[1]) / 2.0
                if ax_anchor is not None:
                    cx = ax_anchor[0]
                    cy = ax_anchor[1]
                new_xlim = self._zoom_lims(xlim, cx, factor, log=xlog)
                new_ylim = self._zoom_lims(ylim, cy, factor, log=ylog)
                ax.set_xlim(*new_xlim)
                ax.set_ylim(*new_ylim)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Zoom skip axis %s: %s", ax, exc)
                continue
        self._canvas.draw_idle()

    @staticmethod
    def _zoom_lims(lim: tuple, anchor: float, factor: float, log: bool) -> tuple:
        """Новые границы, при которых точка ``anchor`` остаётся на месте."""
        lo, hi = float(lim[0]), float(lim[1])
        if log and lo > 0 and hi > 0 and anchor > 0:
            import math
            lo_l = math.log10(lo)
            hi_l = math.log10(hi)
            a_l = math.log10(anchor)
            new_lo = 10 ** (lo_l - (a_l - lo_l) * factor)
            new_hi = 10 ** (hi_l + (hi_l - a_l) * factor)
            return (new_lo, new_hi)
        new_lo = anchor - (anchor - lo) * factor
        new_hi = anchor + (hi - anchor) * factor
        return (new_lo, new_hi)

    def _on_scroll(self, event) -> None:
        """Колесо мыши: вращение вверх — приблизить, вниз — отдалить."""
        if event.inaxes is None:
            return
        if self._spec is not None and not self._spec.supports_zoom:
            return
        factor = self.ZOOM_STEP ** event.step if event.step > 0 else (1 / self.ZOOM_STEP) ** abs(event.step)
        self.zoom(factor, anchor=(event.xdata, event.ydata))

    def reset_view(self) -> None:
        """Вернуть масштаб диаграммы к исходному («по умолчанию»)."""
        if self._fig is None or self._canvas is None:
            return
        try:
            for ax in self._fig.axes:
                ax.relim()
                ax.autoscale_view()
        except (ValueError, TypeError, AttributeError) as exc:
            logger.debug("Reset view skip axis %s: %s", ax, exc)
        self._canvas.draw_idle()


class MultiChartView(QWidget):
    """Checklist of builtin charts + scrollable grid of rendered tiles.

    Supports multi-select rendering, column control, per-tile and bulk export.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[ChartData] = None
        self._tiles: list[_ChartTile] = []
        self._checkboxes: list[QCheckBox] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Top controls ──
        ctrl_row = QHBoxLayout()

        self._btn_select_all = QPushButton("Выбрать все")
        self._btn_select_all.clicked.connect(self._select_all)
        ctrl_row.addWidget(self._btn_select_all)

        self._btn_deselect_all = QPushButton("Снять все")
        self._btn_deselect_all.clicked.connect(self._deselect_all)
        ctrl_row.addWidget(self._btn_deselect_all)

        ctrl_row.addStretch()

        ctrl_row.addWidget(QLabel("Колонки:"))
        self._columns_spin = QSpinBox()
        self._columns_spin.setRange(1, 4)
        self._columns_spin.setValue(DEFAULT_COLUMNS)
        self._columns_spin.setToolTip("Число колонок сетки диаграмм (1 — один большой график)")
        self._columns_spin.valueChanged.connect(self._reflow_tiles)
        ctrl_row.addWidget(self._columns_spin)

        self._btn_render = QPushButton("Построить выбранные")
        self._btn_render.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self._btn_render.clicked.connect(self.render)
        ctrl_row.addWidget(self._btn_render)

        self._btn_export_all = QPushButton("Экспорт всех в PNG")
        self._btn_export_all.clicked.connect(self.export_all)
        ctrl_row.addWidget(self._btn_export_all)

        layout.addLayout(ctrl_row)

        # ── Body: checklist (left) + scrollable grid (right) ──
        body = QHBoxLayout()

        check_group = QGroupBox("Диаграммы")
        check_layout = QVBoxLayout(check_group)
        check_layout.setContentsMargins(8, 12, 8, 8)

        for chart in BUILTIN_CHARTS:
            cb = QCheckBox(chart.get_name())
            cb.setToolTip(chart.get_description())
            self._checkboxes.append(cb)
            check_layout.addWidget(cb)

        check_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8)
        scroll.setWidget(self._grid_widget)

        body.addWidget(check_group, stretch=0)
        body.addWidget(scroll, stretch=1)

        layout.addLayout(body, stretch=1)

    # ── Public API ──

    def set_data(self, data: Optional[ChartData]) -> None:
        self._data = data

    def has_tiles(self) -> bool:
        return bool(self._tiles)

    def count_tiles(self) -> int:
        return len(self._tiles)

    # ── Actions ──

    def _select_all(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        for cb in self._checkboxes:
            cb.setChecked(False)

    def _selected_indices(self) -> list[int]:
        return [i for i, cb in enumerate(self._checkboxes) if cb.isChecked()]

    def render(self) -> None:
        if self._data is None:
            QMessageBox.information(
                self, "Диаграммы",
                "Данные не загружены. Сначала выполните расчёт.",
            )
            return

        selected = self._selected_indices()
        if not selected:
            QMessageBox.information(
                self, "Диаграммы",
                "Выберите хотя бы одну диаграмму.",
            )
            return

        cols = self._columns_spin.value()
        self._release_tiles()
        self._clear_grid()

        for pos, chart_idx in enumerate(selected):
            chart = BUILTIN_CHARTS[chart_idx]
            try:
                fig = chart.render(self._data)
                chart_type = resolve_type_id(chart_idx)
                tile = _ChartTile()
                tile.set_figure(chart_idx, fig, chart.get_name(), chart_type=chart_type)
                tile._btn_export.clicked.connect(
                    lambda checked, t=tile: self._export_tile(t)
                )
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

    def _reflow_tiles(self) -> None:
        if not self._tiles:
            return
        cols = self._columns_spin.value()
        tiles = list(self._tiles)
        self._clear_grid()
        for pos, tile in enumerate(tiles):
            row, col = divmod(pos, cols)
            self._grid_layout.addWidget(tile, row, col)

    def _release_tiles(self) -> None:
        """Закрыть matplotlib-фигуры плиток перед заменой (освобождение памяти)."""
        import matplotlib.pyplot as plt
        for tile in self._tiles:
            tile.disconnect_events()
            fig = tile.figure
            if fig is not None:
                try:
                    plt.close(fig)
                except Exception as exc:
                    logger.warning("Не удалось закрыть фигуру: %s", exc)
        self._tiles.clear()

    def export_tile(self, tile: _ChartTile) -> None:
        if tile.chart_idx < 0:
            return
        chart = BUILTIN_CHARTS[tile.chart_idx]
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы",
            f"{chart.get_name().lower().replace(' ', '_')}.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )
        if not path:
            return
        fmt = path.rsplit(".", 1)[-1].lower()
        try:
            if tile.figure is not None:
                tile.figure.savefig(path, format=fmt, dpi=150, bbox_inches="tight")
            elif self._data is not None:
                chart.export(self._data, path, fmt=fmt)
            QMessageBox.information(self, "Экспорт", f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def _export_tile(self, tile: _ChartTile) -> None:
        self.export_tile(tile)

    def export_all(self) -> None:
        if not self._tiles:
            QMessageBox.information(self, "Экспорт", "Сначала постройте диаграммы.")
            return
        if self._data is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Папка для экспорта")
        if not folder:
            return
        from pathlib import Path
        folder_path = Path(folder)
        exported = 0
        for tile in self._tiles:
            if tile.chart_idx < 0:
                continue
            chart = BUILTIN_CHARTS[tile.chart_idx]
            fname = f"{chart.get_name().lower().replace(' ', '_')}.png"
            try:
                chart.export(self._data, str(folder_path / fname), fmt="png")
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