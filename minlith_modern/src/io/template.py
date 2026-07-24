"""Template — create and load MINLITH Excel template files."""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from src.core.constants import OXIDE_ORDER
from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

# Display names for oxides in the template (ASCII — compatible with excel.py loader)
_OXIDE_DISPLAY: dict[str, str] = {
    "sio2": "SiO2", "tio2": "TiO2", "al2o3": "Al2O3",
    "fe2o3": "Fe2O3", "feo": "FeO", "mgo": "MgO",
    "cao": "CaO", "na2o": "Na2O", "k2o": "K2O",
    "p2o5": "P2O5", "mno": "MnO", "c": "C",
    "so3": "SO3", "f": "F", "cl": "Cl",
    "s": "S", "co2": "CO2", "so": "SO",
}

# Main oxides that should always be present (for highlighting)
_MAIN_OXIDES = {"sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o"}

# Style constants
_HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_MAIN_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
_OPTIONAL_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)


def create_template(
    path: Path | str,
    sample_names: list[str] | None = None,
    examples: list[dict[str, float]] | None = None,
) -> Path:
    """Create a MINLITH Excel template file.

    Args:
        path: Output file path (.xlsx).
        sample_names: Optional list of sample names to pre-fill columns.
        examples: Optional list of dicts {oxide_field: value} for example data.

    Returns:
        Path to the created file.
    """
    path = Path(path)
    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"

    # ── Row 1: Header ──
    ws.cell(1, 1, "Name").font = _HEADER_FONT
    ws.cell(1, 1).fill = _HEADER_FILL
    ws.cell(1, 1).alignment = Alignment(horizontal="center")
    ws.cell(1, 1).border = _BORDER

    names = sample_names or []
    if examples and not names:
        names = [f"Образец {i + 1}" for i in range(len(examples))]
    if not names:
        names = ["Образец 1"]

    for col_idx, name in enumerate(names, start=2):
        cell = ws.cell(1, col_idx, name)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = _BORDER

    # ── Column A (rows 2+): Oxide labels ──
    for row_idx, oxide in enumerate(OXIDE_ORDER, start=2):
        display = _OXIDE_DISPLAY.get(oxide, oxide.upper())
        cell = ws.cell(row_idx, 1, display)
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="left")
        if oxide in _MAIN_OXIDES:
            cell.fill = _MAIN_FILL
            cell.font = Font(bold=True)
        else:
            cell.fill = _OPTIONAL_FILL

    # ── Example data (if provided) ──
    if examples:
        for col_idx, ex in enumerate(examples, start=2):
            for row_idx, oxide in enumerate(OXIDE_ORDER, start=2):
                val = ex.get(oxide, 0.0)
                if val != 0.0:
                    cell = ws.cell(row_idx, col_idx, val)
                    cell.number_format = "0.00"
                    cell.border = _BORDER
                    cell.alignment = Alignment(horizontal="right")
                else:
                    ws.cell(row_idx, col_idx).border = _BORDER

    # ── Column widths ──
    ws.column_dimensions["A"].width = 12
    for col_idx in range(2, len(names) + 2):
        col_letter = ws.cell(1, col_idx).column_letter
        ws.column_dimensions[col_letter].width = 14

    # ── Freeze panes ──
    ws.freeze_panes = "B2"

    # ── Add legend sheet ──
    legend = wb.create_sheet("Справка")
    legend.cell(1, 1, "Оксид").font = Font(bold=True)
    legend.cell(1, 2, "Обязательный").font = Font(bold=True)
    legend.cell(1, 3, "Описание").font = Font(bold=True)

    descriptions = {
        "sio2": "Кремнезём — основной компонент",
        "tio2": "Титан — обычно微量",
        "al2o3": "Глинозём — ключевой для расчёта",
        "fe2o3": "Оксид железа (III)",
        "feo": "Оксид железа (II)",
        "mgo": "Магнезия",
        "cao": "Известь",
        "na2o": "Натрий",
        "k2o": "Калий",
        "p2o5": "Фосфор",
        "mno": "Марганец",
        "c": "Углерод",
        "so3": "Серный ангидрид",
        "f": "Фтор",
        "cl": "Хлор",
        "s": "Сера",
        "co2": "Углекислый газ",
        "so": "Сернистый газ",
    }

    for i, oxide in enumerate(OXIDE_ORDER, start=2):
        display = _OXIDE_DISPLAY.get(oxide, oxide.upper())
        legend.cell(i, 1, display)
        legend.cell(i, 2, "Да" if oxide in _MAIN_OXIDES else "Нет")
        legend.cell(i, 3, descriptions.get(oxide, ""))

    legend.column_dimensions["A"].width = 12
    legend.column_dimensions["B"].width = 14
    legend.column_dimensions["C"].width = 40

    # ── Add instructions sheet ──
    instr = wb.create_sheet("Инструкция")
    instructions = [
        "Как заполнить шаблон MINLITH:",
        "",
        "1. Лист «Данные» — внесите содержания оксидов (в %) для каждого образца.",
        "2. Столбец A содержит названия оксидов.",
        "3. Обязательные оксиды: SiO2, Al2O3, Fe2O3, FeO, MgO, CaO, Na2O, K2O.",
        "4. Остальные оксиды можно оставить равными 0 (или не заполнять).",
        "5. Сумма всех оксидов должна быть в диапазоне 98-102%.",
        "6. Сохраните файл и загрузите в MINLITH Modern через «Импорт .xlsx».",
        "",
        "Формат файла совместим с автоматическим распознаванием:",
        "  — Строка 1: имена образцов (столбец A = «Name»)",
        "  — Столбец A (строки 2+): подписи оксидов",
        "  — Ячейки B2+: значения оксидов",
    ]
    for i, line in enumerate(instructions, start=1):
        instr.cell(i, 1, line)
    instr.column_dimensions["A"].width = 80

    wb.save(path)
    logger.info("Template created: %s", path)
    return path


