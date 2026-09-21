"""Reports package — PDF, Word, HTML generation."""

from src.reports.html_generator import HTMLGenerator
from src.reports.pdf_generator import PDFGenerator
from src.reports.template_builder import (
    PREDEFINED_TEMPLATES,
    BlockType,
    ReportBlock,
    ReportTemplate,
)
from src.reports.word_generator import WordGenerator

__all__ = [
    "ReportTemplate", "ReportBlock", "BlockType", "PREDEFINED_TEMPLATES",
    "PDFGenerator", "WordGenerator", "HTMLGenerator",
]
