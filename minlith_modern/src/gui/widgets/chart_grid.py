"""Shared multi-chart grid widget — checklist + tiles, used by chart pages."""

from __future__ import annotations

import logging
from typing import NamedTuple

import numpy as np
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
from src.charts.data_builder import MINERAL_FIELDS, MINERAL_LABELS
from src.gui.widgets.chart_interactions import (
    ChartCategory,
    InteractionSpec,
    get_spec,
    resolve_type_id,
)
from src.gui.widgets.chart_sizes import ChartSizeSpec, aspect_for, get_size_spec
from src.gui.widgets.zoom_math import (
    DEFAULT_ZOOM_STEP,
    MIN_RANGE_WIDTH,
    ModifierMode,
    anchor_fraction,
    is_categorical_axis,
    modifier_mode,
    normalize_zoom_step,
    pan_lims,
    value_at_fraction,
    zoom_lims,
    zoom_radial,
)

logger = logging.getLogger(__name__)

DEFAULT_COLUMNS = 2
MIN_CANVAS_WIDTH = 320

# Типы, которые всегда занимают всю ширину сетки (много подграфиков).
FULL_WIDTH_TYPE_IDS: frozenset[str] = frozenset({"harker"})


class _AxisHome(NamedTuple):
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    rlim: tuple[float, float] | None = None
    aspect: str | None = None


def _noop_scroll_zoom(event) -> None:
    """Заглушка для встроенного scroll-зума matplotlib (отключение)."""
    return None


