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
    """Brief: mineral table only."""
    t = ReportTemplate(name="Brief")
    t.add_block(BlockType.HEADER, title="MINLITH — Brief Report")
    t.add_block(BlockType.MINERAL_TABLE, title="Mineral Composition (wt%)")
    return t


def template_standard() -> ReportTemplate:
    """Standard: header + minerals + parameters + 1 chart."""
    t = ReportTemplate(name="Standard")
    t.add_block(BlockType.HEADER, title="MINLITH — Standard Report")
    t.add_block(BlockType.OXIDE_TABLE, title="Input Composition")
    t.add_block(BlockType.MINERAL_TABLE, title="Mineral Composition (wt%)")
    t.add_block(BlockType.PARAMETERS, title="Calculation Parameters")
    t.add_block(BlockType.DEFECT, title="Oxide Defect")
    t.add_block(BlockType.CHART, title="Mineral Bar Chart", chart_type="bar")
    return t


def template_full() -> ReportTemplate:
    """Full: everything."""
    t = ReportTemplate(name="Full")
    t.add_block(BlockType.HEADER, title="MINLITH — Full Report")
    t.add_block(BlockType.TEXT, title="Description", text_content="Enter description here...")
    t.add_block(BlockType.OXIDE_TABLE, title="Input Composition")
    t.add_block(BlockType.MINERAL_TABLE, title="Mineral Composition (wt%)", min_wt_percent=0.1)
    t.add_block(BlockType.PARAMETERS, title="Calculation Parameters")
    t.add_block(BlockType.DEFECT, title="Oxide Defect")
    t.add_block(BlockType.CHART, title="Mineral Composition", chart_type="bar")
    t.add_block(BlockType.CHART, title="Mineral Pie Chart", chart_type="pie")
    t.add_block(BlockType.CHART, title="Defect Chart", chart_type="defect")
    return t


PREDEFINED_TEMPLATES: dict[str, ReportTemplate] = {
    "brief": template_brief,
    "standard": template_standard,
    "full": template_full,
}
