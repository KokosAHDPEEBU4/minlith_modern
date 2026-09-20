"""Страница настроек — сайдбар + карточки.

Редизайн по прототипам «эдавыбджа.py» / «Новый текстовый документ.html»:
навигация по секциям, поиск настроек, карточки с описаниями, тумблеры,
адаптация под светлую/тёмную тему приложения.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.utils.config import ConfigManager

logger = logging.getLogger(__name__)

# Цвета Catppuccin-палитры по теме (должны совпадать с ../styles/*.qss).
_THEME_COLORS: dict[str, dict[str, str]] = {
    "dark": {
        "window": "#1e1e2e", "panel": "#313244", "border": "#45475a",
        "text": "#cdd6f4", "muted": "#a6adc8", "accent": "#89b4fa",
        "accent_hover": "#74c7ec", "danger": "#f38ba8", "primary_text": "#11111b",
        "success": "#a6e3a1",
    },
    "light": {
        "window": "#ffffff", "panel": "#f0f0f5", "border": "#d0d0d8",
        "text": "#1e1e2e", "muted": "#6b7280", "accent": "#1e66f5",
        "accent_hover": "#3b82f6", "danger": "#d20f39", "primary_text": "#ffffff",
        "success": "#10b981",
    },
}


_TOGGLE_IMAGES: dict[tuple[str, bool], str] = {}


def _toggle_image_path(theme: str, checked: bool) -> str:
    """Рендерить PNG-тумблер (34×18, ползунок слева/справа) и вернуть путь."""
    key = (theme, checked)
    if key in _TOGGLE_IMAGES:
        return _TOGGLE_IMAGES[key]

    c = _THEME_COLORS.get(theme, _THEME_COLORS["dark"])
    track = c["accent"] if checked else c["border"]
    label = "on" if checked else "off"
    path = Path(tempfile.gettempdir()) / f"minlith_toggle_{theme}_{label}.png"

    pm = QPixmap(34, 18)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(track))
    painter.drawRoundedRect(QRectF(0, 0, 34, 18), 9, 9)
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(QRectF(1 + (16 if checked else 0), 1, 16, 16))
    painter.end()
    pm.save(str(path), "PNG")

    _TOGGLE_IMAGES[key] = str(path)
    return str(path)


def _build_theme_qss(theme: str) -> str:
    """Собрать QSS страницы под текущую тему (Catppuccin)."""
    c = _THEME_COLORS.get(theme, _THEME_COLORS["dark"])
    off_img = _toggle_image_path(theme, False).replace("\\", "/")
    on_img = _toggle_image_path(theme, True).replace("\\", "/")
    return f"""
QWidget {{ background-color: {c['window']}; color: {c['text']}; font-size: 13px; }}

QLabel#navTitle {{ font-size: 17px; font-weight: bold; padding: 4px 20px 16px; }}

QListWidget#settingsNav {{
    background-color: {c['panel']}; border: none;
    border-right: 1px solid {c['border']};
    font-size: 14px; outline: 0; padding-top: 4px;
}}
QListWidget#settingsNav::item {{
    padding: 11px 20px; color: {c['muted']};
    border-left: 3px solid transparent;
}}
QListWidget#settingsNav::item:hover {{ background-color: {c['window']}; color: {c['text']}; }}
QListWidget#settingsNav::item:selected {{
    background-color: {c['window']}; color: {c['accent']};
    border-left-color: {c['accent']}; font-weight: 600;
}}

QLabel#sectionTitle {{ font-size: 22px; font-weight: bold; }}

QFrame#settingsCard {{
    background-color: {c['panel']}; border: 1px solid {c['border']};
    border-radius: 10px;
}}
QLabel#cardTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#cardDesc {{ font-size: 12px; color: {c['muted']}; margin-bottom: 8px; }}
QLabel#settingLabel {{ font-size: 14px; }}
QLabel#settingSub {{ font-size: 12px; color: {c['muted']}; }}

