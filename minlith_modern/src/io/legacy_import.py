"""Legacy import — read samples from old MINLITH1.xlsx format."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl

from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

# Row indices in ИСХ ДАННЫЕ sheet (0-indexed from row 2)
_OXIDE_ROWS = {
    "sio2": 2, "tio2": 3, "al2o3": 4, "fe2o3": 5, "feo": 6,
    "mgo": 7, "cao": 8, "na2o": 9, "k2o": 10, "p2o5": 11, "mno": 12,
    "c": 13, "so3": 14, "f": 15, "cl": 16, "s": 17, "co2": 18, "so": 19,
}


def import_from_minlith(path: Path) -> list[Sample]:
    """Import samples from legacy MINLITH1.xlsx.

    Reads the 'ИСХ ДАННЫЕ' sheet (sheet index 1).
    """
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)

    # Find the ИСХ ДАННЫЕ sheet
    ws = None
    for name in wb.sheetnames:
        if "ИСХ" in name.upper() or "ДАННЫЕ" in name.upper():
            ws = wb[name]
            break
    if ws is None and len(wb.sheetnames) > 1:
        ws = wb.worksheets[1]

    if ws is None:
        wb.close()
        return []

    samples = []

    # Detect format: if A2 = "SiO2" → horizontal
    cell_a2 = ws.cell(2, 1).value
    if str(cell_a2).strip() == "SiO2" if cell_a2 else False:
        # Horizontal: rows=oxides, cols=samples
        for c in range(2, (ws.max_column or 1) + 1):
            name = ws.cell(1, c).value
            sio2 = ws.cell(2, c).value
            if name is None and sio2 is None:
                continue

            oxide_data = {}
            for field, row in _OXIDE_ROWS.items():
                try:
                    oxide_data[field] = float(ws.cell(row, c).value or 0)
                except (ValueError, TypeError):
                    oxide_data[field] = 0.0

            samples.append(Sample(
                name=str(name) if name else f"Legacy_{c}",
                composition=OxideComposition(**oxide_data),
            ))
    else:
        # Transposed: col A = labels, cols B+ = samples
        label_rows = {}
        for r in range(2, (ws.max_row or 1) + 1):
            label = ws.cell(r, 1).value
            if label:
                label_rows[str(label).strip()] = r

        for c in range(2, (ws.max_column or 1) + 1):
            name = ws.cell(1, c).value
            if name is None:
                continue

            oxide_data = {}
            for field in _OXIDE_FIELDS:
                row = label_rows.get(field.upper().replace("2", "₂").replace("3", "₃"))
                if row is None:
                    # Try direct field name
                    for label, r in label_rows.items():
                        if label.lower().replace("₂", "2").replace("₃", "3") == field:
                            row = r
                            break
                try:
                    oxide_data[field] = float(ws.cell(row, c).value or 0) if row else 0.0
                except (ValueError, TypeError):
                    oxide_data[field] = 0.0

            samples.append(Sample(
                name=str(name) if name else f"Legacy_{c}",
                composition=OxideComposition(**oxide_data),
            ))

    wb.close()
    logger.info("Imported %d samples from legacy MINLITH: %s", len(samples), path.name)
    return samples


# For transposed format lookup
_OXIDE_FIELDS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]