def load_template(path: Path | str) -> list[Sample]:
    """Load samples from a MINLITH template Excel file.

    This is a thin wrapper around load_samples() that adds:
    - Template-specific validation (checks for required oxides)
    - Warning if sum is outside 98-102%
    - Logging of detected oxides per sample

    Args:
        path: Path to the template .xlsx file.

    Returns:
        List of Sample objects.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If no samples found or required oxides missing.
    """
    from src.io.excel import load_samples

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    samples = load_samples(path)
    if not samples:
        raise ValueError(f"No samples found in template: {path.name}")

    # Validate each sample
    for sample in samples:
        ox = sample.composition
        total = ox.sum()

        # Warn about sum
        if total < 98.0 or total > 102.0:
            logger.warning(
                "Sample '%s': sum=%.2f%% (expected 98-102%%)",
                sample.name, total,
            )

        # Warn about missing main oxides
        missing = []
        for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o"]:
            if getattr(ox, field, 0.0) == 0.0:
                missing.append(field.upper())
        if missing:
            logger.warning(
                "Sample '%s': missing oxides: %s",
                sample.name, ", ".join(missing),
            )

        logger.info(
            "Template sample '%s': sum=%.2f%%, oxides detected=%d",
            sample.name, total,
            sum(1 for f in OXIDE_ORDER if getattr(ox, f, 0.0) != 0.0),
        )

    return samples


def create_reference_template(path: Path | str) -> Path:
    """Create a template pre-filled with T-O2 reference values.

    Args:
        path: Output file path (.xlsx).

    Returns:
        Path to the created file.
    """
    t_o2_example = {
        "sio2": 52.5, "tio2": 0.99, "al2o3": 23.41,
        "fe2o3": 1.71, "feo": 8.06, "mgo": 2.35,
        "cao": 0.28, "na2o": 0.94, "k2o": 3.45,
        "p2o5": 0.31, "mno": 0.157502,
    }
    return create_template(
        path,
        sample_names=["T-O2 (эталон)"],
        examples=[t_o2_example],
    )