QLineEdit {{
    padding: 6px 10px; border: 1px solid {c['border']};
    border-radius: 6px; background-color: {c['window']}; color: {c['text']};
}}
QLineEdit:focus {{ border-color: {c['accent']}; }}
QLineEdit#searchEdit {{ padding: 8px 12px; }}

QComboBox {{
    padding: 5px 10px; border: 1px solid {c['border']};
    border-radius: 6px; background-color: {c['window']}; color: {c['text']};
    min-width: 150px;
}}
QComboBox:focus {{ border-color: {c['accent']}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background-color: {c['window']}; color: {c['text']};
    selection-background-color: {c['accent']}; selection-color: {c['primary_text']};
}}

QSpinBox, QDoubleSpinBox {{
    padding: 5px 8px; border: 1px solid {c['border']};
    border-radius: 6px; background-color: {c['window']}; color: {c['text']};
    min-width: 110px;
}}

QPushButton {{
    padding: 7px 14px; border: 1px solid {c['border']};
    border-radius: 6px; background-color: {c['panel']};
    color: {c['text']}; font-size: 13px;
}}
QPushButton:hover {{ background-color: {c['window']}; }}
QPushButton#primary {{
    background-color: {c['accent']}; color: {c['primary_text']}; border: none;
}}
QPushButton#primary:hover {{ background-color: {c['accent_hover']}; }}
QPushButton#dangerRow {{ color: {c['danger']}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 34px; height: 18px; border: none;
    background: transparent;
    image: url({off_img});
}}
QCheckBox::indicator:checked {{
    image: url({on_img});
}}

QScrollArea {{ background: transparent; border: none; }}

