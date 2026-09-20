"""Tests for report system: templates, chart renderer, generators."""

from __future__ import annotations

import zipfile

import pytest

from src.reports.chart_renderer import (
    build_chart_data,
    find_chart_plugin,
    render_chart_base64,
    render_chart_png,
)
from src.reports.html_generator import HTMLGenerator
from src.reports.pdf_generator import PDFGenerator
from src.reports.template_builder import (
    PREDEFINED_TEMPLATES,
    BlockType,
    ReportTemplate,
)
from src.reports.word_generator import WordGenerator

REPORT_CHART_TYPES = [
    "bar", "pie", "defect", "boxplot", "heatmap",
    "correlation", "harker", "qapf", "tas", "radar",
]


def template_with_chart(chart_type: str, name: str = "Test") -> ReportTemplate:
    t = ReportTemplate(name=name)
    t.add_block(BlockType.HEADER, title="MINLITH")
    t.add_block(BlockType.MINERAL_TABLE, title="Minerals")
    t.add_block(BlockType.CHART, title="Chart", chart_type=chart_type)
    return t


# ── Chart renderer ──

def test_predefined_templates_exist() -> None:
    assert set(PREDEFINED_TEMPLATES) == {
        "brief", "standard", "full", "core", "geochemical",
    }
    for factory in PREDEFINED_TEMPLATES.values():
        t = factory()
        assert t.blocks, f"template {t.name!r} has no blocks"


def test_build_chart_data(result_list) -> None:
    data = build_chart_data(result_list)
    assert data.sample_names == [r.sample_name for r in result_list]
    assert "sio2" in data.oxides and "k2o" in data.oxides
    assert "ab" in data.minerals_wt and "prl" in data.minerals_wt
    assert len(data.rock_types) == len(result_list)
    assert data.metadata["k_values"]["k1"]


@pytest.mark.parametrize("chart_type", REPORT_CHART_TYPES)
def test_render_chart_png(result_list, chart_type) -> None:
    if find_chart_plugin(chart_type) is None:
        pytest.skip(f"no plugin for {chart_type}")
    png = render_chart_png(chart_type, result_list)
    assert png is not None
    assert png.startswith(b"\x89PNG")


def test_render_chart_base64(result_list) -> None:
    uri = render_chart_base64("bar", result_list)
    assert uri is not None
    assert uri.startswith("data:image/png;base64,")


def test_render_chart_unknown_type(result_list) -> None:
    assert render_chart_png("not_a_chart", result_list) is None


# ── HTML generator ──

def test_html_generator_embeds_chart(result_list, tmp_path) -> None:
    out = tmp_path / "report.html"
    HTMLGenerator(result_list).generate(out, template_with_chart("bar"))
    html = out.read_text(encoding="utf-8")
    assert "<img" in html
    assert "data:image/png;base64" in html


def test_html_generator_page_break_handled(result_list, tmp_path) -> None:
    t = template_with_chart("bar")
    t.add_block(BlockType.PAGE_BREAK)
    out = tmp_path / "report.html"
    HTMLGenerator(result_list).generate(out, t)
    assert out.exists()


# ── Word generator ──

def test_word_generator_embeds_chart(result_list, tmp_path) -> None:
    out = tmp_path / "report.docx"
    WordGenerator(result_list).generate(out, template_with_chart("bar"))
    assert out.exists() and out.stat().st_size > 0
    with zipfile.ZipFile(out) as zf:
        media = [n for n in zf.namelist() if n.startswith("word/media/")]
        assert media, "expected embedded chart image in docx"


# ── PDF generator ──

def test_pdf_generator_embeds_chart(result_list, tmp_path) -> None:
    out = tmp_path / "report.pdf"
    PDFGenerator(result_list).generate(out, template_with_chart("bar"))
    assert out.exists() and out.stat().st_size > 0
    assert b"%PDF" in out.read_bytes()[:16]
