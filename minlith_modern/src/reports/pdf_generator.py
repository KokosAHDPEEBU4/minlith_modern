"""PDF report generator using reportlab."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.core.models import CalculationResult
from src.reports.chart_renderer import render_chart_png
from src.reports.template_builder import BlockType, ReportBlock, ReportTemplate

logger = logging.getLogger(__name__)

# Color palette
HEADER_BG = colors.HexColor("#1e1e2e")
HEADER_FG = colors.white
ROW_ALT = colors.HexColor("#f5f5f5")
ACCENT = colors.HexColor("#4a9eff")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=18, spaceAfter=12, textColor=colors.HexColor("#1e1e2e"),
    ))
    styles.add(ParagraphStyle(
        "BlockTitle", parent=styles["Heading2"],
        fontSize=13, spaceAfter=6, textColor=colors.HexColor("#333333"),
    ))
    styles.add(ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey,
    ))
    return styles


class PDFGenerator:
    """Generate PDF reports from CalculationResult(s)."""

    def __init__(self, results: list[CalculationResult]) -> None:
        self._results = results
        self._styles = _build_styles()

    def generate(
        self,
        path: Path,
        template: ReportTemplate | None = None,
        title: str = "MINLITH Report",
    ) -> None:
        doc = SimpleDocTemplate(
            str(path), pagesize=A4,
            leftMargin=15 * mm, rightMargin=15 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm,
        )

        story = []
        blocks = template.blocks if template else self._default_blocks()

        for block in blocks:
            elements = self._render_block(block)
            story.extend(elements)

        # Add page numbers
        def add_page_number(canvas, doc):
            page_num = canvas.getPageNumber()
            text = f"MINLITH Report — стр. {page_num}"
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawCentredString(A4[0] / 2, 10 * mm, text)
            canvas.restoreState()

        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        logger.info("PDF exported: %s", path)

    def _default_blocks(self) -> list[ReportBlock]:
        return [
            ReportBlock(BlockType.HEADER, title="MINLITH — Отчёт"),
            ReportBlock(BlockType.MINERAL_TABLE, title="Минеральный состав"),
            ReportBlock(BlockType.PARAMETERS, title="Коэффициенты"),
        ]

    def _render_block(self, block: ReportBlock) -> list:
        elements = []

        if block.block_type == BlockType.HEADER:
            elements.append(Paragraph(block.title or "MINLITH Report", self._styles["ReportTitle"]))
            elements.append(Spacer(1, 6 * mm))

        elif block.block_type == BlockType.MINERAL_TABLE:
            if block.title:
                elements.append(Paragraph(block.title, self._styles["BlockTitle"]))
            elements.append(self._build_mineral_table(block))
            elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.OXIDE_TABLE:
            if block.title:
                elements.append(Paragraph(block.title, self._styles["BlockTitle"]))
            elements.append(self._build_oxide_table())
            elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.PARAMETERS:
            if block.title:
                elements.append(Paragraph(block.title, self._styles["BlockTitle"]))
            elements.append(self._build_parameters_table())
            elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.DEFECT:
            if block.title:
                elements.append(Paragraph(block.title, self._styles["BlockTitle"]))
            elements.append(self._build_defect_table())
            elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.TEXT:
            if block.text_content:
                elements.append(Paragraph(block.text_content, self._styles["Normal"]))
                elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.CHART:
            img_data = self._render_chart_image(block)
            if img_data:
                if block.title:
                    elements.append(Paragraph(block.title, self._styles["BlockTitle"]))
                img = Image(io.BytesIO(img_data), width=160 * mm, height=100 * mm)
                elements.append(img)
                elements.append(Spacer(1, 4 * mm))

        elif block.block_type == BlockType.PAGE_BREAK:
            from reportlab.platypus import PageBreak
            elements.append(PageBreak())

        return elements

    def _build_mineral_table(self, block: ReportBlock) -> Table:
        minerals = [
            ("Ab", "ab"), ("An", "an"), ("Or", "or_"), ("Q", "q"),
            ("Ill", "ill"), ("Chl", "chl"), ("Kn", "kn"), ("Mm", "mm"),
            ("Gb", "gb"), ("Ap", "ap"), ("Cc", "cc"), ("Dl", "dl"),
            ("Ank", "ank"), ("Rch", "rch"), ("Sd", "sd"), ("Srp", "srp"),
            ("Mst", "mst"), ("Ht", "ht"), ("Prl", "prl"),
        ]

        # Filter by min_wt_percent if set
        if block.min_wt_percent > 0:
            filtered = []
            for code, field in minerals:
                max_wt = max(
                    (getattr(r.minerals_weight, field, 0.0) for r in self._results),
                    default=0.0,
                )
                if max_wt >= block.min_wt_percent:
                    filtered.append((code, field))
            minerals = filtered

        header = ["Mineral"] + [r.sample_name for r in self._results]
        data = [header]

        for code, field in minerals:
            row = [code]
            for r in self._results:
                val = getattr(r.minerals_weight, field, 0.0)
                row.append(f"{val:.2f}")
            data.append(row)

        # Sum row
        data.append(["Σ"] + [f"{sum(r.minerals_weight.__dict__.values()):.1f}" for r in self._results])

        table = Table(data, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ROW_ALT]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(style))
        return table

    def _build_oxide_table(self) -> Table:
        oxides = [
            ("SiO₂", "sio2"), ("TiO₂", "tio2"), ("Al₂O₃", "al2o3"),
            ("Fe₂O₃", "fe2o3"), ("FeO", "feo"), ("MgO", "mgo"),
            ("CaO", "cao"), ("Na₂O", "na2o"), ("K₂O", "k2o"),
            ("P₂O₅", "p2o5"), ("MnO", "mno"),
        ]

        header = ["Oxide"] + [r.sample_name for r in self._results]
        data = [header]
        for label, field in oxides:
            row = [label] + [f"{getattr(r.input_composition, field, 0.0):.2f}" for r in self._results]
            data.append(row)

        table = Table(data, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(style))
        return table

    def _build_parameters_table(self) -> Table:
        header = ["Parameter"] + [r.sample_name for r in self._results]
        data = [header]
        for label, field in [("Type", "rock_type"), ("F", "F"), ("A", "A"),
                              ("k1", "k1"), ("k2", "k2"), ("k3", "k3"), ("k4", "k4")]:
            row = [label]
            for r in self._results:
                if field == "rock_type":
                    row.append(str(int(r.rock_type)))
                else:
                    row.append(f"{getattr(r.coefficients, field, 0.0):.4f}")
            data.append(row)

        table = Table(data, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(style))
        return table

    def _build_defect_table(self) -> Table:
        if not self._results or not self._results[0].defect:
            return Table([["No defect data"]])

        oxides = list(self._results[0].defect.keys())
        header = ["Δ Oxide"] + [r.sample_name for r in self._results]
        data = [header]
        for oxide in oxides:
            row = [oxide] + [f"{r.defect.get(oxide, 0.0):.2f}" for r in self._results]
            data.append(row)

        table = Table(data, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(style))
        return table

    def _render_chart_image(self, block: ReportBlock) -> bytes | None:
        """Render a chart to PNG bytes for embedding."""
        return render_chart_png(
            block.chart_type, self._results,
            sample_idx=block.chart_sample_idx, dpi=150,
        )
