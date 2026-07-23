"""Excel I/O — import samples from .xlsx/.xls and export results.

Supported input formats:
  1. MINLITH original (ИСХ ДАННЫЕ style):
     - Row 1: sample names
     - Rows 2-19: oxide values (SiO2..SO)
     - Column A: oxide labels

  2. Transposed (Копия ИД style):
     - Column A: oxide labels (row 1 = "Name")
     - Columns B+: sample data

  3. .xls (old Excel 97-2003) — via xlrd

Output format matches Excel minerals sheet structure.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import openpyxl

from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

# Oxide labels in order (rows 2-19 in ИСХ ДАННЫЕ, rows 2-19 in Копия ИД)
OXIDE_LABELS: list[str] = [
    "SiO2", "TiO2", "Al2O3", "Fe2O3", "FeO",
    "MgO", "CaO", "Na2O", "K2O", "P2O5",
    "MnO", "C", "SO3", "F", "Cl", "S", "CO2", "SO",
]

# Mapping from Excel label to OxideComposition field
_LABEL_TO_FIELD: dict[str, str] = {
    "SiO2": "sio2", "TiO2": "tio2", "Al2O3": "al2o3",
    "Fe2O3": "fe2o3", "FeO": "feo", "MgO": "mgo",
    "CaO": "cao", "Na2O": "na2o", "K2O": "k2o",
    "P2O5": "p2o5", "MnO": "mno", "C": "c",
    "SO3": "so3", "F": "f", "Cl": "cl",
    "S": "s", "CO2": "co2", "SO": "so",
}


def _safe_float(val: object) -> float:
    """Convert value to float, returning 0.0 for None/non-numeric."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def load_samples(path: str | Path) -> list[Sample]:
    """Load samples from an Excel file (.xlsx or .xls).

    Auto-detects format:
      - If row 1 col A is empty/None and row 2 col A = "SiO2" → ИСХ ДАННЫЕ format
      - If row 1 col A = "Name" → transposed format

    Returns list of Sample objects.
    """
    path = Path(path)
    if path.suffix.lower() == ".xls":
        return _load_xls(path)

    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    ws = wb.active
    if ws is None:
        return []

    # Detect format
    cell_a1 = ws.cell(1, 1).value
    cell_a2 = ws.cell(2, 1).value

    if str(cell_a2).strip() == "SiO2" if cell_a2 else False:
        samples = _load_horizontal(ws)
    elif str(cell_a1).strip().lower() == "name" if cell_a1 else False:
        samples = _load_transposed(ws)
    else:
        # Try horizontal by default
        samples = _load_horizontal(ws)

    wb.close()
    logger.info("Loaded %d samples from %s", len(samples), path.name)
    return samples


def _load_xls(path: Path) -> list[Sample]:
    """Load samples from .xls (Excel 97-2003) via xlrd."""
    try:
        import xlrd
    except ImportError:
        raise ImportError("xlrd is required for .xls files: pip install xlrd")

    wb = xlrd.open_workbook(str(path))
    ws = wb.sheet_by_index(0)

    # Detect format
    cell_a1 = ws.cell_value(0, 0)
    cell_a2 = ws.cell_value(1, 0) if ws.nrows > 1 else ""

    if str(cell_a2).strip() == "SiO2" if cell_a2 else False:
        return _load_horizontal_xls(ws)
    elif str(cell_a1).strip().lower() == "name" if cell_a1 else False:
        return _load_transposed_xls(ws)
    else:
        return _load_horizontal_xls(ws)


def _load_horizontal_xls(ws) -> list[Sample]:
    """Load from ИСХ ДАННЫЕ format in .xls."""
    samples = []
    for c in range(1, ws.ncols):
        name = ws.cell_value(0, c)
        sio2 = ws.cell_value(1, c)
        if name == "" and sio2 == "":
            continue
        fields: dict[str, float] = {}
        for r_idx, label in enumerate(OXIDE_LABELS, start=1):
            fields[_LABEL_TO_FIELD[label]] = _safe_float(ws.cell_value(r_idx, c))
        sample_name = str(name) if name else f"Sample_{c}"
        samples.append(Sample(name=sample_name, composition=OxideComposition(**fields)))
    return samples


def _load_transposed_xls(ws) -> list[Sample]:
    """Load from Копия ИД format in .xls."""
    samples = []
    label_rows: dict[str, int] = {}
    for r in range(1, ws.nrows):
        label = ws.cell_value(r, 0)
        if label:
            label_rows[str(label).strip()] = r

    for c in range(1, ws.ncols):
        name = ws.cell_value(0, c)
        if name == "":
            continue
        fields: dict[str, float] = {}
        for label, field in _LABEL_TO_FIELD.items():
            row = label_rows.get(label)
            fields[field] = _safe_float(ws.cell_value(row, c)) if row is not None else 0.0
        sample_name = str(name) if name else f"Sample_{c}"
        samples.append(Sample(name=sample_name, composition=OxideComposition(**fields)))
    return samples


