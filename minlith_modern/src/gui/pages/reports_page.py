"""Страница отчётов — генерация PDF, Word, HTML с кастомизацией."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QGroupBox,
    QAbstractItemView,
    QTextBrowser,
)
from PyQt6.QtCore import Qt

from src.core.models import CalculationResult
from src.reports.template_builder import (
    PREDEFINED_TEMPLATES, ReportTemplate, ReportBlock, BlockType,
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


class BlockEditDialog(QDialog):
    def __init__(self, block: ReportBlock, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактирование блока")
        self.setMinimumWidth(400)
        self._block = block

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._title_edit = QLineEdit(block.title)
        form.addRow("Заголовок:", self._title_edit)

        self._text_edit = QLineEdit(block.text_content)
        self._text_edit.setVisible(block.block_type == BlockType.TEXT)
        form.addRow("Текст:", self._text_edit)

        self._chart_combo = QComboBox()
        for code, label in CHART_TYPES:
            self._chart_combo.addItem(label, code)
        self._chart_combo.setVisible(block.block_type == BlockType.CHART)
        for i, (code, _) in enumerate(CHART_TYPES):
            if code == block.chart_type:
                self._chart_combo.setCurrentIndex(i)
                break
        form.addRow("Тип диаграммы:", self._chart_combo)

        self._sample_spin = QSpinBox()
        self._sample_spin.setRange(0, 100)
        self._sample_spin.setValue(block.chart_sample_idx)
        self._sample_spin.setVisible(block.block_type == BlockType.CHART)
        form.addRow("Индекс образца:", self._sample_spin)

        self._min_wt = QSpinBox()
        self._min_wt.setRange(0, 100)
        self._min_wt.setValue(int(block.min_wt_percent * 10))
        self._min_wt.setSuffix("%")
        self._min_wt.setVisible(block.block_type == BlockType.MINERAL_TABLE)
        form.addRow("Мин. вес.%:", self._min_wt)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_block(self) -> ReportBlock:
        self._block.title = self._title_edit.text()
        self._block.text_content = self._text_edit.text()
        if self._block.block_type == BlockType.CHART:
            self._block.chart_type = self._chart_combo.currentData()
            self._block.chart_sample_idx = self._sample_spin.value()
        if self._block.block_type == BlockType.MINERAL_TABLE:
            self._block.min_wt_percent = self._min_wt.value() / 10.0
        return self._block


def _block_summary(block: ReportBlock) -> str:
    """One-line summary of a block for display."""
    type_labels = dict(BLOCK_TYPES)
    type_name = type_labels.get(block.block_type, block.block_type.value)
    title = block.title or block.block_type.value
    extra = ""
    if block.block_type == BlockType.CHART:
        chart_label = dict(CHART_TYPES).get(block.chart_type, block.chart_type)
        extra = f" → {chart_label}"
    elif block.block_type == BlockType.MINERAL_TABLE and block.min_wt_percent > 0:
        extra = f" (≥{block.min_wt_percent:.0f}%)"
    return f"[{type_name}] {title}{extra}"


class ReportsPage(QWidget):
    """Страница отчётов с визуальным конструктором."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[CalculationResult] = []
        self._template = template_standard()
        self._custom_templates: dict[str, ReportTemplate] = {}
        self._is_custom = False

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Отчёты"))
        header.addStretch()
        layout.addLayout(header)

        # ── Template selector row ──
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("Шаблон:"))
        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItems(["Краткий", "Стандартный", "Полный"])
        self._tmpl_combo.setMinimumWidth(150)
        self._tmpl_combo.currentIndexChanged.connect(self._on_preset_changed)
        tmpl_row.addWidget(self._tmpl_combo)

        self._btn_rename = QPushButton("Переименовать")
        self._btn_rename.setToolTip("Переименовать пользовательский шаблон")
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_rename.setEnabled(False)
        tmpl_row.addWidget(self._btn_rename)

        self._btn_delete = QPushButton("Удалить")
        self._btn_delete.setToolTip("Удалить пользовательский шаблон")
        self._btn_delete.clicked.connect(self._on_delete_template)
        self._btn_delete.setEnabled(False)
        tmpl_row.addWidget(self._btn_delete)

        tmpl_row.addStretch()

        self._btn_load = QPushButton("Загрузить JSON")
        self._btn_load.clicked.connect(self._on_load_template)
        tmpl_row.addWidget(self._btn_load)

        self._btn_save = QPushButton("Сохранить JSON")
        self._btn_save.clicked.connect(self._on_save_template)
        tmpl_row.addWidget(self._btn_save)

        layout.addLayout(tmpl_row)

        # ── Main content: left=block list, right=preview+add ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: block list with controls ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Структура отчёта:"))

        self._block_list = QListWidget()
        self._block_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._block_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._block_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._block_list.model().rowsMoved.connect(self._on_blocks_reordered)
        self._block_list.itemDoubleClicked.connect(self._on_edit_block)
        left_layout.addWidget(self._block_list)

        # Control buttons
        ctrl = QHBoxLayout()

        self._btn_add = QPushButton("+ Добавить")
        self._btn_add.clicked.connect(self._on_add_block)
        ctrl.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Редактировать")
        self._btn_edit.clicked.connect(self._on_edit_block)
        ctrl.addWidget(self._btn_edit)

        self._btn_remove = QPushButton("- Удалить")
        self._btn_remove.clicked.connect(self._on_remove_block)
        ctrl.addWidget(self._btn_remove)

        left_layout.addLayout(ctrl)

        order = QHBoxLayout()
        self._btn_up = QPushButton("▲ Вверх")
        self._btn_up.clicked.connect(self._on_move_up)
        order.addWidget(self._btn_up)

        self._btn_down = QPushButton("▼ Вниз")
        self._btn_down.clicked.connect(self._on_move_down)
        order.addWidget(self._btn_down)

        order.addStretch()
        left_layout.addLayout(order)

        splitter.addWidget(left)

        # ── RIGHT: preview + add block ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Add block section
        add_group = QGroupBox("Добавить блок")
        add_form = QHBoxLayout(add_group)

        self._block_type_combo = QComboBox()
        for bt, label in BLOCK_TYPES:
            self._block_type_combo.addItem(label, bt)
        add_form.addWidget(self._block_type_combo)

        self._btn_add_confirm = QPushButton("+ Добавить")
        self._btn_add_confirm.clicked.connect(self._on_add_block)
        add_form.addWidget(self._btn_add_confirm)

        right_layout.addWidget(add_group)

        # Preview
        right_layout.addWidget(QLabel("Предпросмотр отчёта:"))
        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(False)
        self._preview.setMinimumHeight(300)
        right_layout.addWidget(self._preview)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # ── Export buttons ──
        btn_row = QHBoxLayout()

        self._btn_pdf = QPushButton("Экспорт PDF")
        self._btn_pdf.clicked.connect(lambda: self._export("pdf"))
        btn_row.addWidget(self._btn_pdf)

        self._btn_word = QPushButton("Экспорт Word")
        self._btn_word.clicked.connect(lambda: self._export("docx"))
        btn_row.addWidget(self._btn_word)

        self._btn_html = QPushButton("Экспорт HTML")
        self._btn_html.clicked.connect(lambda: self._export("html"))
        btn_row.addWidget(self._btn_html)

        layout.addLayout(btn_row)

        self._refresh()

    def set_results(self, results: list[CalculationResult]) -> None:
        self._results = results

    # ── Template management ──

    def _on_preset_changed(self, index: int) -> None:
        if index == 0:
            self._template = template_brief()
            self._is_custom = False
        elif index == 1:
            self._template = template_standard()
            self._is_custom = False
        elif index == 2:
            self._template = template_full()
            self._is_custom = False
        self._btn_rename.setEnabled(False)
        self._btn_delete.setEnabled(False)
        self._refresh()

    def _on_rename(self) -> None:
        name, ok = __import__("PyQt6.QtWidgets", fromlist=["QInputDialog"]).QInputDialog.getText(
            self, "Переименовать шаблон", "Название:",
            text=self._template.name,
        )
        if ok and name.strip():
            self._template.name = name.strip()
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
            self._tmpl_combo.setCurrentIndex(1)
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
            self._tmpl_combo.blockSignals(True)
            self._tmpl_combo.clear()
            self._tmpl_combo.addItems(["Краткий", "Стандартный", "Полный"])
            self._tmpl_combo.addItem(f"📋 {self._template.name}")
            self._tmpl_combo.setCurrentIndex(3)
            self._tmpl_combo.blockSignals(False)
            self._btn_rename.setEnabled(True)
            self._btn_delete.setEnabled(True)
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

    # ── Block management ──

    def _on_add_block(self) -> None:
        bt = self._block_type_combo.currentData()
        type_labels = dict(BLOCK_TYPES)
        block = ReportBlock(block_type=bt, title=type_labels.get(bt, ""))
        if bt == BlockType.CHART:
            block.chart_type = "bar"
        self._template.blocks.append(block)
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()
        self._block_list.setCurrentRow(len(self._template.blocks) - 1)

    def _on_edit_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0:
            return
        block = self._template.blocks[row]
        dlg = BlockEditDialog(block, self)
        if dlg.exec():
            self._template.blocks[row] = dlg.get_block()
            self._is_custom = True
            self._ensure_custom_combo()
            self._refresh()

    def _on_remove_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0:
            return
        self._template.blocks.pop(row)
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()

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

    def _on_blocks_reordered(self) -> None:
        if not self._template:
            return
        new_order = []
        for i in range(self._block_list.count()):
            item = self._block_list.item(i)
            text = item.text()
            try:
                idx = int(text.split(".")[0]) - 1
                if 0 <= idx < len(self._template.blocks):
                    new_order.append(self._template.blocks[idx])
            except (ValueError, IndexError):
                pass
        if len(new_order) == len(self._template.blocks):
            self._template.blocks = new_order
        self._is_custom = True
        self._ensure_custom_combo()
        self._refresh()

    def _ensure_custom_combo(self) -> None:
        """Make sure 'Custom' is in the combo and selected."""
        if self._is_custom and self._tmpl_combo.count() == 3:
            self._tmpl_combo.addItem(f"📋 {self._template.name}")
        if self._is_custom:
            self._tmpl_combo.setCurrentIndex(self._tmpl_combo.count() - 1)
            self._btn_rename.setEnabled(True)
            self._btn_delete.setEnabled(True)

    def _refresh(self) -> None:
        """Refresh block list and preview."""
        self._block_list.clear()
        for i, block in enumerate(self._template.blocks):
            summary = _block_summary(block)
            self._block_list.addItem(f"{i+1}. {summary}")

        # Generate HTML preview
        html = self._generate_preview_html()
        self._preview.setHtml(html)

    def _generate_preview_html(self) -> str:
        """Generate a preview HTML of the current template."""
        from datetime import datetime

        if not self._results:
            return f"""
            <html><body style="font-family: Segoe UI, Arial, sans-serif; padding: 20px; color: #666;">
            <h2 style="color: #1e1e2e;">{self._template.name}</h2>
            <p><em>Нет данных для предпросмотра. Выполните расчёт на вкладке «Расчёт».</em></p>
            <hr>
            <h3>Структура отчёта:</h3>
            <ol>
            {''.join(f'<li>{_block_summary(b)}</li>' for b in self._template.blocks)}
            </ol>
            </body></html>
            """

        from src.reports.html_generator import _block_html

        block_htmls = []
        for block in self._template.blocks:
            block_htmls.append(_block_html(block, self._results))

        return f"""
        <html><head><style>
        body {{ font-family: Segoe UI, Arial, sans-serif; margin: 10px; background: #fafafa; color: #333; }}
        h1 {{ color: #1e1e2e; border-bottom: 2px solid #4a9eff; padding-bottom: 8px; font-size: 16px; }}
        h2 {{ color: #45475a; margin-top: 16px; font-size: 14px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 8px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 12px; }}
        th {{ background: #1e1e2e; color: white; padding: 6px 8px; text-align: left; }}
        td {{ padding: 4px 8px; border-bottom: 1px solid #eee; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        .negative {{ color: #e74c3c; }}
        .param {{ font-weight: bold; color: #4a9eff; }}
        .footer {{ margin-top: 20px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 10px; color: #999; }}
        </style></head><body>
        <h1>MINLITH Report</h1>
        {''.join(block_htmls)}
        <div class="footer">Preview &mdash; {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
        </body></html>
        """

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
