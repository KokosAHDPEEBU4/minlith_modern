"""LaTeX exporter for publication-ready tables."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.core.models import CalculationResult

logger = logging.getLogger(__name__)


class LaTeXExporter:
    """Export calculation results to LaTeX format for scientific publications."""

    def __init__(self, results: list[CalculationResult]) -> None:
        self._results = results

    def export(
        self,
        path: Path,
        style: str = "gost",  # "gost" | "nature" | "springer"
        caption: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Path:
        """Export results to LaTeX table."""
        lines = []

        # Preamble
        lines.append(r"\documentclass{article}")
        lines.append(r"\usepackage[utf8]{inputenc}")
        lines.append(r"\usepackage[T2A]{fontenc}")
        lines.append(r"\usepackage[english,russian]{babel}")
        lines.append(r"\usepackage{booktabs}")
        lines.append(r"\usepackage{siunitx}")
        lines.append(r"\begin{document}")
        lines.append("")

        # Table
        n_cols = 1 + len(self._results)
        col_spec = "l" + "S[table-format=2.2]" * len(self._results)
        lines.append(r"\begin{table}[htbp]")
        lines.append(r"\centering")
        lines.append(f"\\caption{{{caption or 'Минеральный состав образцов'}}}")
        lines.append(f"\\label{{{label or 'tab:minerals'}}}")
        lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
        lines.append(r"\toprule")

        # Header
        header = "Минерал"
        for r in self._results:
            header += f" & {{{r.sample_name}}}"
        header += r" \\"
        lines.append(header)
        lines.append(r"\midrule")

        # Mineral rows
        minerals = [
            ("Ab", "ab", "Альбит"),
            ("An", "an", "Анортит"),
            ("Or", "or\\textsubscript{2}", "Ортоклаз"),
            ("Q", "q", "Кварц"),
            ("Ill", "ill", "Иллит"),
            ("Chl", "chl", "Хлорит"),
            ("Kn", "kn", "Каолинит"),
            ("Mm", "mm", "Монтмориллонит"),
            ("Gb", "gb", "Гиббсит"),
            ("Ap", "ap", "Апатит"),
            ("Cc", "cc", "Кальцит"),
            ("Dl", "dl", "Доломит"),
        ]

        for code, field, full_name in minerals:
            row = f"{full_name}"
            for r in self._results:
                val = getattr(r.minerals_weight, field, 0.0)
                row += f" & {val:.2f}"
            row += r" \\"
            lines.append(row)

        # Sum row
        lines.append(r"\midrule")
        sum_row = r"\textbf{Σ}"
        for r in self._results:
            total = sum(
                getattr(r.minerals_weight, f, 0.0)
                for f in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                          "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]
            )
            sum_row += f" & {total:.1f}"
        sum_row += r" \\"
        lines.append(sum_row)

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("")
        lines.append(r"\end{document}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("LaTeX exported: %s", path)
        return path
