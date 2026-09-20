"""Страница отчётов — генерация PDF, Word, HTML с кастомизацией."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QTextBrowser,
    QTextEdit,
    QAbstractItemView,
    QSizePolicy,
)

from src.core.models import CalculationResult
from src.reports.template_builder import (
    ReportTemplate, ReportBlock, BlockType,
    template_brief, template_standard, template_full,
)

logger = logging.getLogger(__name__)

BLOCK_TYPES = [
    (BlockType.HEADER, "Заголовок"),
    (BlockType.TEXT, "Текст"),
    (BlockType.OXIDE_TABLE, "Таблица оксидов"),
    (BlockType.MINERAL_TABLE, "Таблица минералов"),
    (BlockType.PARAMETERS, "Коэффициенты"),
    (BlockType.DEFECT, "Дефект"),
    (BlockType.CHART, "Диаграмма"),
    (BlockType.PAGE_BREAK, "Разрыв страницы"),
]

CHART_TYPES = [
    ("bar", "Столбчатая"), ("pie", "Круговая"), ("defect", "Дефект"),
    ("boxplot", "Box Plot"), ("heatmap", "Тепловая карта"),
    ("correlation", "Корреляция"), ("harker", "Harker"),
    ("qapf", "QAPF"), ("tas", "TAS"), ("radar", "Radar"),
]

CHART_LABELS = dict(CHART_TYPES)
BLOCK_LABELS = dict(BLOCK_TYPES)


def _block_summary(block: ReportBlock) -> str:
    type_name = BLOCK_LABELS.get(block.block_type, block.block_type.value)
    title = block.title or block.block_type.value
    extra = ""
    if block.block_type == BlockType.CHART:
        extra = f" → {CHART_LABELS.get(block.chart_type, block.chart_type)}"
    elif block.block_type == BlockType.MINERAL_TABLE and block.min_wt_percent > 0:
        extra = f" (≥{block.min_wt_percent:.0f}%)"
    return f"{type_name}: {title}{extra}"


def _build_chart_data(results: list[CalculationResult]):
    """Build ChartData from CalculationResult list."""
    import numpy as np
    from src.charts.base import ChartData

    data = ChartData()
    data.sample_names = [r.sample_name for r in results]

    mineral_fields = [
        "ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
        "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl",
    ]
    for f in mineral_fields:
        data.minerals_wt[f] = np.array([getattr(r.minerals_weight, f, 0.0) for r in results])

    oxide_fields = ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]
    for f in oxide_fields:
        data.oxides[f] = np.array([getattr(r.input_composition, f, 0.0) for r in results])

    data.rock_types = [int(r.rock_type) for r in results]

    if results and results[0].defect:
        for oxide in results[0].defect:
            data.defect[oxide] = np.array([r.defect.get(oxide, 0.0) for r in results])

    data.F_values = [r.coefficients.F for r in results]
    data.A_values = [r.coefficients.A for r in results]

    data.metadata["k_values"] = {
        "k1": [r.coefficients.k1 for r in results],
        "k2": [r.coefficients.k2 for r in results],
        "k3": [r.coefficients.k3 for r in results],
        "k4": [r.coefficients.k4 for r in results],
    }

    return data


def _render_chart_to_base64(chart_type: str, chart_data, sample_idx: int = 0) -> str | None:
    """Render a chart to base64 PNG string for HTML embedding."""
    from src.charts.built_in import BUILTIN_CHARTS
    import matplotlib.pyplot as plt

    _chart_name_map = {c.get_name().lower(): c for c in BUILTIN_CHARTS}
    # some charts have names that differ from keys
    _alias = {
        "bar": "Mineral Bar Chart",
        "pie": "Mineral Pie Chart",
        "defect": "Defect Chart",
        "boxplot": "Mineral Box Plot",
        "heatmap": "Mineral Heatmap",
        "correlation": "correlation",
        "harker": "harker",
        "qapf": "qapf",
        "tas": "tas",
        "radar": "Mineral Radar",
    }

    plugin = None
    alias_name = _alias.get(chart_type, chart_type)
    # try exact match first, then lowercase match
    plugin = _chart_name_map.get(alias_name.lower())
    if plugin is None:
        for c in BUILTIN_CHARTS:
            if c.get_name().lower() == alias_name.lower():
                plugin = c
                break

    if plugin is None:
        return None

    kwargs = {}
    if chart_type == "bar":
        kwargs = dict(stacked=True, normalized=True)
    elif chart_type in ("pie", "defect", "radar"):
        kwargs = dict(sample_idx=sample_idx)

    try:
        fig = plugin.render(chart_data, **kwargs)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("Chart preview render failed (%s): %s", chart_type, e)
        return None


class ReportsPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[CalculationResult] = []
        self._template = template_standard()
        self._is_custom = False
        self._suppress = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # ── 1. PREVIEW (top, ~40%) ──
        preview_label = QLabel("Предпросмотр отчёта")
        preview_label.setStyleSheet("font-weight: bold; font-size: 12px; padding-top: 4px;")
        root.addWidget(preview_label)

        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(False)
        self._preview.setMinimumHeight(200)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self._preview, stretch=4)

        # ── 2. TEMPLATE SELECTOR ROW ──
        tmpl_row = QHBoxLayout()
        tmpl_row.setSpacing(6)

        tmpl_row.addWidget(QLabel("Шаблон:"))
        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItems(["Краткий", "Стандартный", "Полный"])
        self._tmpl_combo.setMinimumWidth(140)
        self._tmpl_combo.currentIndexChanged.connect(self._on_preset_changed)
        tmpl_row.addWidget(self._tmpl_combo)

        self._btn_rename = QPushButton("Переименовать")
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_rename.setEnabled(False)
        tmpl_row.addWidget(self._btn_rename)

        self._btn_delete = QPushButton("Удалить")
        self._btn_delete.clicked.connect(self._on_delete_template)
        self._btn_delete.setEnabled(False)
        tmpl_row.addWidget(self._btn_delete)

        tmpl_row.addStretch()

        self._btn_load = QPushButton("Загрузить")
        self._btn_load.setToolTip("Загрузить шаблон из JSON")
        self._btn_load.clicked.connect(self._on_load_template)
        tmpl_row.addWidget(self._btn_load)

        self._btn_save = QPushButton("Сохранить")
        self._btn_save.setToolTip("Сохранить шаблон в JSON")
        self._btn_save.clicked.connect(self._on_save_template)
        tmpl_row.addWidget(self._btn_save)

        root.addLayout(tmpl_row)

        # ── 3. BOTTOM SPLITTER: block list | inline editor ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # LEFT: block list + controls
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(4)

        left_lay.addWidget(QLabel("Структура отчёта:"))

        self._block_list = QListWidget()
        self._block_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._block_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._block_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._block_list.currentRowChanged.connect(self._on_block_selected)
        self._block_list.model().rowsMoved.connect(self._on_blocks_reordered)
        left_lay.addWidget(self._block_list)

        # add row: combo + button
        add_row = QHBoxLayout()
        self._block_type_combo = QComboBox()
        for bt, label in BLOCK_TYPES:
            self._block_type_combo.addItem(label, bt)
        add_row.addWidget(self._block_type_combo, stretch=1)

        btn_add = QPushButton("+ Добавить")
        btn_add.clicked.connect(self._on_add_block)
        add_row.addWidget(btn_add)
        left_lay.addLayout(add_row)

        # remove / reorder row
        btn_row = QHBoxLayout()
        btn_remove = QPushButton("Удалить")
        btn_remove.clicked.connect(self._on_remove_block)
        btn_row.addWidget(btn_remove)

        btn_row.addStretch()

        btn_up = QPushButton("▲ Вверх")
        btn_up.setFixedWidth(80)
        btn_up.setToolTip("Переместить вверх")
        btn_up.clicked.connect(self._on_move_up)
        btn_row.addWidget(btn_up)

        btn_down = QPushButton("▼ Вниз")
        btn_down.setFixedWidth(80)
        btn_down.setToolTip("Переместить вниз")
        btn_down.clicked.connect(self._on_move_down)
        btn_row.addWidget(btn_down)

        left_lay.addLayout(btn_row)

        splitter.addWidget(left)

        # RIGHT: inline editor
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 0, 0, 0)
        right_lay.setSpacing(4)

        right_lay.addWidget(QLabel("Редактирование блока:"))

        self._editor_form = QFormLayout()
        self._editor_form.setSpacing(6)

        self._edit_title = QLineEdit()
        self._edit_title.setPlaceholderText("Заголовок блока...")
        self._edit_title.textChanged.connect(self._on_field_changed)
        self._editor_form.addRow("Заголовок:", self._edit_title)

        self._edit_text = QTextEdit()
        self._edit_text.setPlaceholderText("Текст...")
        self._edit_text.setMaximumHeight(80)
        self._edit_text.textChanged.connect(self._on_field_changed)
        self._editor_form.addRow("Текст:", self._edit_text)

        self._edit_chart_type = QComboBox()
        for code, label in CHART_TYPES:
            self._edit_chart_type.addItem(label, code)
        self._edit_chart_type.currentIndexChanged.connect(self._on_field_changed)
        self._editor_form.addRow("Тип диаграммы:", self._edit_chart_type)

        self._edit_sample_idx = QSpinBox()
        self._edit_sample_idx.setRange(0, 100)
        self._edit_sample_idx.valueChanged.connect(self._on_field_changed)
        self._editor_form.addRow("Индекс образца:", self._edit_sample_idx)

        self._edit_min_wt = QSpinBox()
        self._edit_min_wt.setRange(0, 100)
        self._edit_min_wt.setSuffix("%")
        self._edit_min_wt.valueChanged.connect(self._on_field_changed)
        self._editor_form.addRow("Мин. вес.%:", self._edit_min_wt)

        right_lay.addLayout(self._editor_form)

        self._edit_hint = QLabel("Выберите блок в списке слева")
        self._edit_hint.setWordWrap(True)
        self._edit_hint.setStyleSheet("color: #888; font-style: italic; padding: 8px;")
        right_lay.addWidget(self._edit_hint)

        right_lay.addStretch()

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, stretch=5)

        # ── 4. EXPORT BUTTONS ──
        export_row = QHBoxLayout()
        btn_pdf = QPushButton("Экспорт PDF")
        btn_pdf.clicked.connect(lambda: self._export("pdf"))
        export_row.addWidget(btn_pdf)

        btn_word = QPushButton("Экспорт Word")
        btn_word.clicked.connect(lambda: self._export("docx"))
        export_row.addWidget(btn_word)

        btn_html = QPushButton("Экспорт HTML")
        btn_html.clicked.connect(lambda: self._export("html"))
        export_row.addWidget(btn_html)

        btn_latex = QPushButton("Экспорт LaTeX")
        btn_latex.setToolTip("Таблица минерального состава в формате LaTeX (для публикаций)")
        btn_latex.clicked.connect(self._export_latex)
        export_row.addWidget(btn_latex)

        root.addLayout(export_row)

        self._refresh()

    def set_results(self, results: list[CalculationResult]) -> None:
        self._results = results
        self._refresh()

    # ── Template management ──

    def _on_preset_changed(self, index: int) -> None:
        if self._suppress:
            return
        presets = [template_brief, template_standard, template_full]
        if 0 <= index < len(presets):
            self._template = presets[index]()
            self._is_custom = False
            self._btn_rename.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._refresh()

    def _on_rename(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Переименовать шаблон", "Название:",
            text=self._template.name,
        )
        if ok and name.strip():
            self._template.name = name.strip()
            self._is_custom = True
            self._ensure_custom_combo()
            self._refresh()

    def _on_delete_template(self) -> None:
        reply = QMessageBox.question(
            self, "Удалить шаблон",
            f"Удалить шаблон '{self._template.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._template = template_standard()
            self._is_custom = False
            self._suppress = True
            self._tmpl_combo.setCurrentIndex(1)
            self._suppress = False
            self._btn_rename.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._refresh()

    def _on_load_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить шаблон", "", "JSON (*.json);;Все файлы (*)")
        if not path:
            return
        try:
            self._template = ReportTemplate.load(Path(path))
            self._is_custom = True
            self._ensure_custom_combo()
            self._refresh()
            QMessageBox.information(self, "Шаблон", f"Загружен: {self._template.name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_save_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить шаблон", f"{self._template.name}.json", "JSON (*.json)")
        if not path:
            return
        try:
            self._template.save(Path(path))
            QMessageBox.information(self, "Шаблон", f"Сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _ensure_custom_combo(self) -> None:
        self._suppress = True
        if self._is_custom and self._tmpl_combo.count() <= 3:
            self._tmpl_combo.addItem(f"★ {self._template.name}")
        if self._is_custom:
            self._tmpl_combo.setCurrentIndex(self._tmpl_combo.count() - 1)
            self._btn_rename.setEnabled(True)
            self._btn_delete.setEnabled(True)
        self._suppress = False

    # ── Block management ──

    def _on_add_block(self) -> None:
        bt = self._block_type_combo.currentData()
        block = ReportBlock(block_type=bt, title=BLOCK_LABELS.get(bt, ""))
        if bt == BlockType.CHART:
            block.chart_type = "bar"
        self._template.blocks.append(block)
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()
        self._block_list.setCurrentRow(len(self._template.blocks) - 1)

    def _on_remove_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0:
            return
        self._template.blocks.pop(row)
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()
        if self._template.blocks:
            self._block_list.setCurrentRow(min(row, len(self._template.blocks) - 1))

    def _on_move_up(self) -> None:
        row = self._block_list.currentRow()
        if row <= 0:
            return
        self._template.move_block(row, row - 1)
        self._refresh()
        self._block_list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self._block_list.currentRow()
        if row < 0 or row >= len(self._template.blocks) - 1:
            return
        self._template.move_block(row, row + 1)
        self._refresh()
        self._block_list.setCurrentRow(row + 1)

    def _on_block_selected(self, row: int) -> None:
        if self._suppress or row < 0 or row >= len(self._template.blocks):
            self._clear_editor()
            return
        block = self._template.blocks[row]
        self._show_editor(block)

    def _on_blocks_reordered(self) -> None:
        new_order = []
        for i in range(self._block_list.count()):
            item = self._block_list.item(i)
            if item is None:
                continue
            idx = self._block_list.row(item)
            if 0 <= idx < len(self._template.blocks):
                new_order.append(self._template.blocks[idx])
        if len(new_order) == len(self._template.blocks):
            self._template.blocks = new_order
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()

    # ── Inline editor ──

    def _clear_editor(self) -> None:
        self._suppress = True
        self._edit_title.clear()
        self._edit_text.clear()
        self._edit_sample_idx.setValue(0)
        self._edit_min_wt.setValue(0)
        self._set_field_visible("text", False)
        self._set_field_visible("chart", False)
        self._set_field_visible("sample", False)
        self._set_field_visible("min_wt", False)
        self._edit_hint.setVisible(True)
        self._suppress = False

    def _show_editor(self, block: ReportBlock) -> None:
        self._suppress = True
        bt = block.block_type

        self._edit_title.setText(block.title)
        self._edit_text.setPlainText(block.text_content)

        for i, (code, _) in enumerate(CHART_TYPES):
            if code == block.chart_type:
                self._edit_chart_type.setCurrentIndex(i)
                break
        self._edit_sample_idx.setValue(block.chart_sample_idx)
        self._edit_min_wt.setValue(int(block.min_wt_percent * 10))

        self._set_field_visible("text", bt == BlockType.TEXT)
        self._set_field_visible("chart", bt == BlockType.CHART)
        self._set_field_visible("sample", bt == BlockType.CHART)
        self._set_field_visible("min_wt", bt == BlockType.MINERAL_TABLE)

        hint = {
            BlockType.HEADER: "Заголовок отчёта",
            BlockType.TEXT: "Произвольный текст-пояснение",
            BlockType.OXIDE_TABLE: "Таблица входных оксидов",
            BlockType.MINERAL_TABLE: "Рассчитанный минеральный состав (вес.%)",
            BlockType.PARAMETERS: "Коэффициенты расчёта (F, A, k1–k4)",
            BlockType.DEFECT: "Остатки (дефект) по оксидам",
            BlockType.CHART: "Диаграмма — выберите тип и образец",
            BlockType.PAGE_BREAK: "Разрыв страницы — разделяет разделы",
        }
        self._edit_hint.setText(hint.get(bt, ""))
        self._edit_hint.setStyleSheet("color: #888; font-style: italic; padding: 4px; font-size: 11px;")
        self._edit_hint.setVisible(True)

        self._suppress = False

    def _set_field_visible(self, name: str, visible: bool) -> None:
        widgets = {
            "text": self._edit_text,
            "chart": self._edit_chart_type,
            "sample": self._edit_sample_idx,
            "min_wt": self._edit_min_wt,
        }
        w = widgets.get(name)
        if w is None:
            return
        w.setVisible(visible)
        for i in range(self._editor_form.rowCount()):
            label_item = self._editor_form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self._editor_form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if field_item and field_item.widget() is w:
                if label_item and label_item.widget():
                    label_item.widget().setVisible(visible)
                break

    def _on_field_changed(self) -> None:
        if self._suppress:
            return
        row = self._block_list.currentRow()
        if row < 0 or row >= len(self._template.blocks):
            return
        block = self._template.blocks[row]
        block.title = self._edit_title.text()
        block.text_content = self._edit_text.toPlainText()
        if block.block_type == BlockType.CHART:
            block.chart_type = self._edit_chart_type.currentData() or "bar"
            block.chart_sample_idx = self._edit_sample_idx.value()
        if block.block_type == BlockType.MINERAL_TABLE:
            block.min_wt_percent = self._edit_min_wt.value() / 10.0
        self._is_custom = True
        self._ensure_custom_combo()
        item = self._block_list.item(row)
        if item:
            item.setText(f"{row+1}. {_block_summary(block)}")
        self._refresh_preview()

    # ── Refresh ──

    def _refresh(self) -> None:
        self._suppress = True
        current_row = self._block_list.currentRow()

        self._block_list.clear()
        for i, block in enumerate(self._template.blocks):
            self._block_list.addItem(f"{i+1}. {_block_summary(block)}")

        if 0 <= current_row < len(self._template.blocks):
            self._block_list.setCurrentRow(current_row)
        elif self._template.blocks:
            self._block_list.setCurrentRow(0)
        else:
            self._clear_editor()

        self._suppress = False
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._results:
            blocks_html = "".join(
                f"<li>{_block_summary(b)}</li>" for b in self._template.blocks
            )
            html = f"""
            <html><body style="font-family: Segoe UI, Arial, sans-serif; padding: 12px; color: #555;">
            <div style="color: #999; font-size: 11px;">{self._template.name} — {len(self._template.blocks)} блоков</div>
            <p style="color: #888; font-style: italic;">Нет данных. Выполните расчёт.</p>
            <ol style="font-size: 12px;">{blocks_html}</ol>
            </body></html>
            """
        else:
            from src.reports.html_generator import _block_html
            from datetime import datetime

            chart_data = _build_chart_data(self._results)

            parts = []
            for block in self._template.blocks:
                if block.block_type == BlockType.CHART:
                    img_src = _render_chart_to_base64(
                        block.chart_type, chart_data, block.chart_sample_idx)
                    if img_src:
                        title = block.title or CHART_LABELS.get(block.chart_type, block.chart_type)
                        parts.append(
                            f'<h2>{title}</h2>'
                            f'<div style="text-align:center; margin: 8px 0;">'
                            f'<img src="{img_src}" style="max-width:100%; height:auto;">'
                            f'</div>'
                        )
                    else:
                        parts.append(f'<p><em>Диаграмма «{block.chart_type}» не построена.</em></p>')
                else:
                    parts.append(_block_html(block, self._results))

            html = f"""
            <html><head><style>
            body {{ font-family: Segoe UI, Arial, sans-serif; margin: 8px; background: #fafafa; color: #333; font-size: 12px; }}
            h1 {{ color: #1e1e2e; border-bottom: 2px solid #4a9eff; padding-bottom: 6px; font-size: 15px; }}
            h2 {{ color: #45475a; margin-top: 14px; font-size: 13px; }}
            table {{ border-collapse: collapse; width: auto; max-width: 100%; margin: 6px 0; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.08); font-size: 11px; }}
            th {{ background: #1e1e2e; color: white; padding: 5px 7px; text-align: left; }}
            td {{ padding: 3px 7px; border-bottom: 1px solid #eee; }}
            tr:nth-child(even) {{ background: #f8f9fa; }}
            .negative {{ color: #e74c3c; }}
            .param {{ font-weight: bold; color: #4a9eff; }}
            .footer {{ margin-top: 16px; padding-top: 6px; border-top: 1px solid #ddd; font-size: 10px; color: #aaa; }}
            </style></head><body>
            <h1>MINLITH Report</h1>
            {''.join(parts)}
            <div class="footer">{self._template.name} — {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
            </body></html>
            """
        self._preview.setHtml(html)

    # ── Export ──

    def _export(self, fmt: str) -> None:
        if not self._results:
            QMessageBox.information(self, "Экспорт",
                                    "Нет результатов. Сначала выполните расчёт.")
            return

        ext_map = {"pdf": "PDF (*.pdf)", "docx": "Word (*.docx)", "html": "HTML (*.html)"}
        path, _ = QFileDialog.getSaveFileName(
            self, f"Экспорт {fmt.upper()}", f"minlith_report.{fmt}",
            ext_map.get(fmt, "Все файлы (*)"))
        if not path:
            return

        try:
            path = Path(path)
            if fmt == "pdf":
                from src.reports.pdf_generator import PDFGenerator
                PDFGenerator(self._results).generate(path, self._template)
            elif fmt == "docx":
                from src.reports.word_generator import WordGenerator
                WordGenerator(self._results).generate(path, self._template)
            elif fmt == "html":
                from src.reports.html_generator import HTMLGenerator
                HTMLGenerator(self._results).generate(path, self._template)
            QMessageBox.information(self, "Экспорт", f"Готово:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logger.error("Export error: %s", e)

    def _export_latex(self) -> None:
        if not self._results:
            QMessageBox.information(self, "Экспорт",
                                    "Нет результатов. Сначала выполните расчёт.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт LaTeX", "minlith_report.tex", "LaTeX (*.tex)")
        if not path:
            return

        try:
            from src.reports.latex_exporter import LaTeXExporter
            LaTeXExporter(self._results).export(Path(path))
            QMessageBox.information(self, "Экспорт", f"Готово:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logger.error("LaTeX export error: %s", e)
