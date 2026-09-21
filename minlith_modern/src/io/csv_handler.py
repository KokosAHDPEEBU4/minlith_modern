"""CSV handler — read/write CSV files (separator ;, UTF-8-SIG)."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

OXIDE_FIELDS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]

OXIDE_LABELS = {
    "sio2": "SiO2", "tio2": "TiO2", "al2o3": "Al2O3", "fe2o3": "Fe2O3",
    "feo": "FeO", "mgo": "MgO", "cao": "CaO", "na2o": "Na2O",
    "k2o": "K2O", "p2o5": "P2O5", "mno": "MnO", "c": "C",
    "so3": "SO3", "f": "F", "cl": "Cl", "s": "S", "co2": "CO2", "so": "SO",
}


def read_csv(path: Path, separator: str | None = None) -> list[Sample]:
    """Read samples from CSV file.

    Автоопределение: разделитель (; или ,), кодировка (utf-8, cp1251).
    Поддержка кириллических названий колонок.
    """
    samples = []

    # Auto-detect encoding
    first_line = ""
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                first_line = f.readline()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        enc = "utf-8-sig"

    # Auto-detect separator
    if separator is None:
        separator = ";" if ";" in first_line else ","

    with open(path, encoding=enc) as f:
        reader = csv.DictReader(f, delimiter=separator)
        for row in reader:
            name = row.get("Name", row.get("name", row.get("Образец", row.get("Sample", ""))))
            oxide_data = {}
            for field in OXIDE_FIELDS:
                label = OXIDE_LABELS[field]
                # Try multiple column name variants
                val = (row.get(field) or row.get(label) or
                       row.get(field.upper()) or row.get(field.lower()) or "0")
                try:
                    oxide_data[field] = float(str(val).replace(",", ".")) if val else 0.0
                except (ValueError, TypeError):
                    oxide_data[field] = 0.0

            samples.append(Sample(
                name=name or f"Sample_{len(samples)+1}",
                composition=OxideComposition(**oxide_data),
            ))

    logger.info("Read %d samples from CSV: %s", len(samples), path.name)
    return samples


def write_csv(
    path: Path,
    results: list,
    separator: str = ";",
) -> None:
    """Write calculation results to CSV."""

    mineral_codes = ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                     "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]

    fieldnames = ["Sample", "Type", "F", "A"] + [f"{c}_wt%" for c in mineral_codes]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=separator)
        writer.writeheader()
        for r in results:
            row = {
                "Sample": r.sample_name,
                "Type": int(r.rock_type),
                "F": f"{r.coefficients.F:.4f}",
                "A": f"{r.coefficients.A:.4f}",
            }
            for code in mineral_codes:
                val = getattr(r.minerals_weight, code, 0.0)
                row[f"{code}_wt%"] = f"{val:.2f}"
            writer.writerow(row)

    logger.info("Written %d results to CSV: %s", len(results), path.name)
