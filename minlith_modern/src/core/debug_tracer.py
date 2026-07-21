"""Debug trace collector for mineral calculation steps."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class TraceStep:
    """Single step in the calculation trace."""

    step: str
    variable: str
    value: Any
    comment: str = ""


@dataclass
class TraceCondition:
    """Condition check in the calculation trace."""

    step: str
    condition: str
    result: bool
    branch: str


class DebugTraceCollector:
    """Collects debug trace for a single sample calculation."""

    def __init__(self, sample_name: str):
        self.sample_name = sample_name
        self.steps: list[TraceStep] = []
        self.conditions: list[TraceCondition] = []

    def record(self, step: str, variable: str, value: Any, comment: str = "") -> None:
        """Record a calculation step."""
        self.steps.append(TraceStep(step=step, variable=variable, value=value, comment=comment))

    def record_condition(
        self, step: str, condition: str, result: bool, branch: str
    ) -> None:
        """Record a condition check."""
        self.conditions.append(
            TraceCondition(step=step, condition=condition, result=result, branch=branch)
        )

    def to_dict(self) -> dict:
        """Export trace as dictionary."""
        return {
            "sample_name": self.sample_name,
            "steps": [
                {"step": s.step, "variable": s.variable, "value": s.value, "comment": s.comment}
                for s in self.steps
            ],
            "conditions": [
                {"step": c.step, "condition": c.condition, "result": c.result, "branch": c.branch}
                for c in self.conditions
            ],
        }

    def to_text(self) -> str:
        """Export trace as readable text."""
        lines = [f"=== Trace: {self.sample_name} ===\n"]
        for s in self.steps:
            lines.append(f"  {s.step}: {s.variable} = {s.value}  {s.comment}")
        for c in self.conditions:
            mark = "✓" if c.result else "✗"
            lines.append(f"  {c.step}: {c.condition} → {mark} ({c.branch})")
        return "\n".join(lines)

    def export_json(self, path: Path) -> None:
        """Export trace to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