def _load_horizontal(ws) -> list[Sample]:
    """Load from ИСХ ДАННЫЕ format (rows=oxides, cols=samples)."""
    samples = []
    # Find sample columns: row 1 has names, row 2 has SiO2
    for c in range(2, (ws.max_column or 1) + 1):
        name = ws.cell(1, c).value
        sio2 = ws.cell(2, c).value
        if name is None and sio2 is None:
            continue

        oxide_values: dict[str, float] = {}
        for r_idx, label in enumerate(OXIDE_LABELS, start=2):
            oxide_values[label] = _safe_float(ws.cell(r_idx, c).value)

        fields = {}
        for label, val in oxide_values.items():
            field = _LABEL_TO_FIELD.get(label)
            if field:
                fields[field] = val

        sample_name = str(name) if name else f"Sample_{c}"
        samples.append(Sample(name=sample_name, composition=OxideComposition(**fields)))

    return samples


def _load_transposed(ws) -> list[Sample]:
    """Load from Копия ИД format (col A=oxides, cols B+=samples)."""
    samples = []
    # Build oxide label → row mapping from column A
    label_rows: dict[str, int] = {}
    for r in range(2, (ws.max_row or 1) + 1):
        label = ws.cell(r, 1).value
        if label:
            label_rows[str(label).strip()] = r

    # Read samples from columns B onwards
    for c in range(2, (ws.max_column or 1) + 1):
        name = ws.cell(1, c).value
        if name is None:
            continue

        fields: dict[str, float] = {}
        for label, field in _LABEL_TO_FIELD.items():
            row = label_rows.get(label)
            if row:
                fields[field] = _safe_float(ws.cell(row, c).value)
            else:
                fields[field] = 0.0

        sample_name = str(name) if name else f"Sample_{c}"
        samples.append(Sample(name=sample_name, composition=OxideComposition(**fields)))

    return samples


def save_results(
    path: str | Path,
    results: list,
    include_input: bool = True,
    include_defect: bool = True,
) -> None:
    """Save calculation results to an Excel file.

    Creates sheets:
      - "Results": mineral weight % per sample
      - "Input": original oxide compositions (optional)
      - "Defect": oxide residuals (optional)
    """
    from src.core.models import CalculationResult
    from src.core.constants import MINERAL_CODES

    path = Path(path)
    wb = openpyxl.Workbook()

    # ── Results sheet ──
    ws = wb.active
    ws.title = "Results"

    # Header row
    ws.cell(1, 1, "Sample")
    ws.cell(1, 2, "Type")
    ws.cell(1, 3, "F")
    ws.cell(1, 4, "A")
    col = 5
    for code in MINERAL_CODES:
        ws.cell(1, col, code)
        col += 1

    # Data rows
    for i, result in enumerate(results, start=2):
        ws.cell(i, 1, result.sample_name)
        ws.cell(i, 2, result.rock_type.name)
        ws.cell(i, 3, result.coefficients.F)
        ws.cell(i, 4, result.coefficients.A)
        col = 5
        for code in MINERAL_CODES:
            field = code.lower().replace("or", "or_").replace("ill", "ill")
            # Map mineral code to MineralComposition field
            field_map = {
                "Ab": "ab", "An": "an", "Or": "or_", "Q": "q", "Mm": "mm",
                "Ill": "ill", "Chl": "chl", "Gb": "gb", "Kn": "kn",
                "Ap": "ap", "Cc": "cc", "Dl": "dl", "Ank": "ank",
                "Rch": "rch", "Sd": "sd", "Srp": "srp", "Mst": "mst",
                "Ht": "ht", "Prl": "prl", "Pr": "pr", "Rt": "rt",
                "Hl": "hl", "Gy": "gy", "Fl": "fl",
            }
            attr = field_map.get(code, code.lower())
            val = getattr(result.minerals_weight, attr, 0.0)
            ws.cell(i, col, round(val, 2))
            col += 1

    # ── Input sheet ──
    if include_input:
        ws_in = wb.create_sheet("Input")
        ws_in.cell(1, 1, "Oxide")
        for i, result in enumerate(results, start=2):
            ws_in.cell(1, i, result.sample_name)

        oxide_fields = [
            ("SiO2", "sio2"), ("TiO2", "tio2"), ("Al2O3", "al2o3"),
            ("Fe2O3", "fe2o3"), ("FeO", "feo"), ("MgO", "mgo"),
            ("CaO", "cao"), ("Na2O", "na2o"), ("K2O", "k2o"),
            ("P2O5", "p2o5"), ("MnO", "mno"),
        ]
        for r, (label, field) in enumerate(oxide_fields, start=2):
            ws_in.cell(r, 1, label)
            for i, result in enumerate(results, start=2):
                val = getattr(result.input_composition, field, 0.0)
                ws_in.cell(r, i, round(val, 4))

    # ── Defect sheet ──
    if include_defect:
        ws_d = wb.create_sheet("Defect")
        ws_d.cell(1, 1, "Oxide")
        for i, result in enumerate(results, start=2):
            ws_d.cell(1, i, result.sample_name)

        if results:
            for r, oxide in enumerate(results[0].defect.keys(), start=2):
                ws_d.cell(r, 1, oxide)
                for i, result in enumerate(results, start=2):
                    val = result.defect.get(oxide, 0.0)
                    ws_d.cell(r, i, round(val, 2))

    # ── GeoParameters sheet ──
    ws_geo = wb.create_sheet("GeoParams")
    ws_geo.cell(1, 1, "Parameter")
    for i, result in enumerate(results, start=2):
        ws_geo.cell(1, i, result.sample_name)

    geo_fields = [
        ("CIA", "CIA"), ("ICV", "ICV"), ("PIA", "PIA"),
        ("ASI", "ASI"), ("AI", "AI"),
    ]
    for r, (label, attr) in enumerate(geo_fields, start=2):
        ws_geo.cell(r, 1, label)
        for i, result in enumerate(results, start=2):
            val = getattr(result.geo_params, attr, 0.0) if result.geo_params else 0.0
            ws_geo.cell(r, i, round(val, 4))

    wb.save(str(path))

    # Auto-fit column widths
    for ws in wb.worksheets:
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            ws.column_dimensions[col_letter].width = min(max_length + 2, 20)

    logger.info("Saved results to %s", path)


