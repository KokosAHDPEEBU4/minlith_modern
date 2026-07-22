"""ZIP archive handler — load samples from .zip containing .xlsx/.csv files."""

from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

from src.core.models import Sample

logger = logging.getLogger(__name__)


def load_samples_from_zip(path: str | Path) -> list[Sample]:
    """Load samples from all .xlsx/.csv files inside a ZIP archive.

    Supports nested ZIPs one level deep. Returns combined sample list.
    """
    from src.io.excel import load_samples
    from src.io.csv_handler import read_csv

    path = Path(path)
    samples: list[Sample] = []

    if not zipfile.is_zipfile(path):
        raise ValueError(f"Not a valid ZIP file: {path.name}")

    with tempfile.TemporaryDirectory(prefix="minlith_zip_") as tmp:
        with zipfile.ZipFile(str(path), "r") as zf:
            zf.extractall(tmp)

        tmp_path = Path(tmp)
        extensions = {".xlsx", ".xls", ".csv"}

        for f in sorted(tmp_path.rglob("*")):
            if f.suffix.lower() not in extensions:
                continue
            try:
                if f.suffix.lower() in (".xlsx", ".xls"):
                    loaded = load_samples(f)
                else:
                    loaded = read_csv(f)
                samples.extend(loaded)
                logger.info("Loaded %d samples from %s (inside zip)", len(loaded), f.name)
            except Exception as e:
                logger.warning("Failed to load %s from zip: %s", f.name, e)

    logger.info("Loaded %d total samples from %s", len(samples), path.name)
    return samples
