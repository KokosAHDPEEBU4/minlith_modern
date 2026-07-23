"""Word report generator using python-docx."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from src.core.models import CalculationResult
from src.reports.template_builder import ReportTemplate, ReportBlock, BlockType

logger = logging.getLogger(__name__)


class WordGenerator:
    """Generate Word (.docx) reports from CalculationResult(s)."""

    def __init__(self, results: list[CalculationResult]) -> None:
        self._results = results

    def generate(
        self,
        path: Path,
        template: Optional[ReportTemplate] = None,
        title: str = "MINLITH Report",
    ) -> None:
        doc = Document()
        doc.core_properties.title = title

        blocks = template.blocks if template else self._default_blocks()

        for block in blocks:
            self._render_block(doc, block)

        doc.save(str(path))
        logger.info("Word exported: %s", path)

    def _default_blocks(self) -> list[ReportBlock]:
        return [
            ReportBlock(BlockType.HEADER, title="MINLITH Report"),
            ReportBlock(BlockType.TEXT, text_content=self._build_summary_text()),
            ReportBlock(BlockType.OXIDE_TABLE, title="Input Composition"),
            ReportBlock(BlockType.MINERAL_TABLE, title="Mineral Composition"),
            ReportBlock(BlockType.PARAMETERS, title="Coefficients"),
            ReportBlock(BlockType.DEFECT, title="Defect (Oxide Residuals)"),
        ]

    def _build_summary_text(self) -> str:
        lines = [f"Samples: {len(self._results)}"]
        for r in self._results:
            lines.append(
                f"  {r.sample_name}: Type {int(r.rock_type)}, "
                f"F={r.coefficients.F:.3f}, Ab={r.minerals_weight.ab:.1f}%, "
                f"Q={r.minerals_weight.q:.1f}%"
            )
        return "\n".join(lines)

    def _render_block(self, doc: Document, block: ReportBlock) -> None:
        if block.block_type == BlockType.HEADER:
            heading = doc.add_heading(block.title or "MINLITH Report", level=0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        elif block.block_type == BlockType.MINERAL_TABLE:
            if block.title:
                doc.add_heading(block.title, level=1)
            self._add_mineral_table(doc, block)
            doc.add_paragraph()

        elif block.block_type == BlockType.OXIDE_TABLE:
            if block.title:
                doc.add_heading(block.title, level=1)
            self._add_oxide_table(doc)
            doc.add_paragraph()

        elif block.block_type == BlockType.PARAMETERS:
            if block.title:
                doc.add_heading(block.title, level=1)
            self._add_parameters_table(doc)
            doc.add_paragraph()

        elif block.block_type == BlockType.DEFECT:
            if block.title:
                doc.add_heading(block.title, level=1)
            self._add_defect_table(doc)
            doc.add_paragraph()

        elif block.block_type == BlockType.TEXT:
            if block.text_content:
                doc.add_paragraph(block.text_content)

        elif block.block_type == BlockType.CHART:
            img_data = self._render_chart_image(block)
            if img_data:
                if block.title:
                    doc.add_heading(block.title, level=1)
                doc.add_picture(io.BytesIO(img_data), width=Inches(5.5))
                doc.add_paragraph()

        elif block.block_type == BlockType.PAGE_BREAK:
            doc.add_page_break()

    def _add_mineral_table(self, doc: Document, block: ReportBlock) -> None:
        minerals = [
            ("Ab", "ab"), ("An", "an"), ("Or", "or_"), ("Q", "q"),
            ("Ill", "ill"), ("Chl", "chl"), ("Kn", "kn"), ("Mm", "mm"),
            ("Gb", "gb"), ("Ap", "ap"), ("Cc", "cc"), ("Dl", "dl"),
            ("Ank", "ank"), ("Rch", "rch"), ("Sd", "sd"), ("Srp", "srp"),
            ("Mst", "mst"), ("Ht", "ht"), ("Prl", "prl"),
        ]

        if block.min_wt_percent > 0:
            minerals = [
                (code, field) for code, field in minerals
                if any(getattr(r.minerals_weight, field, 0.0) >= block.min_wt_percent
                       for r in self._results)
            ]

        n_cols = 1 + len(self._results)
        table = doc.add_table(rows=1 + len(minerals) + 1, cols=n_cols, style="Light Grid Accent 1")
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Header
        table.cell(0, 0).text = "Mineral"
        for j, r in enumerate(self._results, 1):
            table.cell(0, j).text = r.sample_name

        # Mineral rows
        for i, (code, field) in enumerate(minerals, 1):
            table.cell(i, 0).text = code
            for j, r in enumerate(self._results, 1):
                val = getattr(r.minerals_weight, field, 0.0)
                table.cell(i, j).text = f"{val:.2f}"

        # Sum row
        sum_row = len(minerals) + 1
        table.cell(sum_row, 0).text = "Σ"
        for j, r in enumerate(self._results, 1):
            total = sum(v for k, v in r.minerals_weight.__dict__.items() if not k.startswith("_"))
            table.cell(sum_row, j).text = f"{total:.1f}"

    def _add_oxide_table(self, doc: Document) -> None:
        oxides = [
            ("SiO₂", "sio2"), ("TiO₂", "tio2"), ("Al₂O₃", "al2o3"),
            ("Fe₂O₃", "fe2o3"), ("FeO", "feo"), ("MgO", "mgo"),
            ("CaO", "cao"), ("Na₂O", "na2o"), ("K₂O", "k2o"),
            ("P₂O₅", "p2o5"), ("MnO", "mno"),
        ]

        n_cols = 1 + len(self._results)
        table = doc.add_table(rows=1 + len(oxides), cols=n_cols, style="Light Grid Accent 1")
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        table.cell(0, 0).text = "Oxide"
        for j, r in enumerate(self._results, 1):
            table.cell(0, j).text = r.sample_name

        for i, (label, field) in enumerate(oxides, 1):
            table.cell(i, 0).text = label
            for j, r in enumerate(self._results, 1):
                table.cell(i, j).text = f"{getattr(r.input_composition, field, 0.0):.2f}"

    def _add_parameters_table(self, doc: Document) -> None:
        params = [
            ("Type", lambda r: str(int(r.rock_type))),
            ("F", lambda r: f"{r.coefficients.F:.4f}"),
            ("A", lambda r: f"{r.coefficients.A:.4f}"),
            ("k1", lambda r: f"{r.coefficients.k1:.4f}"),
            ("k2", lambda r: f"{r.coefficients.k2:.4f}"),
            ("k3", lambda r: f"{r.coefficients.k3:.4f}"),
            ("k4", lambda r: f"{r.coefficients.k4:.4f}"),
        ]

        n_cols = 1 + len(self._results)
        table = doc.add_table(rows=1 + len(params), cols=n_cols, style="Light Grid Accent 1")
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        table.cell(0, 0).text = "Parameter"
        for j, r in enumerate(self._results, 1):
            table.cell(0, j).text = r.sample_name

        for i, (label, fn) in enumerate(params, 1):
            table.cell(i, 0).text = label
            for j, r in enumerate(self._results, 1):
                table.cell(i, j).text = fn(r)

    def _add_defect_table(self, doc: Document) -> None:
        if not self._results or not self._results[0].defect:
            return

        oxides = list(self._results[0].defect.keys())
        n_cols = 1 + len(self._results)
        table = doc.add_table(rows=1 + len(oxides), cols=n_cols, style="Light Grid Accent 1")
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        table.cell(0, 0).text = "Δ Oxide"
        for j, r in enumerate(self._results, 1):
            table.cell(0, j).text = r.sample_name

        for i, oxide in enumerate(oxides, 1):
            table.cell(i, 0).text = oxide
            for j, r in enumerate(self._results, 1):
                table.cell(i, j).text = f"{r.defect.get(oxide, 0.0):.2f}"

    def _render_chart_image(self, block: ReportBlock) -> Optional[bytes]:
        try:
            from src.charts import BUILTIN_CHARTS, ChartData
            import numpy as np

            chart = None
            for c in BUILTIN_CHARTS:
                if block.chart_type.lower() in c.get_name().lower():
                    chart = c
                    break
            if not chart:
                return None

            data = self._build_chart_data()
            fig = chart.render(data, sample_idx=block.chart_sample_idx)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            import matplotlib.pyplot as plt
            plt.close(fig)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.warning("Chart render for Word failed: %s", e)
            return None

    def _build_chart_data(self) -> "ChartData":
        from src.charts import ChartData
        import numpy as np

        data = ChartData(sample_names=[r.sample_name for r in self._results])

        for field in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                       "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]:
            data.minerals_wt[field] = np.array([getattr(r.minerals_weight, field, 0.0) for r in self._results])

        for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o"]:
            data.oxides[field] = np.array([getattr(r.input_composition, field, 0.0) for r in self._results])

        data.rock_types = [int(r.rock_type) for r in self._results]

        if self._results and self._results[0].defect:
            for oxide in self._results[0].defect:
                data.defect[oxide] = np.array([r.defect.get(oxide, 0.0) for r in self._results])

        return data