def save_results_json(path: str | Path, results: list) -> None:
    """Save calculation results to JSON file."""
    import json
    from src.core.models import CalculationResult

    path = Path(path)
    data = []
    for r in results:
        minerals = {k: round(v, 2) for k, v in r.minerals_weight.__dict__.items()
                    if not k.startswith("_") and v != 0}
        oxides = {k: round(v, 4) for k, v in r.input_composition.__dict__.items()
                  if v != 0}
        data.append({
            "sample_name": r.sample_name,
            "rock_type": r.rock_type.name,
            "F": round(r.coefficients.F, 4),
            "A": round(r.coefficients.A, 4),
            "k1": round(r.coefficients.k1, 4),
            "k2": round(r.coefficients.k2, 4),
            "k3": round(r.coefficients.k3, 4),
            "k4": round(r.coefficients.k4, 4),
            "oxides": oxides,
            "minerals_wt": minerals,
            "defect": {k: round(v, 2) for k, v in r.defect.items()},
            "warnings": r.warnings,
        })

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved results to JSON: %s", path)


def save_results_csv(path: str | Path, results: list, delimiter: str = ";") -> None:
    """Save calculation results to CSV (semicolon-separated by default)."""
    import csv
    from src.core.constants import MINERAL_CODES

    path = Path(path)
    oxide_fields = [
        ("SiO2", "sio2"), ("TiO2", "tio2"), ("Al2O3", "al2o3"),
        ("Fe2O3", "fe2o3"), ("FeO", "feo"), ("MgO", "mgo"),
        ("CaO", "cao"), ("Na2O", "na2o"), ("K2O", "k2o"),
        ("P2O5", "p2o5"), ("MnO", "mno"),
    ]
    field_map = {
        "Ab": "ab", "An": "an", "Or": "or_", "Q": "q", "Mm": "mm",
        "Ill": "ill", "Chl": "chl", "Gb": "gb", "Kn": "kn",
        "Ap": "ap", "Cc": "cc", "Dl": "dl", "Ank": "ank",
        "Rch": "rch", "Sd": "sd", "Srp": "srp", "Mst": "mst",
        "Ht": "ht", "Prl": "prl", "Pr": "pr", "Rt": "rt",
        "Hl": "hl", "Gy": "gy", "Fl": "fl",
    }

    header = ["Sample", "Type", "F", "A"]
    header += [label for label, _ in oxide_fields]
    header += list(MINERAL_CODES)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(header)
        for r in results:
            row = [r.sample_name, r.rock_type.name, r.coefficients.F, r.coefficients.A]
            row += [round(getattr(r.input_composition, field, 0.0), 4) for _, field in oxide_fields]
            row += [round(getattr(r.minerals_weight, field_map.get(code, code.lower()), 0.0), 2)
                    for code in MINERAL_CODES]
            writer.writerow(row)

    logger.info("Saved results to CSV: %s", path)