QLabel#toast {{
    background-color: {c['success']}; color: {c['primary_text']};
    padding: 10px 18px; border-radius: 8px; font-size: 13px;
}}
"""


class SettingsPage(QWidget):
    """Страница настроек приложения (сайдбар + карточки)."""

    settings_changed = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._search_items: list[tuple[QWidget, QFrame, str]] = []
        self._cards: list[QFrame] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: transparent;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 20, 0, 0)
        side_layout.setSpacing(0)

        nav_title = QLabel("⚙️ Настройки")
        nav_title.setObjectName("navTitle")
        side_layout.addWidget(nav_title)

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("searchEdit")
        self._search_edit.setPlaceholderText("Поиск настроек…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search)
        self._search_edit.setStyleSheet("margin: 0 16px 12px;")
        side_layout.addWidget(self._search_edit)

        self._sections = ["Расчёт", "Экспорт", "Диаграммы", "Интерфейс"]
        self._nav = QListWidget()
        self._nav.setObjectName("settingsNav")
        for name in self._sections:
            self._nav.addItem(QListWidgetItem(name))
        self._nav.setCurrentRow(0)
        side_layout.addWidget(self._nav)

        root.addWidget(sidebar)

        # ── Content ──
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 28, 20, 28)
        content_layout.setSpacing(14)

        self._page_title = QLabel(self._sections[0])
        self._page_title.setObjectName("sectionTitle")
        content_layout.addWidget(self._page_title)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_calculation_section())
        self._stack.addWidget(self._build_export_section())
        self._stack.addWidget(self._build_charts_section())
        self._stack.addWidget(self._build_interface_section())
        content_layout.addWidget(self._stack, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_reset = QPushButton("Сбросить")
        self._btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(self._btn_reset)
        btn_row.addStretch()
        self._btn_save = QPushButton("Сохранить")
        self._btn_save.setObjectName("primary")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)
        content_layout.addLayout(btn_row)

        root.addWidget(content, stretch=1)

        # ── Toast ──
        self._toast = QLabel("", self)
        self._toast.setObjectName("toast")
        self._toast.hide()

        # Connections
        self._nav.currentRowChanged.connect(self._switch_page)
        self._apply_qss()

    # ── Помощники разметки ────────────────────────────────

    def _apply_qss(self) -> None:
        theme = self._config.get("theme", "dark")
        self.setStyleSheet(_build_theme_qss(theme))

    def _switch_page(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        self._page_title.setText(self._sections[idx])

    def _make_card(self, title: str, desc: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("settingsCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 20, 18, 20)
        lay.setSpacing(4)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        lay.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("cardDesc")
            d.setWordWrap(True)
            lay.addWidget(d)
        self._cards.append(card)
        return card, lay

    def _add_row(
        self,
        card: QFrame,
        layout: QVBoxLayout,
        label: str,
        control: QWidget,
        subtitle: str = "",
        tooltip: str = "",
    ) -> None:
        row = QWidget()
        row.setObjectName("settingRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 9, 0, 9)
        h.setSpacing(16)
        info = QVBoxLayout()
        info.setSpacing(2)
        lbl = QLabel(label)
        lbl.setObjectName("settingLabel")
        info.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("settingSub")
            sub.setWordWrap(True)
            info.addWidget(sub)
        h.addLayout(info, 1)
        if tooltip:
            control.setToolTip(tooltip)
        h.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(row)
        card_title = ""
        title_lbl = card.findChild(QLabel, "cardTitle")
        if title_lbl is not None:
            card_title = title_lbl.text()
        self._search_items.append(
            (row, card, " ".join((card_title, label, subtitle)).lower()))

    def _section_page(self, specs) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(18)
        for title, desc, build in specs:
            card, lay = self._make_card(title, desc)
            build(lay, card)
            col.addWidget(card)
        col.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    # ── Секции ────────────────────────────────────────────

    def _build_calculation_section(self) -> QScrollArea:
        def _build_params(lay: QVBoxLayout, card: QFrame) -> None:
            mode = QComboBox()
            mode.addItems(["clean", "stub", "custom"])
            mode.setCurrentText(self._config.get("algorithm_mode", "clean"))
            mode.setToolTip(
                "clean — clean_engine: полный паритет с Excel-версией (без округлений)\n"
                "stub — резервный расчёт по теории\n"
                "custom — пользовательская реализация алгоритма"
            )
            self._algorithm_mode = mode
            self._add_row(card, lay, "Режим алгоритма", mode,
                          subtitle="clean — паритет с Excel (без округлений)",
                          tooltip="Какой движок участвует в расчётах")

            self._molar_mass = QComboBox()
            self._molar_mass.addItems(["iupac", "minlith"])
            self._molar_mass.setCurrentText(self._config.get("molar_mass_source", "iupac"))
            self._molar_mass.setToolTip("Официальные (IUPAC) или исходные значения MINLITH")
            self._add_row(card, lay, "Источник молярных масс", self._molar_mass,
                          subtitle="База для пересчёта оксидов в молекулы",
                          tooltip="iupac — современные значения, minlith — из Excel-оригинала")

            self._batch_size = QComboBox()
            self._batch_size.addItems(["auto", "1", "2", "4", "8"])
            self._batch_size.setCurrentText(str(self._config.get("batch_size", "auto")))
            self._batch_size.setToolTip("Размер пакета параллельного расчёта (auto = до 4 потоков)")
            self._add_row(card, lay, "Размер пакета", self._batch_size,
                          subtitle="Параллельный расчёт образцов (auto — до 4 потоков)",
                          tooltip="Эффективно только при запуске расчёта из CLI")

            self._timeout = QSpinBox()
            self._timeout.setRange(10, 600)
            self._timeout.setValue(self._config.get("timeout_seconds", 120))
            self._timeout.setSuffix(" сек")
            self._timeout.setToolTip("Лимит времени на расчёт одного образца (10–600 сек)")
            self._add_row(card, lay, "Таймаут расчёта", self._timeout,
                          subtitle="Защита от «зависших» образцов",
                          tooltip="Если образец не посчитался за это время — расчёт прекращается")

        def _build_tolerance(lay: QVBoxLayout, card: QFrame) -> None:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            self._sum_lo = QLineEdit(str(self._config.get("sum_tolerance", [98, 102])[0]))
            self._sum_lo.setFixedWidth(64)
            self._sum_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._sum_hi = QLineEdit(str(self._config.get("sum_tolerance", [98, 102])[1]))
            self._sum_hi.setFixedWidth(64)
            self._sum_hi.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.addWidget(self._sum_lo)
            dash = QLabel("—")
            h.addWidget(dash)
            h.addWidget(self._sum_hi)
            self._add_row(card, lay, "Допустимая сумма (%)", row,
                          subtitle="Сумма оксидов после нормировки",
                          tooltip="Если сумма вне диапазона — сработает "
                                  "предупреждение или автокоррекция")

            self._auto_correct = QCheckBox()
            self._auto_correct.setChecked(self._config.get("auto_correct_sum", False))
            self._auto_correct.setToolTip("Нормировать суммы вне допуска до 100%")
            self._add_row(card, lay, "Автокоррекция суммы до 100%", self._auto_correct,
                          subtitle="Нормировать суммы вне допуска",
                          tooltip="Пропорционально пересчитать оксиды так, чтобы сумма стала 100%")

            self._warn_negative = QCheckBox()
            self._warn_negative.setChecked(self._config.get("warn_negative", True))
            self._add_row(card, lay, "Предупреждать об отрицательных", self._warn_negative,
                          subtitle="Подсветка отрицательных значений",
                          tooltip="Показывать предупреждение, если в формуле оказались "
                                  "отрицательные значения")

            self._decimal_places = QSpinBox()
            self._decimal_places.setRange(0, 6)
            self._decimal_places.setValue(self._config.get("decimal_places", 2))
            self._decimal_places.setToolTip("Сколько знаков выводить после запятой (0–6)")
            self._add_row(card, lay, "Знаков после запятой", self._decimal_places,
                          subtitle="Округление в результатах и экспорте",
                          tooltip="0 — целые, до 6 знаков")

        def _build_masses(lay: QVBoxLayout, card: QFrame) -> None:
            self._edit_masses = QPushButton("Изменить молярные массы…")
            self._edit_masses.setMinimumWidth(220)
            self._edit_masses.clicked.connect(self._on_edit_molar_masses)
            self._add_row(card, lay, "Пользовательские молярные массы", self._edit_masses,
                          subtitle="Переопределения поверх выбранного «Источника»",
                          tooltip="Открыть таблицу с правкой значений отдельных оксидов")

        return self._section_page([
            ("Основные параметры", "Движок, молярные массы и производительность", _build_params),
            ("Допуски и точность", "Контроль суммы оксидов и округление", _build_tolerance),
            ("Пользовательские молярные массы",
                          "Переопределения поверх базовой таблицы", _build_masses),
        ])

    def _build_export_section(self) -> QScrollArea:
        def _build(lay: QVBoxLayout, card: QFrame) -> None:
            self._include_formula_units = QCheckBox()
            self._include_formula_units.setChecked(self._config.get("include_formula_units", False))
            self._include_formula_units.setToolTip("Добавлять в выгрузку формульные единицы")
            self._add_row(card, lay, "Формулы (FormulaUnits)", self._include_formula_units,
                          subtitle="Добавлять в выгрузку результаты пересчёта в молекулы")

            self._include_parameters = QCheckBox()
            self._include_parameters.setChecked(self._config.get("include_parameters", True))
            self._include_parameters.setToolTip("Добавлять в выгрузку GeoParams")
            self._add_row(card, lay, "Геохимические параметры (GeoParams)",
                          self._include_parameters,
                          subtitle="CIA, ICV, PIA, ASI, AI и др.")

            self._include_defect = QCheckBox()
            self._include_defect.setChecked(self._config.get("include_defect", True))
            self._include_defect.setToolTip("Добавлять в выгрузку невязки баланса")
            self._add_row(card, lay, "Невязки (Defect)", self._include_defect,
                          subtitle="Остаток баланса после распределения минералов")

        return self._section_page([
            ("Опции экспорта", "Состав выгружаемых данных (Excel/CSV/JSON/LaTeX)", _build),
        ])

    def _build_charts_section(self) -> QScrollArea:
        def _build(lay: QVBoxLayout, card: QFrame) -> None:
            self._chart_theme = QComboBox()
            self._chart_theme.addItems(["dark", "light"])
            self._chart_theme.setCurrentText(self._config.get("chart_theme", "dark"))
            self._chart_theme.setToolTip("Фон диаграмм: тёмный (Catppuccin) или белый")
            self._add_row(card, lay, "Фон диаграмм", self._chart_theme,
                          subtitle="Catppuccin (тёмный) или белый",
                          tooltip="Цветовая схема самих диаграмм")

            self._zoom_step = QDoubleSpinBox()
            self._zoom_step.setRange(1.05, 5.0)
            self._zoom_step.setSingleStep(0.05)
            self._zoom_step.setDecimals(2)
            self._zoom_step.setValue(float(self._config.get("chart.zoom_step", 1.2)))
            self._zoom_step.setToolTip("Фактор зума за один шаг колеса/кнопки (1.05–5.0)")
            self._add_row(card, lay, "Шаг зума диаграмм", self._zoom_step,
                          subtitle="Величина приближения за один шаг",
                          tooltip="Как сильно приближает диаграмму одно «прокручивание» колеса")

        return self._section_page([
            ("Диаграммы", "Превью в GUI: фон и интерактивность", _build),
        ])

    def _build_interface_section(self) -> QScrollArea:
        def _build(lay: QVBoxLayout, card: QFrame) -> None:
            self._theme = QComboBox()
            self._theme.addItems(["dark", "light"])
            self._theme.setCurrentText(self._config.get("theme", "dark"))
            self._theme.setToolTip("Catppuccin dark / light — применяется сразу после сохранения")
            self._add_row(card, lay, "Тема интерфейса", self._theme,
                          subtitle="Catppuccin (тёмная) или светлая",
                          tooltip="Переключение темы применяется сразу после «Сохранить»")

            self._language = QComboBox()
            self._language.addItems(["ru", "en"])
            self._language.setCurrentText(self._config.get("language", "ru"))
            self._language.setToolTip("Язык интерфейса и подписей")
            self._add_row(card, lay, "Язык интерфейса", self._language,
                          subtitle="ru / en")

        return self._section_page([
            ("Интерфейс", "Внешний вид и локализация", _build),
        ])

    # ── Поиск ─────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        q = text.strip().lower()
        for row, card, search_text in self._search_items:
            row.setVisible(not q or q in search_text)
        if q:
            for card in self._cards:
                card.setVisible(any(
                    r.isVisible() for r, c, _ in self._search_items if c is card))
        else:
            for card in self._cards:
                card.setVisible(True)

    # ── Диалог молярных масс ──────────────────────────────

    def _on_edit_molar_masses(self) -> None:
        """Открыть редактор переопределений молярных масс (custom_molar_masses)."""
        from src.core.constants import MOLAR_MASSES_IUPAC, MOLAR_MASSES_MINLITH

        src = self._molar_mass.currentText()
        base = MOLAR_MASSES_MINLITH if src == "minlith" else MOLAR_MASSES_IUPAC
        saved = dict(self._config.get("custom_molar_masses", {}))

        dialog = QDialog(self)
        dialog.setWindowTitle("Пользовательские молярные массы")
        dialog.setMinimumSize(380, 420)
        lay = QVBoxLayout(dialog)

        hint = QLabel(
            "Пустое значение = использовать базовую таблицу.\n"
            "Переопределения действуют поверх «Источника молярных масс»."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        lay.addWidget(hint)

        table = QTableWidget(len(base), 2, dialog)
        table.setHorizontalHeaderLabels(["Оксид", "Молярная масса"])
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for i, (oxide, default) in enumerate(base.items()):
            table.setItem(i, 0, QTableWidgetItem(oxide))
            val = saved.get(oxide, default)
            table.setItem(i, 1, QTableWidgetItem("" if oxide not in saved
                                                 else f"{val:g}"))
        lay.addWidget(table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        result: dict[str, float] = {}
        for i in range(table.rowCount()):
            oxide = table.item(i, 0).text().strip()
            raw = table.item(i, 1).text().strip()
            if not raw:
                continue
            try:
                v = float(raw)
            except ValueError:
                continue
            if v > 0 and v != base.get(oxide):
                result[oxide] = v
        self._config["custom_molar_masses"] = result

        logger.info("Обновлены пользовательские молярные массы: %s", result)

    # ── Сохранение / сброс ────────────────────────────────

    def _on_save(self) -> None:
        self._config["molar_mass_source"] = self._molar_mass.currentText()
        try:
            lo = float(self._sum_lo.text())
            hi = float(self._sum_hi.text())
            self._config["sum_tolerance"] = [lo, hi]
        except ValueError:
            pass
        self._config["warn_negative"] = self._warn_negative.isChecked()
        self._config["auto_correct_sum"] = self._auto_correct.isChecked()
        self._config["decimal_places"] = self._decimal_places.value()
        self._config["timeout_seconds"] = self._timeout.value()
        self._config["algorithm_mode"] = self._algorithm_mode.currentText()
        self._config["include_formula_units"] = self._include_formula_units.isChecked()
        self._config["include_defect"] = self._include_defect.isChecked()
        self._config["include_parameters"] = self._include_parameters.isChecked()
        batch = self._batch_size.currentText()
        self._config["batch_size"] = "auto" if batch == "auto" else int(batch)
        self._config["chart.zoom_step"] = round(self._zoom_step.value(), 2)
        self._config["theme"] = self._theme.currentText()
        self._config["chart_theme"] = self._chart_theme.currentText()
        self._config["language"] = self._language.currentText()
        self._config.save()

        # Apply chart theme immediately
        from src.charts.engines.matplotlib_engine import set_chart_theme
        set_chart_theme(self._chart_theme.currentText())

        self._apply_qss()
        self.settings_changed.emit()
        self._show_toast("✓ Настройки сохранены")
        logger.info("Настройки сохранены")

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self, "Сброс настроек",
            "Вернуть все настройки по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._config.reset()
        self._reload_widgets()
        self.settings_changed.emit()
        self._show_toast("Сброшено до настроек по умолчанию")
        logger.info("Настройки сброшены до умолчаний")

    def _reload_widgets(self) -> None:
        """Reload widget values from config (after reset)."""
        self._molar_mass.setCurrentText(self._config.get("molar_mass_source", "iupac"))
        tol = self._config.get("sum_tolerance", [98.0, 102.0])
        self._sum_lo.setText(str(tol[0]))
        self._sum_hi.setText(str(tol[1]))
        self._warn_negative.setChecked(self._config.get("warn_negative", True))
        self._auto_correct.setChecked(self._config.get("auto_correct_sum", False))
        self._decimal_places.setValue(self._config.get("decimal_places", 2))
        self._timeout.setValue(self._config.get("timeout_seconds", 120))
        self._algorithm_mode.setCurrentText(self._config.get("algorithm_mode", "clean"))
        self._include_formula_units.setChecked(self._config.get("include_formula_units", False))
        self._include_defect.setChecked(self._config.get("include_defect", True))
        self._include_parameters.setChecked(self._config.get("include_parameters", True))
        self._batch_size.setCurrentText(str(self._config.get("batch_size", "auto")))
        self._zoom_step.setValue(float(self._config.get("chart.zoom_step", 1.2)))
        self._theme.setCurrentText(self._config.get("theme", "dark"))
        self._chart_theme.setCurrentText(self._config.get("chart_theme", "dark"))
        self._language.setCurrentText(self._config.get("language", "ru"))
        self._apply_qss()

    # ── Toast ─────────────────────────────────────────────

    def _show_toast(self, msg: str) -> None:
        self._toast.setText(msg)
        self._toast.adjustSize()
        self._toast.move(
            self.width() - self._toast.width() - 24,
            self.height() - self._toast.height() - 24,
        )
        self._toast.show()
        QTimer.singleShot(2200, self._toast.hide)
