"""XRF importer — read data from Bruker/Panalytical/Rigaku XRF spectrometers."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

# Element → Oxide mapping (for XRF output in element mode)
_ELEMENT_TO_OXIDE = {
    "Si": "sio2", "Ti": "tio2", "Al": "al2o3", "Fe": "fe2o3",
    "Mg": "mgo", "Ca": "cao", "Na": "na2o", "K": "k2o",
    "P": "p2o5", "Mn": "mno", "S": "s", "Sr": "sro",
    "Ba": "bao", "Zr": "zro2", "Rb": "rb2o", "Ni": "nio",
}

# Common column name mappings for different XRF formats
_COLUMN_ALIASES = {
    "sio2": ["SiO2", "SiO₂", "SiO2%", "SiO2 (%)", "sio2", "Si"],
    "tio2": ["TiO2", "TiO₂", "TiO2%", "TiO2 (%)", "tio2", "Ti"],
    "al2o3": ["Al2O3", "Al₂O₃", "Al2O3%", "Al2O3 (%)", "al2o3", "Al"],
    "fe2o3": ["Fe2O3", "Fe₂O₃", "Fe2O3%", "Fe2O3 (%)", "fe2o3", "Fe"],
    "feo": ["FeO", "FeO%", "FeO (%)", "feo"],
    "mgo": ["MgO", "MgO%", "MgO (%)", "mgo", "Mg"],
    "cao": ["CaO", "CaO%", "CaO (%)", "cao", "Ca"],
    "na2o": ["Na2O", "Na₂O", "Na2O%", "Na2O (%)", "na2o", "Na"],
    "k2o": ["K2O", "K₂O", "K2O%", "K2O (%)", "k2o", "K"],
    "p2o5": ["P2O5", "P₂O₅", "P2O5%", "P2O5 (%)", "p2o5", "P"],
    "mno": ["MnO", "MnO%", "MnO (%)", "mno", "Mn"],
}


def _detect_format(path: Path) -> str:
    """Detect XRF file format."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    elif suffix in (".xls", ".xlsx"):
        return "excel"
    elif suffix == ".txt":
        return "txt"
    return "csv"


def _find_column(headers: list[str], field: str) -> int | None:
    """Find column index for an oxide field."""
    aliases = _COLUMN_ALIASES.get(field, [field])
    for i, h in enumerate(headers):
        h_clean = h.strip().lower()
        for alias in aliases:
            if h_clean == alias.lower():
                return i
    return None


def read_xrf_csv(path: Path) -> list[Sample]:
    """Read XRF data from CSV (Bruker/Panalytical format)."""
    samples = []

    with open(path, "r", encoding="utf-8-sig") as f:
        # Detect delimiter
        sample_line = f.readline()
        sep = ";" if ";" in sample_line else ","
        f.seek(0)

        reader = csv.reader(f, delimiter=sep)
        headers = next(reader)

        # Find name column
        name_col = None
        for i, h in enumerate(headers):
            if h.strip().lower() in ("name", "sample", "образец", "номер", "id"):
                name_col = i
                break
        if name_col is None:
            name_col = 0

        # Map oxide columns
        oxide_map = {}
        for field in _COLUMN_ALIASES:
            col_idx = _find_column(headers, field)
            if col_idx is not None:
                oxide_map[field] = col_idx

        for row in reader:
            if len(row) <= name_col:
                continue
            name = row[name_col].strip()
            if not name:
                continue

            oxide_data = {}
            for field, col_idx in oxide_map.items():
                try:
                    val = float(row[col_idx].replace(",", ".").strip())
                    oxide_data[field] = val
                except (ValueError, IndexError):
                    oxide_data[field] = 0.0

            samples.append(Sample(
                name=name,
                composition=OxideComposition(**oxide_data),
            ))

    logger.info("Loaded %d samples from XRF CSV: %s", len(samples), path.name)
    return samples


def read_xrf_txt(path: Path) -> list[Sample]:
    """Read XRF data from Bruker-style TXT format."""
    samples = []

    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    # Find header line (contains oxide names)
    header_idx = None
    for i, line in enumerate(lines):
        if "SiO2" in line or "SiO₂" in line or "Si" in line:
            header_idx = i
            break

    if header_idx is None:
        logger.warning("Could not find header in %s", path.name)
        return []

    headers = lines[header_idx].strip().split("\t")
    if len(headers) < 3:
        headers = lines[header_idx].strip().split(";")

    oxide_map = {}
    for field in _COLUMN_ALIASES:
        col_idx = _find_column(headers, field)
        if col_idx is not None:
            oxide_map[field] = col_idx

    name_col = 0

    for line in lines[header_idx + 1:]:
        parts = line.strip().split("\t")
        if len(parts) < 3:
            parts = line.strip().split(";")
        if len(parts) <= name_col:
            continue

        name = parts[name_col].strip()
        if not name:
            continue

        oxide_data = {}
        for field, col_idx in oxide_map.items():
            try:
                val = float(parts[col_idx].replace(",", ".").strip())
                oxide_data[field] = val
            except (ValueError, IndexError):
                oxide_data[field] = 0.0

        samples.append(Sample(
            name=name,
            composition=OxideComposition(**oxide_data),
        ))

    logger.info("Loaded %d samples from XRF TXT: %s", len(samples), path.name)
    return samples


def read_xrf(path: Path) -> list[Sample]:
    """Auto-detect format and read XRF data."""
    fmt = _detect_format(path)
    if fmt == "txt":
        return read_xrf_txt(path)
    return read_xrf_csv(path)
