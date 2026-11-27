"""Single source for building ChartData from calculation results.

Используется GUI (страница диаграмм), отчётами (chart_renderer) и CLI.
"""

from __future__ import annotations

import numpy as np

from src.charts.base import ChartData
from src.core.models import CalculationResult

MINERAL_FIELDS = [
    "ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
    "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl",
]

OXIDE_FIELDS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "co2",
]

MINERAL_LABELS: dict[str, str] = {
    "ab": "Альбит",
    "an": "Анортит",
    "or_": "Ортоклаз",
    "q": "Кварц",
    "ill": "Иллит",
    "chl": "Хлорит",
    "kn": "Каолинит",
    "mm": "Монтмориллонит",
    "gb": "Гиббсит",
    "ap": "Апатит",
    "cc": "Кальцит",
    "dl": "Доломит",
    "ank": "Анкерит",
    "rch": "Родохрозит",
    "sd": "Сидерит",
    "srp": "Серпентин",
    "mst": "Магнезит",
    "ht": "Гематит",
    "prl": "Пиролюзит",
}


def visible_mineral_fields(
    data: ChartData, threshold: float = 0.01
) -> list[str]:
    """Return mineral fields that actually occur in at least one sample.

    Zero-only rows (e.g. magnetite in a quartz arenite) made legends and
    heatmaps unreadable; charts should show only minerals present in the data.
    """
    fields: list[str] = []
    for field, values in data.minerals_wt.items():
        if len(values) == 0:
            continue
        try:
            peak = float(np.nanmax(np.abs(np.asarray(values, dtype=float))))
        except (TypeError, ValueError):
            continue
        if peak > threshold:
            fields.append(field)
    return fields


def mineral_label(field: str) -> str:
    """Human-readable Russian label for a mineral field."""
    return MINERAL_LABELS.get(field, field)


def mineral_series(
    data: ChartData, field: str, n_samples: int
) -> np.ndarray:
    """Return a mineral series padded/truncated to ``n_samples``."""
    values = np.asarray(data.minerals_wt.get(field, []), dtype=float)
    if values.size >= n_samples:
        return values[:n_samples]
    return np.pad(values, (0, n_samples - values.size))


def build_chart_data(results: list[CalculationResult]) -> ChartData:
    """Build a full ``ChartData`` from a list of calculation results."""
    data = ChartData(sample_names=[r.sample_name for r in results])

    for field in MINERAL_FIELDS:
        data.minerals_wt[field] = np.array(
            [float(getattr(r.minerals_weight, field, 0.0)) for r in results],
            dtype=float,
        )

    for field in OXIDE_FIELDS:
        data.oxides[field] = np.array(
            [float(getattr(r.input_composition, field, 0.0)) for r in results],
            dtype=float,
        )

    data.rock_types = [int(r.rock_type) for r in results]

    if results and results[0].defect:
        for oxide in results[0].defect:
            data.defect[oxide] = np.array(
                [float(r.defect.get(oxide, 0.0)) for r in results],
                dtype=float,
            )

    data.F_values = [float(r.coefficients.F) for r in results]
    data.A_values = [float(r.coefficients.A) for r in results]
    data.metadata["k_values"] = {
        "k1": [float(r.coefficients.k1) for r in results],
        "k2": [float(r.coefficients.k2) for r in results],
        "k3": [float(r.coefficients.k3) for r in results],
        "k4": [float(r.coefficients.k4) for r in results],
    }
    return data
