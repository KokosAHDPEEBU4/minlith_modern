"""Страница отчётов — генерация PDF, Word, HTML с кастомизацией."""

from __future__ import annotations

import logging
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
    QCheckBox,
    QGroupBox,
)

from src.core.models import CalculationResult
from src.reports.template_builder import (
    PREDEFINED_TEMPLATES, ReportTemplate, ReportBlock, BlockType,
    template_brief, template_standard, template_full,
)

logger = logging.getLogger(__name__)

# All available block types for the user
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

# Available chart types
CHART_TYPES = [
    ("bar", "Столбчатая"),
    ("pie", "Круговая"),
    ("defect", "Дефект"),
    ("boxplot", "Box Plot"),
    ("heatmap", "Тепловая карта"),
    ("correlation", "Корреляция"),
    ("harker", "Harker"),
    ("qapf", "QAPF"),
    ("tas", "TAS"),
    ("radar", "Radar"),
]


class BlockEditDialog(QDialog):
    """Dialog to edit a single report block."""

    def __init__(self, block: ReportBlock, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактирование блока")
        self.setMinimumWidth(400)
        self._block = block

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Title
        self._title_edit = QLineEdit(block.title)
        form.addRow("Заголовок:", self._title_edit)

        # Text content (for TEXT blocks)
        self._text_edit = QLineEdit(block.text_content)
        self._text_edit.setVisible(block.block_type == BlockType.TEXT)
        form.addRow("Текст:", self._text_edit)

        # Chart type (for CHART blocks)
        self._chart_combo = QComboBox()
        for code, label in CHART_TYPES:
            self._chart_combo.addItem(label, code)
        self._chart_combo.setVisible(block.block_type == BlockType.CHART)
        # Set current chart type
        for i, (code, _) in enumerate(CHART_TYPES):
            if code == block.chart_type:
                self._chart_combo.setCurrentIndex(i)
                break
        form.addRow("Тип диаграммы:", self._chart_combo)

        # Chart sample index (for CHART blocks)
        self._sample_spin = QSpinBox()
        self._sample_spin.setRange(0, 100)
        self._sample_spin.setValue(block.chart_sample_idx)
        self._sample_spin.setVisible(block.block_type == BlockType.CHART)
        form.addRow("Индекс образца:", self._sample_spin)

        # Min weight percent (for MINERAL_TABLE)
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


class ReportsPage(QWidget):
    """Страница генерации отчётов с кастомизацией блоков."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[CalculationResult] = []
        self._current_template: Optional[ReportTemplate] = None

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Отчёты"))
        header.addStretch()
        layout.addLayout(header)

        # Template selection
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("Шаблон:"))
        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItems(["Краткий", "Стандартный", "Полный", "Пользовательский"])
        self._tmpl_combo.setCurrentIndex(1)
        self._tmpl_combo.currentIndexChanged.connect(self._on_template_changed)
        tmpl_row.addWidget(self._tmpl_combo)

        self._btn_load = QPushButton("Загрузить...")
        self._btn_load.setToolTip("Загрузить шаблон из JSON")
        self._btn_load.clicked.connect(self._on_load_template)
        tmpl_row.addWidget(self._btn_load)

        self._btn_save = QPushButton("Сохранить...")
        self._btn_save.setToolTip("Сохранить текущий шаблон в JSON")
        self._btn_save.clicked.connect(self._on_save_template)
        tmpl_row.addWidget(self._btn_save)

        tmpl_row.addStretch()
        layout.addLayout(tmpl_row)

        # Splitter: block list + block editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: block list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QHBoxLayout()
        list_label.addWidget(QLabel("Блоки отчёта:"))
        list_label.addStretch()
        left_layout.addLayout(list_label)

        self._block_list = QListWidget()
        self._block_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._block_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._block_list.model().rowsMoved.connect(self._on_blocks_reordered)
        left_layout.addWidget(self._block_list)

        # Block control buttons
        block_btns = QHBoxLayout()

        self._btn_add_block = QPushButton("+ Добавить")
        self._btn_add_block.clicked.connect(self._on_add_block)
        block_btns.addWidget(self._btn_add_block)

        self._btn_edit_block = QPushButton("Редактировать")
        self._btn_edit_block.clicked.connect(self._on_edit_block)
        block_btns.addWidget(self._btn_edit_block)

        self._btn_remove_block = QPushButton("- Удалить")
        self._btn_remove_block.clicked.connect(self._on_remove_block)
        block_btns.addWidget(self._btn_remove_block)

        self._btn_up = QPushButton("▲")
        self._btn_up.setToolTip("Переместить вверх")
        self._btn_up.clicked.connect(self._on_move_up)
        block_btns.addWidget(self._btn_up)

        self._btn_down = QPushButton("▼")
        self._btn_down.setToolTip("Переместить вниз")
        self._btn_down.clicked.connect(self._on_move_down)
        block_btns.addWidget(self._btn_down)

        left_layout.addLayout(block_btns)

        splitter.addWidget(left)

        # Right: block details
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("Предпросмотр:"))
        self._preview = QListWidget()
        self._preview.setMaximumHeight(200)
        right_layout.addWidget(self._preview)

        # Add block type selector
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Тип блока:"))
        self._block_type_combo = QComboBox()
        for bt, label in BLOCK_TYPES:
            self._block_type_combo.addItem(label, bt)
        add_row.addWidget(self._block_type_combo)
        add_row.addStretch()
        right_layout.addLayout(add_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Export buttons
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

        # Initialize with standard template
        self._on_template_changed(1)

    def set_results(self, results: list[CalculationResult]) -> None:
        self._results = results

    def _on_template_changed(self, index: int) -> None:
        if index == 0:
            self._current_template = template_brief()
        elif index == 1:
            self._current_template = template_standard()
        elif index == 2:
            self._current_template = template_full()
        else:
            # Custom — start with standard
            if self._current_template is None:
                self._current_template = template_standard()
        self._refresh_block_list()

    def _refresh_block_list(self) -> None:
        self._block_list.clear()
        if not self._current_template:
            return
        for i, block in enumerate(self._current_template.blocks):
            type_label = dict(BLOCK_TYPES).get(block.block_type, block.block_type.value)
            title = block.title or block.block_type.value
            chart_info = f" [{block.chart_type}]" if block.block_type == BlockType.CHART else ""
            self._block_list.addItem(f"{i+1}. {type_label}: {title}{chart_info}")

        self._preview.clear()
        for block in self._current_template.blocks:
            self._preview.addItem(f"[{block.block_type.value}] {block.title}")

    def _on_add_block(self) -> None:
        bt = self._block_type_combo.currentData()
        block = ReportBlock(block_type=bt, title=dict(BLOCK_TYPES).get(bt, ""))
        if bt == BlockType.CHART:
            block.chart_type = "bar"
        if self._current_template is None:
            self._current_template = template_standard()
        self._current_template.blocks.append(block)
        self._tmpl_combo.setCurrentIndex(3)  # Switch to "Custom"
        self._refresh_block_list()

    def _on_edit_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0 or not self._current_template:
            return
        block = self._current_template.blocks[row]
        dlg = BlockEditDialog(block, self)
        if dlg.exec():
            self._current_template.blocks[row] = dlg.get_block()
            self._refresh_block_list()

    def _on_remove_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0 or not self._current_template:
            return
        self._current_template.blocks.pop(row)
        self._refresh_block_list()

    def _on_move_up(self) -> None:
        row = self._block_list.currentRow()
        if row <= 0 or not self._current_template:
            return
        self._current_template.move_block(row, row - 1)
        self._refresh_block_list()
        self._block_list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self._block_list.currentRow()
        if row < 0 or not self._current_template or row >= len(self._current_template.blocks) - 1:
            return
        self._current_template.move_block(row, row + 1)
        self._refresh_block_list()
        self._block_list.setCurrentRow(row + 1)

    def _on_blocks_reordered(self) -> None:
        """Handle drag-drop reorder."""
        if not self._current_template:
            return
        # Re-read order from list widget
        new_order = []
        for i in range(self._block_list.count()):
            item = self._block_list.item(i)
            text = item.text()
            # Extract block index from "1. ..."
            try:
                idx = int(text.split(".")[0]) - 1
                if 0 <= idx < len(self._current_template.blocks):
                    new_order.append(self._current_template.blocks[idx])
            except (ValueError, IndexError):
                pass
        if len(new_order) == len(self._current_template.blocks):
            self._current_template.blocks = new_order
        self._refresh_block_list()

    def _on_load_template(self) -> None:
        from pathlib import Path
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить шаблон", "",
            "JSON (*.json);;Все файлы (*)",
        )
        if not path:
            return
        try:
            self._current_template = ReportTemplate.load(Path(path))
            self._tmpl_combo.setCurrentIndex(3)  # Custom
            self._refresh_block_list()
            QMessageBox.information(self, "Шаблон", f"Шаблон загружен:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_save_template(self) -> None:
        if not self._current_template:
            return
        from pathlib import Path
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить шаблон", "my_template.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            self._current_template.save(Path(path))
            QMessageBox.information(self, "Шаблон", f"Шаблон сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _export(self, fmt: str) -> None:
        if not self._results:
            QMessageBox.information(self, "Экспорт", "Нет результатов для экспорта. Сначала выполните расчёт.")
            return

        ext_map = {"pdf": "PDF (*.pdf)", "docx": "Word (*.docx)", "html": "HTML (*.html)"}
        path, _ = QFileDialog.getSaveFileName(
            self, f"Экспорт {fmt.upper()}", f"minlith_report.{fmt}",
            ext_map.get(fmt, "Все файлы (*)"),
        )
        if not path:
            return

        try:
            from pathlib import Path
            path = Path(path)
            tmpl = self._current_template or template_standard()
            if fmt == "pdf":
                from src.reports.pdf_generator import PDFGenerator
                gen = PDFGenerator(self._results)
                gen.generate(path, tmpl)
            elif fmt == "docx":
                from src.reports.word_generator import WordGenerator
                gen = WordGenerator(self._results)
                gen.generate(path, tmpl)
            elif fmt == "html":
                from src.reports.html_generator import HTMLGenerator
                gen = HTMLGenerator(self._results)
                gen.generate(path, tmpl)

            QMessageBox.information(self, "Экспорт", f"Отчёт экспортирован:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
            logger.error("Ошибка экспорта отчёта: %s", e)
