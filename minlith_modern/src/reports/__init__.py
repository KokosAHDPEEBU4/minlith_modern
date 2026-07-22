"""Reports package — PDF, Word, HTML generation."""

from src.reports.template_builder import ReportTemplate, ReportBlock, BlockType, PREDEFINED_TEMPLATES
from src.reports.pdf_generator import PDFGenerator
from src.reports.word_generator import WordGenerator
from src.reports.html_generator import HTMLGenerator

__all__ = [
    "ReportTemplate", "ReportBlock", "BlockType", "PREDEFINED_TEMPLATES",
    "PDFGenerator", "WordGenerator", "HTMLGenerator",
]