def _now_stamp() -> str:
    """Метка времени для имён файлов: ``YYYY-MM-DD_HH-MM-SS``."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _savefig_with_stamp(fig, path: str, fmt: str) -> None:
    """Сохранить фигуру с подписью даты/времени внизу (подпись потом убирается)."""
    from datetime import datetime

    caption = None
    try:
        caption = fig.text(
            0.5, 0.01, f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ha="center", va="bottom", fontsize=8, alpha=0.6, color="#888888",
            transform=fig.transFigure,
        )
        fig.savefig(path, format=fmt, dpi=150, bbox_inches="tight")
    finally:
        if caption is not None:
            try:
                caption.remove()
            except Exception:
                pass


class _ChartTile(QWidget):
    """A single chart tile: title + interactive canvas + controls.

    The canvas is a live matplotlib QtAgg widget with the standard toolbar
    (box-zoom, pan, home/reset, save) plus explicit zoom in/out buttons.
    """

    ZOOM_STEP = DEFAULT_ZOOM_STEP

    def __init__(self, parent=None, zoom_step: float = DEFAULT_ZOOM_STEP) -> None:
        super().__init__(parent)
        self._zoom_step = normalize_zoom_step(zoom_step)
        self._home: dict[int, _AxisHome] = {}
        self._pie_exploded: dict[int, bool] = {}
        self._pie_base: dict[int, tuple[float, float]] = {}
        self._pie_labels: dict[int, float] = {}
        self._view_notify = None
        self._size_spec: ChartSizeSpec = get_size_spec(None)
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
        self._btn_zoom_out.clicked.connect(self._on_zoom_out)
        btn_row.addWidget(self._btn_zoom_out)

        self._btn_zoom_in = QPushButton("Приблизить")
        self._btn_zoom_in.setFixedHeight(28)
        self._btn_zoom_in.setToolTip("Приблизить (колесо мыши — вверх)")
        self._btn_zoom_in.clicked.connect(self._on_zoom_in)
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
        self._size_spec = get_size_spec(chart_type)

        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

        canvas = FigureCanvasQTAgg(fig)
        canvas.setMinimumSize(MIN_CANVAS_WIDTH, 260)
        canvas.setStyleSheet("border: none;")
        self._cids["scroll_event"] = canvas.mpl_connect("scroll_event", self._on_scroll)
        self._canvas_layout.addWidget(
            canvas, stretch=1,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        toolbar = NavigationToolbar2QT(canvas, self)
        toolbar.setStyleSheet(
            "QToolBar { border: none; background: transparent; }"
            "QToolButton { padding: 2px; }"
        )
        self._canvas_layout.addWidget(toolbar)

        self._canvas = canvas
        self._toolbar = toolbar

        self._snapshot_home()
        self._apply_spec()
        self._connect_pie_events()
        self._apply_display_size()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._apply_display_size()

    def _native_aspect(self) -> float | None:
        """«Родной» аспект фигуры (ширина/высота), если известен."""
        fig = self._fig
        if fig is None:
            return None
        try:
            width, height = fig.get_size_inches()
            height = float(height)
            if height <= 0:
                return None
            return float(width) / height
        except Exception:
            return None

    def _apply_display_size(self) -> None:
        """Держать канвас в рамках стандарта размера типа диаграммы.

        Ширина ограничивается ``max_width`` и шириной хоста; высота считается
        из целевого аспекта и зажимается в ``[min_height, max_height]``.
        Канвас центрируется по горизонтали.
        """
        canvas = self._canvas
        if canvas is None:
            return
        avail_w = self._canvas_host.width()
        if avail_w <= 1:
            return
        spec = self._size_spec
        aspect = aspect_for(spec, self._native_aspect())
        width = avail_w if spec.max_width is None else min(avail_w, spec.max_width)
        width = max(MIN_CANVAS_WIDTH, width)
        height = int(round(width / aspect)) if aspect > 0 else width
        height = max(spec.min_height, min(height, spec.max_height))
        if canvas.width() == width and canvas.height() == height:
            return
        canvas.setFixedSize(width, height)

    def _connect_pie_events(self) -> None:
        """Подключить hover/click для круговых диаграмм (категория D).

        События подключаются только если спецификация категории D требует
        подсказки или действия по клику. Другие категории не трогаем.
        """
        if not self._spec:
            return
        if self._spec.category is not ChartCategory.PIE:
            return
        if not (self._spec.hover_info or self._spec.click_action):
            return
        if self._canvas is None:
            return
        self._pie_base.clear()
        self._pie_labels.clear()
        self._pie_exploded.clear()
        for i, wedge in enumerate(self._all_wedges()):
            self._pie_base[i] = (float(wedge.center[0]), float(wedge.center[1]))
            self._pie_exploded[i] = False
            pct = (float(wedge.theta2) - float(wedge.theta1)) / 360.0 * 100.0
            self._pie_labels[i] = pct
        self._cids["hover"] = self._canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._cids["click"] = self._canvas.mpl_connect("button_press_event", self._on_click)

    def _all_wedges(self) -> list:
        """Все сектора (Wedge) pie по всем осям фигуры."""
        wedges: list = []
        if self._fig is None:
            return wedges
        for ax in self._fig.axes:
            for patch in ax.patches:
                if patch.__class__.__name__ == "Wedge":
                    wedges.append(patch)
        return wedges

    def _get_wedges(self, ax) -> list:
        """Найти все Wedge (сектора круговой) на осях."""
        return [p for p in ax.patches if p.__class__.__name__ == "Wedge"]

    def _on_hover(self, event) -> None:
        """Hover для круговой: подсказка «Название — значение (процент)»."""
        if not self._spec or self._spec.category is not ChartCategory.PIE:
            return
        if not self._spec.hover_info:
            return
        if self._toolbar is None:
            return
        if event.inaxes:
            for i, wedge in enumerate(self._get_wedges(event.inaxes)):
                if wedge.contains(event)[0]:
                    label = wedge.get_label()
                    pct = self._pie_labels.get(i)
                    if pct is None:
                        pct = (float(wedge.theta2) - float(wedge.theta1)) / 360.0 * 100.0
                    self._toolbar.set_message(f"{label} — {pct:.1f}%")
                    return
        self._toolbar.set_message("")

    def _on_click(self, event) -> None:
        """Клик по круговой: explode среза; повторный клик — возврат."""
        if not self._spec or self._spec.category is not ChartCategory.PIE:
            return
        if not self._spec.click_action:
            return
        if event.inaxes:
            wedges = self._get_wedges(event.inaxes)
            for i, wedge in enumerate(wedges):
                if wedge.contains(event)[0]:
                    is_exploded = self._pie_exploded.get(i, False)
                    base = self._pie_base.get(i, (0.0, 0.0))
                    if is_exploded:
                        wedge.set_center((base[0], base[1]))
                    else:
                        offset = 0.1
                        theta = (float(wedge.theta1) + float(wedge.theta2)) / 2
                        rad = np.radians(theta)
                        wedge.set_center(
                            (base[0] + offset * np.cos(rad), base[1] + offset * np.sin(rad))
                        )
                    self._pie_exploded[i] = not is_exploded
                    self._canvas.draw_idle()
                    return

    def _reset_pie(self) -> None:
        """Вернуть все срезы круговой в базовое положение (сброс формы)."""
        for i, wedge in enumerate(self._all_wedges()):
            if self._pie_exploded.get(i, False):
                base = self._pie_base.get(i, (0.0, 0.0))
                wedge.set_center((base[0], base[1]))
                self._pie_exploded[i] = False

    def _snapshot_home(self) -> None:
        """Запомнить исходные пределы и аспект осей для сброса «По умолчанию»."""
        self._home.clear()
        if self._fig is None:
            return
        for ax in self._fig.axes:
            try:
                xlim = (float(ax.get_xlim()[0]), float(ax.get_xlim()[1]))
                ylim = (float(ax.get_ylim()[0]), float(ax.get_ylim()[1]))
                aspect = str(ax.get_aspect())
            except (TypeError, ValueError, IndexError):
                xlim, ylim, aspect = None, None, None

            rlim = None
            if hasattr(ax, "get_rlim"):
                try:
                    rlim = (float(ax.get_rlim()[0]), float(ax.get_rlim()[1]))
                except (TypeError, ValueError):
                    rlim = None

            self._home[id(ax)] = _AxisHome(xlim=xlim, ylim=ylim, rlim=rlim, aspect=aspect)

    def _min_range_for(self, ax, which: str) -> float:
        """Вычислить минимальную ширину диапазона зума (с учётом SPEC 3.1)."""
        base = MIN_RANGE_WIDTH
        if self._spec is not None:
            base = self._spec.min_range_width
            frac = self._spec.min_range_fraction
            if frac is not None:
                home = self._home.get(id(ax))
                if home is not None:
                    lims = home.xlim if which == "x" else home.ylim
                    if lims is not None:
                        width = abs(lims[1] - lims[0])
                        if width > 0:
                            return width * frac
        return base

    def _keep_aspect(self, ax) -> None:
        """Восстановить equal aspect, если он был задан изначально."""
        home = self._home.get(id(ax))
        if home and home.aspect == "equal":
            try:
                ax.set_aspect("equal", adjustable="datalim")
            except (ValueError, TypeError, AttributeError):
                pass

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

    def _supports_zoom(self) -> bool:
        """True, если плитке разрешён зум (иначе пределы менять нельзя)."""
        return self._spec is None or self._spec.supports_zoom

    def set_zoom_step(self, step: float) -> None:
        """Обновить шаг зума плитки (конфиг читать запрещено — параметр).

        После вызова кнопки «Приблизить/Отдалить» и колесо используют
        новый фактор без пересоздания плитки.
        """
        new_step = normalize_zoom_step(step)
        if new_step != step:
            logger.warning("zoom_step %r вне (1.0, 5.0] — использован дефолт %s", step, new_step)
        self._zoom_step = new_step

    def _on_zoom_in(self) -> None:
        self.zoom(self._zoom_step)

    def _on_zoom_out(self) -> None:
        self.zoom(1 / self._zoom_step)

    def zoom(
        self,
        factor: float,
        anchor: tuple | None = None,
        notify: bool = True,
    ) -> None:
        """Изменить масштаб осей вокруг ``anchor`` (зум обеих осей).

        ``anchor`` — точка в координатах данных (``event.xdata/ydata``);
        если не задана, используется центр каждой оси. ``factor > 1`` —
        приблизить, ``factor < 1`` — отдалить. Категориальные оси (номинальные
        метки) при зуме не масштабируются — пропускаются.
        """
        if self._fig is None or self._canvas is None:
            return
        self._apply_zoom(factor, anchor, ModifierMode.ZOOM_XY, notify=notify)

    def _apply_zoom(
        self,
        factor: float,
        anchor: tuple | None,
        mode: ModifierMode,
        redraw: bool = True,
        notify: bool = False,
    ) -> None:
        """Общая логика зума/пана: изменить пределы осей (без обязательного draw).

        ``mode`` определяет, какие оси затрагиваются.
        Для категории EQUAL_ASPECT принудительно ZOOM_XY.

        При ``notify=True`` после применения пределов плитка оповещает сетку
        о произошедшем зуме (синхронизация §9.2); сама сетка по каналу
        ``apply_synced`` не оповещает (защита от циклов).
        """
        if self._fig is None or self._canvas is None:
            return

        apply_mode = mode
        if self._spec is not None and self._spec.category is ChartCategory.EQUAL_ASPECT:
            apply_mode = ModifierMode.ZOOM_XY

        frac_x: float | None = None
        frac_y: float | None = None
        lim_out_x: tuple | None = None
        lim_out_y: tuple | None = None

        for ax in self._fig.axes:
            try:
                if hasattr(ax, "get_rlim"):
                    if apply_mode in (ModifierMode.ZOOM_XY, ModifierMode.ZOOM_Y):
                        rlim = ax.get_rlim()
                        min_r = self._min_range_for(ax, "y")
                        new_r = zoom_radial(rlim, factor, min_range_width=min_r)
                        ax.set_rlim(*new_r)
                        self._keep_aspect(ax)
                    continue

                xlog = ax.get_xscale() == "log"
                ylog = ax.get_yscale() == "log"
                ax_anchor = (
                    (float(anchor[0]), float(anchor[1])) if anchor is not None else None
                )
                if (
                    apply_mode in (ModifierMode.ZOOM_XY, ModifierMode.ZOOM_X)
                    and not is_categorical_axis(ax, "x")
                ):
                    xlim = ax.get_xlim()
                    if ax_anchor is not None and ax_anchor[0] is not None:
                        cx = ax_anchor[0]
                    else:
                        cx = (xlim[0] + xlim[1]) / 2.0
                    new_x = zoom_lims(
                        xlim,
                        cx,
                        factor,
                        log=xlog,
                        min_range_width=self._min_range_for(ax, "x"),
                    )
                    ax.set_xlim(*new_x)
                    lim_out_x = new_x
                    frac_x = anchor_fraction(cx, new_x)
                if (
                    apply_mode in (ModifierMode.ZOOM_XY, ModifierMode.ZOOM_Y)
                    and not is_categorical_axis(ax, "y")
                ):
                    ylim = ax.get_ylim()
                    if ax_anchor is not None and ax_anchor[1] is not None:
                        cy = ax_anchor[1]
                    else:
                        cy = (ylim[0] + ylim[1]) / 2.0
                    new_y = zoom_lims(
                        ylim,
                        cy,
                        factor,
                        log=ylog,
                        min_range_width=self._min_range_for(ax, "y"),
                    )
                    ax.set_ylim(*new_y)
                    lim_out_y = new_y
                    frac_y = anchor_fraction(cy, new_y)
                self._keep_aspect(ax)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Zoom skip axis %s: %s", ax, exc)
                continue
        if notify and self._view_notify is not None:
            payload: dict = {
                "kind": "zoom",
                "mode": apply_mode.value,
                "factor": factor,
                "anchor_frac_x": frac_x,
                "anchor_frac_y": frac_y,
            }
            if self._spec and self._spec.category is ChartCategory.EQUAL_ASPECT:
                payload["xlim"] = lim_out_x
                payload["ylim"] = lim_out_y
                for a in self._fig.axes:
                    if hasattr(a, "get_rlim"):
                        continue
                    payload["xlog"] = a.get_xscale() == "log"
                    payload["ylog"] = a.get_yscale() == "log"
                    break
            self._emit_view_changed(payload)
        if redraw:
            self._canvas.draw_idle()

    def _emit_view_changed(self, payload: dict) -> None:
        """Сообщить сетке о пользовательском изменении вида (зум/пан)."""
        if self._view_notify is None:
            return
        try:
            self._view_notify(self, payload)
        except Exception as exc:
            logger.debug("Sync notify skip: %s", exc)

    def pan_x(
        self,
        direction: float,
        mode: ModifierMode = ModifierMode.PAN_X,
        notify: bool = True,
    ) -> None:
        """Панорамирование по X: ``direction > 0`` — вправо, ``< 0`` — влево.

        Для категории C — пан обеих осей с сохранением аспекта.
        """
        if mode != ModifierMode.PAN_X:
            return
        if self._fig is None or self._canvas is None:
            return
        if self._spec is not None and not self._spec.pan:
            return
        for ax in self._fig.axes:
            try:
                if hasattr(ax, "get_rlim"):
                    continue
                if is_categorical_axis(ax, "x"):
                    continue
                xlog = ax.get_xscale() == "log"
                xlim = ax.get_xlim()
                new_x = pan_lims(xlim, direction, log=xlog)
                ax.set_xlim(*new_x)
                if (
                    self._spec is not None
                    and self._spec.category is ChartCategory.EQUAL_ASPECT
                ):
                    ylog = ax.get_yscale() == "log"
                    new_y = pan_lims(ax.get_ylim(), direction, log=ylog)
                    ax.set_ylim(*new_y)
                self._keep_aspect(ax)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Pan skip axis %s: %s", ax, exc)
                continue
        if notify and self._view_notify is not None:
            xy = bool(
                self._spec is not None
                and self._spec.category is ChartCategory.EQUAL_ASPECT
            )
            self._emit_view_changed({"kind": "pan", "fraction": direction, "xy": xy})
        self._canvas.draw_idle()

    def apply_synced(self, payload: dict, src_category: ChartCategory | None) -> None:
        """Применить синхронизированное изменение вида от другой плитки (§9).

        ``payload``: результат ``zoom`` (фактор + доли якоря; для категории C
        также абсолютные пределы) или ``pan`` (доля диапазона). Сетка вызывает
        метод, удерживая флаг трансляции — повторное оповещение не возникает.
        """
        if self._fig is None or self._canvas is None:
            return
        kind = payload.get("kind")
        if kind == "zoom":
            self._apply_synced_zoom(payload, src_category)
        elif kind == "pan":
            self._apply_synced_pan(payload)

    def _apply_synced_zoom(self, payload: dict, src_category: ChartCategory | None) -> None:
        mode = ModifierMode(payload["mode"])
        factor = float(payload["factor"])
        for ax in self._fig.axes:
            try:
                if hasattr(ax, "get_rlim"):
                    continue
                same_c = (
                    src_category is ChartCategory.EQUAL_ASPECT
                    and self._spec is not None
                    and self._spec.category is ChartCategory.EQUAL_ASPECT
                )
                if same_c:
                    xset = payload.get("xlim")
                    yset = payload.get("ylim")
                    if xset and not is_categorical_axis(ax, "x"):
                        if payload.get("xlog") == (ax.get_xscale() == "log"):
                            ax.set_xlim(*xset)
                    if yset and not is_categorical_axis(ax, "y"):
                        if payload.get("ylog") == (ax.get_yscale() == "log"):
                            ax.set_ylim(*yset)
                    self._keep_aspect(ax)
                    continue

                xlog = ax.get_xscale() == "log"
                ylog = ax.get_yscale() == "log"
                if (
                    mode in (ModifierMode.ZOOM_XY, ModifierMode.ZOOM_X)
                    and not is_categorical_axis(ax, "x")
                ):
                    xlim = ax.get_xlim()
                    frac = payload.get("anchor_frac_x")
                    if frac is None:
                        cx = (xlim[0] + xlim[1]) / 2.0
                    else:
                        cx = value_at_fraction(float(frac), xlim)
                    ax.set_xlim(
                        *zoom_lims(
                            xlim,
                            cx,
                            factor,
                            log=xlog,
                            min_range_width=self._min_range_for(ax, "x"),
                        )
                    )
                if (
                    mode in (ModifierMode.ZOOM_XY, ModifierMode.ZOOM_Y)
                    and not is_categorical_axis(ax, "y")
                ):
                    ylim = ax.get_ylim()
                    frac = payload.get("anchor_frac_y")
                    if frac is None:
                        cy = (ylim[0] + ylim[1]) / 2.0
                    else:
                        cy = value_at_fraction(float(frac), ylim)
                    ax.set_ylim(
                        *zoom_lims(
                            ylim,
                            cy,
                            factor,
                            log=ylog,
                            min_range_width=self._min_range_for(ax, "y"),
                        )
                    )
                self._keep_aspect(ax)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Sync zoom skip axis %s: %s", ax, exc)
                continue

    def _apply_synced_pan(self, payload: dict) -> None:
        fraction = float(payload.get("fraction", 0.0))
        xy = bool(payload.get("xy", False))
        for ax in self._fig.axes:
            try:
                if hasattr(ax, "get_rlim"):
                    continue
                if not is_categorical_axis(ax, "x"):
                    xlog = ax.get_xscale() == "log"
                    ax.set_xlim(*pan_lims(ax.get_xlim(), fraction, log=xlog))
                if xy and not is_categorical_axis(ax, "y"):
                    ylog = ax.get_yscale() == "log"
                    ax.set_ylim(*pan_lims(ax.get_ylim(), fraction, log=ylog))
                self._keep_aspect(ax)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Sync pan skip axis %s: %s", ax, exc)
                continue

    def _restore_view(self, redraw: bool = True) -> None:
        """Восстановить форму/пределы: pie — базовые центры, C/Polar — snapshot.

        Для категории D возвращает выдвинутые срезы на место (explode off),
        для C и полярных — пределы из snapshot рендерера. Остальные плитки
        (если зум разрешён) — relim + autoscale.
        """
        if self._fig is None or self._canvas is None:
            return
        if self._spec and self._spec.category is ChartCategory.PIE:
            self._reset_pie()
            if redraw:
                self._canvas.draw_idle()
            return
        if not self._supports_zoom():
            return

        if self._spec and self._spec.category in (
            ChartCategory.EQUAL_ASPECT,
            ChartCategory.POLAR,
        ):
            for ax in self._fig.axes:
                home = self._home.get(id(ax))
                if home:
                    try:
                        if home.rlim and hasattr(ax, "set_rlim"):
                            ax.set_rlim(*home.rlim)
                        if home.xlim:
                            ax.set_xlim(*home.xlim)
                        if home.ylim:
                            ax.set_ylim(*home.ylim)
                        if home.aspect and home.aspect != "auto":
                            ax.set_aspect(home.aspect, adjustable="datalim")
                        continue
                    except (ValueError, TypeError, AttributeError) as exc:
                        logger.debug("Reset home skip axis %s: %s", ax, exc)
                        continue

        for ax in self._fig.axes:
            try:
                ax.relim()
                ax.autoscale(enable=True)
            except (ValueError, TypeError, AttributeError) as exc:
                logger.debug("Reset view skip axis %s: %s", ax, exc)
        if redraw:
            self._canvas.draw_idle()

    def _on_scroll(self, event) -> None:
        """Колесо мыши: с модификаторами — зум по осям или пан, без — зум обеих осей."""
        mode = modifier_mode(event)
        if mode is ModifierMode.NONE:
            return
        if not self._supports_zoom():
            return
        step = self._zoom_step
        if event.step > 0:
            factor = step
            direction = -1.0
        else:
            factor = 1 / step
            direction = 1.0
        if mode is ModifierMode.PAN_X:
            self.pan_x(direction)
        else:
            anchor = (event.xdata, event.ydata)
            self._apply_zoom(factor, anchor, mode, notify=True)

    def reset_view(self) -> None:
        """Вернуть масштаб диаграммы к исходному («по умолчанию»)."""
        self._restore_view(redraw=True)


class MultiChartView(QWidget):
    """Checklist of builtin charts + scrollable grid of rendered tiles.

    Supports multi-select rendering, column control, per-tile and bulk export.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: ChartData | None = None
        self._tiles: list[_ChartTile] = []
        self._checkboxes: list[QCheckBox] = []
        self._zoom_step: float = DEFAULT_ZOOM_STEP
        self._syncing: bool = False

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

        self._btn_zoom_all_in = QPushButton("Приблизить все")
        self._btn_zoom_all_in.clicked.connect(lambda: self.zoom_all(1))
        ctrl_row.addWidget(self._btn_zoom_all_in)

        self._btn_zoom_all_out = QPushButton("Отдалить все")
        self._btn_zoom_all_out.clicked.connect(lambda: self.zoom_all(-1))
        ctrl_row.addWidget(self._btn_zoom_all_out)

        self._btn_reset_all = QPushButton("Сбросить все")
        self._btn_reset_all.clicked.connect(self.reset_all)
        ctrl_row.addWidget(self._btn_reset_all)

        self._btn_export_all = QPushButton("Экспорт всех в PNG")
        self._btn_export_all.clicked.connect(self.export_all)
        ctrl_row.addWidget(self._btn_export_all)

        self._btn_export_pdf = QPushButton("Экспорт всех в PDF")
        self._btn_export_pdf.clicked.connect(self.export_all_pdf)
        ctrl_row.addWidget(self._btn_export_pdf)

        self._chk_sync = QCheckBox("Синхронизировать зум")
        self._chk_sync.setToolTip(
            "Зум/пан плитки применяется ко всем плиткам той же группы "
            "(по sync_group спецификации: bar-y, ternary-100, tas-field, samples и др.)"
        )
        ctrl_row.addWidget(self._chk_sync)

        layout.addLayout(ctrl_row)

        # ── Body: side panel (диаграммы → минералы → построить) + grid ──
        body = QHBoxLayout()

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(6)

        check_group = QGroupBox("Диаграммы")
        check_layout = QVBoxLayout(check_group)
        check_layout.setContentsMargins(8, 12, 8, 8)

        for chart in BUILTIN_CHARTS:
            cb = QCheckBox(chart.get_name())
            cb.setToolTip(chart.get_description())
            self._checkboxes.append(cb)
            check_layout.addWidget(cb)

        check_layout.addStretch()
        side_layout.addWidget(check_group, stretch=1)

        # Блок выбора минералов — между чекбоксами диаграмм и построением.
        self._mineral_group = QGroupBox("Минералы для построения")
        mineral_layout = QVBoxLayout(self._mineral_group)
        mineral_layout.setContentsMargins(8, 12, 8, 8)

        min_tools = QHBoxLayout()
        btn_min_all = QPushButton("Все")
        btn_min_all.setToolTip("Отметить все минералы")
        btn_min_all.clicked.connect(lambda: self._set_minerals(True))
        min_tools.addWidget(btn_min_all)
        btn_min_none = QPushButton("Снять")
        btn_min_none.setToolTip("Снять отметки со всех минералов")
        btn_min_none.clicked.connect(lambda: self._set_minerals(False))
        min_tools.addWidget(btn_min_none)
        min_tools.addStretch()
        mineral_layout.addLayout(min_tools)

        self._mineral_widget = QWidget()
        self._mineral_checkbox_layout = QVBoxLayout(self._mineral_widget)
        self._mineral_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self._mineral_checkbox_layout.setSpacing(2)
        mineral_layout.addWidget(self._mineral_widget)

        side_layout.addWidget(self._mineral_group, stretch=1)

        self._btn_render = QPushButton("Построить выбранные")
        self._btn_render.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self._btn_render.clicked.connect(self.render)
        side_layout.addWidget(self._btn_render)

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setWidget(side)
        side_scroll.setFixedWidth(300)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.addWidget(side_scroll, stretch=0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8)
        scroll.setWidget(self._grid_widget)

        body.addWidget(scroll, stretch=1)

        layout.addLayout(body, stretch=1)

        self._mineral_checkboxes: dict[str, QCheckBox] = {}

    # ── Public API ──

    def set_zoom_step(self, step: float) -> None:
        """Задать шаг зума для сетки и всех живых плиток (без пересоздания)."""
        self._zoom_step = normalize_zoom_step(step)
        for tile in self._tiles:
            tile.set_zoom_step(self._zoom_step)

    def set_data(self, data: ChartData | None) -> None:
        self._data = data
        self._populate_minerals(data)

    def _populate_minerals(self, data: ChartData | None) -> None:
        """Пересоздать чекбоксы минералов по данным (отмечены все ненулевые)."""
        while self._mineral_checkbox_layout.count():
            item = self._mineral_checkbox_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._mineral_checkboxes.clear()

        if data is None or not data.minerals_wt:
            self._mineral_group.setEnabled(False)
            return
        self._mineral_group.setEnabled(True)

        nonzero = {k for k, arr in data.minerals_wt.items() if len(arr) and bool(np.any(arr))}
        if not nonzero:
            nonzero = set(data.minerals_wt)
        for key in MINERAL_FIELDS:
            if key not in data.minerals_wt:
                continue
            cb = QCheckBox(MINERAL_LABELS.get(key, key))
            cb.setToolTip(key)
            cb.setChecked(key in nonzero)
            self._mineral_checkboxes[key] = cb
            self._mineral_checkbox_layout.addWidget(cb)
        self._mineral_checkbox_layout.addStretch()

    def _set_minerals(self, checked: bool) -> None:
        for cb in self._mineral_checkboxes.values():
            cb.setChecked(checked)

    def selected_minerals(self) -> list[str]:
        """Порядок — по MINERAL_FIELDS (не менять под данные)."""
        return [k for k in MINERAL_FIELDS
                if k in self._mineral_checkboxes and self._mineral_checkboxes[k].isChecked()]

    def _mineral_filtered_data(self) -> ChartData:
        """Копия данных с minerals_wt, ограниченным выбранными минералами."""
        data = self._data
        if data is None:
            return data  # type: ignore[return-value]
        if not self._mineral_checkboxes:
            return data
        sel = set(self.selected_minerals())
        if len(sel) == len(data.minerals_wt):
            return data
        import copy
        filtered = copy.copy(data)
        filtered.minerals_wt = {k: v for k, v in data.minerals_wt.items() if k in sel}
        return filtered

    def has_tiles(self) -> bool:
        return bool(self._tiles)

    def count_tiles(self) -> int:
        return len(self._tiles)

    def zoom_all(self, sign: int) -> None:
        """Приблизить (``sign=1``) или отдалить (``sign=-1``) все плитки.

        Круговые и прочие без поддержки зума пропускаются молча. Пределы
        мутируются без промежуточных отрисовок; каждая затронутая плитка
        рисуется один раз (бюджет §12).
        """
        factor = self._zoom_step if sign > 0 else 1 / self._zoom_step
        canvases: list = []
        for tile in self._tiles:
            if not tile._supports_zoom():
                continue
            tile._apply_zoom(factor, None, ModifierMode.ZOOM_XY, redraw=False)
            if tile.canvas is not None:
                canvases.append(tile.canvas)
        for canvas in canvases:
            try:
                canvas.draw_idle()
            except Exception as exc:
                logger.debug("Group zoom draw skip: %s", exc)

    def reset_all(self) -> None:
        """Сбросить масштаб всех плиток (кроме тех, что не поддерживают зум)."""
        canvases: list = []
        for tile in self._tiles:
            tile._restore_view(redraw=False)
            if tile.canvas is not None:
                canvases.append(tile.canvas)
        for c in canvases:
            c.draw_idle()

    def on_tile_view_changed(self, tile: _ChartTile, payload: dict) -> None:
        """Синхронизировать изменение вида одной плитки в её sync_group (§9).

        Вызывается плиткой после её собственного зума/пана. Транслируется
        только плиткам той же ``sync_group``, кроме круговых. Категория C —
        абсолютные пределы (общий домен); A/B/E — фактор + доли якоря
        к своим пределам; паны — в долях диапазона. Защита от циклов:
        ``self._syncing`` держится на время трансляции и подавляет
        повторное оповещение плиток.
        """
        if self._syncing:
            return
        if not self._chk_sync.isChecked():
            return
        src_spec = tile.spec
        if src_spec is None or not src_spec.sync_group:
            return
        group = src_spec.sync_group
        if "{oxide}" in group:
            group = group.replace("{oxide}", "sio2")
        canvases: list = []
        self._syncing = True
        try:
            for other in self._tiles:
                if other is tile:
                    continue
                spec = other.spec
                if spec is None or not spec.sync_group:
                    continue
                other_group = spec.sync_group
                if "{oxide}" in other_group:
                    other_group = other_group.replace("{oxide}", "sio2")
                if other_group != group:
                    continue
                if spec.category is ChartCategory.PIE:
                    continue
                other.apply_synced(payload, src_spec.category)
                if other.canvas is not None:
                    canvases.append(other.canvas)
        except Exception as exc:
            logger.debug("Sync broadcast error: %s", exc)
        finally:
            self._syncing = False
        for c in canvases:
            c.draw_idle()

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

        render_data = self._mineral_filtered_data()
        widgets: list = []
        for chart_idx in selected:
            chart = BUILTIN_CHARTS[chart_idx]
            try:
                fig = chart.render(render_data)
                chart_type = resolve_type_id(chart_idx)
                tile = _ChartTile(zoom_step=self._zoom_step)
                tile.set_figure(chart_idx, fig, chart.get_name(), chart_type=chart_type)
                tile._full_width = self._is_wide_chart(chart_idx)
                tile._view_notify = self.on_tile_view_changed
                tile._btn_export.clicked.connect(
                    lambda checked, t=tile: self._export_tile(t)
                )
                widgets.append(tile)
                self._tiles.append(tile)
            except Exception as e:
                logger.error("Chart '%s' failed: %s", chart.get_name(), e)
                err_label = QLabel(f"Ошибка: {chart.get_name()}\n{e}")
                err_label.setStyleSheet("color: #f38ba8; padding: 8px;")
                err_label._full_width = self._is_wide_chart(chart_idx)
                widgets.append(err_label)

        self._place_grid(widgets, cols)
        logger.info("Rendered %d charts", len(self._tiles))

    def _is_wide_chart(self, chart_idx: int) -> bool:
        """Полноширинный тип (много подграфиков — не умещается в колонку)."""
        try:
            return resolve_type_id(chart_idx) in FULL_WIDTH_TYPE_IDS
        except ValueError:
            return False

    def _place_grid(self, widgets: list, cols: int, clear: bool = True) -> None:
        """Разложить виджеты по сетке; широкие занимают всю строку."""
        if clear:
            self._clear_grid()
        cur_row = 0
        col = 0
        for w in widgets:
            if getattr(w, "_full_width", False):
                if col != 0:
                    cur_row += 1
                    col = 0
                self._grid_layout.addWidget(w, cur_row, 0, 1, cols)
                cur_row += 1
            else:
                self._grid_layout.addWidget(w, cur_row, col)
                col += 1
                if col >= cols:
                    cur_row += 1
                    col = 0

    def _reflow_tiles(self) -> None:
        if not self._tiles:
            return
        cols = self._columns_spin.value()
        tiles = list(self._tiles)
        self._clear_grid(keep=tiles)
        self._place_grid(tiles, cols, clear=False)

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
        stamp = _now_stamp()
        default = f"{chart.get_name().lower().replace(' ', '_')}_{stamp}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы",
            default,
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )
        if not path:
            return
        fmt = path.rsplit(".", 1)[-1].lower()
        try:
            if tile.figure is not None:
                _savefig_with_stamp(tile.figure, path, fmt)
            elif self._data is not None:
                chart.export(self._mineral_filtered_data(), path, fmt=fmt)
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
        data = self._mineral_filtered_data()
        stamp = _now_stamp()
        exported = 0
        for tile in self._tiles:
            if tile.chart_idx < 0:
                continue
            chart = BUILTIN_CHARTS[tile.chart_idx]
            fname = f"{chart.get_name().lower().replace(' ', '_')}_{stamp}.png"
            try:
                chart.export(data, str(folder_path / fname), fmt="png")
                exported += 1
            except Exception as e:
                logger.error("Export '%s' failed: %s", chart.get_name(), e)
        QMessageBox.information(
            self, "Экспорт",
            f"Экспортировано {exported} из {len(self._tiles)} диаграмм.",
        )

    def export_all_pdf(self) -> None:
        """Сохранить все плитки в один многостраничный PDF (по странице на плитку).

        Экспортируется текущий вид каждой плитки (зум/пан не сбрасываются).
        """
        if not self._tiles:
            QMessageBox.information(self, "Экспорт", "Сначала постройте диаграммы.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт всех в PDF", f"diagrams_{_now_stamp()}.pdf", "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            exported = self._export_all_pdf_to(path)
            QMessageBox.information(
                self, "Экспорт",
                f"Сохранено {exported} из {len(self._tiles)} диаграмм: {path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def _export_all_pdf_to(self, path: str) -> int:
        from matplotlib.backends.backend_pdf import PdfPages

        data = self._mineral_filtered_data()
        pages: list = []
        temporary: list = []
        for tile in self._tiles:
            if tile.chart_idx < 0:
                continue
            fig = tile.figure
            if fig is None:
                if self._data is None:
                    continue
                fig = BUILTIN_CHARTS[tile.chart_idx].render(data)
                temporary.append(fig)
            pages.append(fig)
        if not pages:
            return 0
        try:
            with PdfPages(path) as pdf:
                for fig in pages:
                    pdf.savefig(fig, bbox_inches="tight")
        finally:
            if temporary:
                import matplotlib.pyplot as plt
                for fig in temporary:
                    plt.close(fig)
        return len(pages)

    def _clear_grid(self, keep: list | None = None) -> None:
        """Убрать виджеты из сетки.

        ``keep`` — плитки, которые переиспользуются (reflow): их только
        отсоединяют от layout, но не удаляют. Остальные виджеты удаляются
        отложенно.
        """
        preserved = keep or ()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if any(widget is tile for tile in preserved):
                continue
            widget.deleteLater()
