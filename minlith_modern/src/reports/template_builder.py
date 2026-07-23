"""Report template builder — block-based report composition."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BlockType(Enum):
    MINERAL_TABLE = "mineral_table"
    OXIDE_TABLE = "oxide_table"
    CHART = "chart"
    PARAMETERS = "parameters"
    DEFECT = "defect"
    TEXT = "text"
    HEADER = "header"
    PAGE_BREAK = "page_break"


@dataclass
class ReportBlock:
    """Single block in a report template."""

    block_type: BlockType
    title: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    # For TEXT block
    text_content: str = ""

    # For CHART block
    chart_type: str = ""
    chart_sample_idx: int = 0

    # For tables
    show_minerals: list[str] = field(default_factory=list)
    min_wt_percent: float = 0.0
    sort_by: str = ""


@dataclass
class ReportTemplate:
    """Full report template with ordered blocks."""

    name: str = "Standard"
    blocks: list[ReportBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_block(self, block_type: BlockType, **kwargs) -> ReportBlock:
        block = ReportBlock(block_type=block_type, **kwargs)
        self.blocks.append(block)
        return block

    def remove_block(self, index: int) -> None:
        if 0 <= index < len(self.blocks):
            self.blocks.pop(index)

    def move_block(self, from_idx: int, to_idx: int) -> None:
        if 0 <= from_idx < len(self.blocks) and 0 <= to_idx < len(self.blocks):
            block = self.blocks.pop(from_idx)
            self.blocks.insert(to_idx, block)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "blocks": [
                {
                    "block_type": b.block_type.value,
                    "title": b.title,
                    "options": b.options,
                    "text_content": b.text_content,
                    "chart_type": b.chart_type,
                    "chart_sample_idx": b.chart_sample_idx,
                    "show_minerals": b.show_minerals,
                    "min_wt_percent": b.min_wt_percent,
                    "sort_by": b.sort_by,
                }
                for b in self.blocks
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReportTemplate:
        blocks = []
        for b in data.get("blocks", []):
            blocks.append(ReportBlock(
                block_type=BlockType(b["block_type"]),
                title=b.get("title", ""),
                options=b.get("options", {}),
                text_content=b.get("text_content", ""),
                chart_type=b.get("chart_type", ""),
                chart_sample_idx=b.get("chart_sample_idx", 0),
                show_minerals=b.get("show_minerals", []),
                min_wt_percent=b.get("min_wt_percent", 0.0),
                sort_by=b.get("sort_by", ""),
            ))
        return cls(name=data.get("name", "Custom"), blocks=blocks, metadata=data.get("metadata", {}))

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ReportTemplate:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


# ── Predefined templates ──

def template_brief() -> ReportTemplate:
    """Краткий: только таблица минералов."""
    t = ReportTemplate(name="Краткий")
    t.add_block(BlockType.HEADER, title="MINLITH — Краткий отчёт")
    t.add_block(BlockType.MINERAL_TABLE, title="Минеральный состав (вес.%)")
    return t


def template_standard() -> ReportTemplate:
    """Стандартный: заголовок + минералы + параметры + диаграмма."""
    t = ReportTemplate(name="Стандартный")
    t.add_block(BlockType.HEADER, title="MINLITH — Стандартный отчёт")
    t.add_block(BlockType.OXIDE_TABLE, title="Входные данные")
    t.add_block(BlockType.MINERAL_TABLE, title="Минеральный состав (вес.%)")
    t.add_block(BlockType.PARAMETERS, title="Коэффициенты расчёта")
    t.add_block(BlockType.DEFECT, title="Дефект (остатки оксидов)")
    t.add_block(BlockType.CHART, title="Минеральный состав", chart_type="bar")
    return t


def template_full() -> ReportTemplate:
    """Полный: всё включено."""
    t = ReportTemplate(name="Полный")
    t.add_block(BlockType.HEADER, title="MINLITH — Полный отчёт")
    t.add_block(BlockType.TEXT, title="Описание", text_content="Введите описание здесь...")
    t.add_block(BlockType.OXIDE_TABLE, title="Входные данные")
    t.add_block(BlockType.MINERAL_TABLE, title="Минеральный состав (вес.%)", min_wt_percent=0.1)
    t.add_block(BlockType.PARAMETERS, title="Коэффициенты расчёта")
    t.add_block(BlockType.DEFECT, title="Дефект (остатки оксидов)")
    t.add_block(BlockType.CHART, title="Минеральный состав", chart_type="bar")
    t.add_block(BlockType.CHART, title="Круговая диаграмма", chart_type="pie")
    t.add_block(BlockType.CHART, title="Дефект", chart_type="defect")
    return t


def template_core_report() -> ReportTemplate:
    """Отчёт по керну: оксиды + минералы + параметры (без диаграмм)."""
    t = ReportTemplate(name="Керн")
    t.add_block(BlockType.HEADER, title="MINLITH — Отчёт по керну")
    t.add_block(BlockType.OXIDE_TABLE, title="Химический состав (вес.%)")
    t.add_block(BlockType.MINERAL_TABLE, title="Минеральный состав (вес.%)")
    t.add_block(BlockType.PARAMETERS, title="Параметры расчёта")
    t.add_block(BlockType.DEFECT, title="Дефект")
    return t


def template_geochemical_passport() -> ReportTemplate:
    """Геохимический паспорт месторождения: сводная + параметры + диаграммы."""
    t = ReportTemplate(name="Геохимический паспорт")
    t.add_block(BlockType.HEADER, title="Геохимический паспорт")
    t.add_block(BlockType.TEXT, title="Описание",
                text_content="Геохимический паспорт месторождения (автоматически)")
    t.add_block(BlockType.OXIDE_TABLE, title="Средний химический состав")
    t.add_block(BlockType.MINERAL_TABLE, title="Средний минеральный состав", min_wt_percent=0.5)
    t.add_block(BlockType.PARAMETERS, title="Средние коэффициенты")
    t.add_block(BlockType.CHART, title="Минеральный состав", chart_type="bar")
    t.add_block(BlockType.CHART, title="Круговая диаграмма", chart_type="pie")
    return t


PREDEFINED_TEMPLATES: dict[str, ReportTemplate] = {
    "brief": template_brief,
    "standard": template_standard,
    "full": template_full,
    "core": template_core_report,
    "geochemical": template_geochemical_passport,
}
