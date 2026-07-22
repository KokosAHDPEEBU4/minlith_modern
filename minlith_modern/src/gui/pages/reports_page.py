"""Reports page — generate PDF, Word, HTML reports."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.models import CalculationResult
from src.reports.template_builder import (
    PREDEFINED_TEMPLATES, ReportTemplate, template_brief, template_standard, template_full,
)

logger = logging.getLogger(__name__)


class ReportsPage(QWidget):
    """Page for generating reports in PDF, Word, HTML."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[CalculationResult] = []

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Reports"))
        header.addStretch()
        layout.addLayout(header)

        # Template selection
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("Template:"))
        self._tmpl_combo = QComboBox()
        self._tmpl_combo.addItems(["Brief", "Standard", "Full"])
        self._tmpl_combo.setCurrentIndex(1)
        tmpl_row.addWidget(self._tmpl_combo)
        tmpl_row.addStretch()
        layout.addLayout(tmpl_row)

        # Template preview
        self._preview = QListWidget()
        self._preview.setMaximumHeight(150)
        layout.addWidget(self._preview)
        self._tmpl_combo.currentIndexChanged.connect(self._update_preview)
        self._update_preview()

        # Export buttons
        btn_row = QHBoxLayout()

        self._btn_pdf = QPushButton("Export PDF")
        self._btn_pdf.clicked.connect(lambda: self._export("pdf"))
        btn_row.addWidget(self._btn_pdf)

        self._btn_word = QPushButton("Export Word")
        self._btn_word.clicked.connect(lambda: self._export("docx"))
        btn_row.addWidget(self._btn_word)

        self._btn_html = QPushButton("Export HTML")
        self._btn_html.clicked.connect(lambda: self._export("html"))
        btn_row.addWidget(self._btn_html)

        layout.addLayout(btn_row)
        layout.addStretch()

    def set_results(self, results: list[CalculationResult]) -> None:
        self._results = results

    def _get_template(self) -> ReportTemplate:
        idx = self._tmpl_combo.currentIndex()
        if idx == 0:
            return template_brief()
        elif idx == 2:
            return template_full()
        return template_standard()

    def _update_preview(self) -> None:
        self._preview.clear()
        tmpl = self._get_template()
        for block in tmpl.blocks:
            self._preview.addItem(f"[{block.block_type.value}] {block.title}")

    def _export(self, fmt: str) -> None:
        if not self._results:
            QMessageBox.information(self, "Export", "No results to export. Calculate first.")
            return

        ext_map = {"pdf": "PDF (*.pdf)", "docx": "Word (*.docx)", "html": "HTML (*.html)"}
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", f"minlith_report.{fmt}",
            ext_map.get(fmt, "All Files (*)"),
        )
        if not path:
            return

        try:
            tmpl = self._get_template()
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

            QMessageBox.information(self, "Export", f"Report exported:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            logger.error("Report export failed: %s", e)
