"""Test fixtures — synthetic samples for all rock types + cached results."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.models import OxideComposition, Sample, AdaptiveCoefficients, RockType
from src.core.calculator import Calculator

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── Synthetic samples (realistic oxide compositions) ──

SAMPLES = {
    "quartzite": Sample(
        name="Quartzite",
        composition=OxideComposition(sio2=95.0, al2o3=2.5, fe2o3=0.5, feo=0.3, mgo=0.2, cao=0.1, na2o=0.2, k2o=0.5),
    ),
    "granite": Sample(
        name="Granite",
        composition=OxideComposition(sio2=72.0, al2o3=14.0, fe2o3=1.5, feo=1.0, mgo=0.5, cao=1.5, na2o=3.5, k2o=4.5, p2o5=0.2),
    ),
    "basalt": Sample(
        name="Basalt",
        composition=OxideComposition(sio2=50.0, al2o3=14.5, fe2o3=3.0, feo=9.0, mgo=8.0, cao=10.5, na2o=2.5, k2o=0.5, tio2=1.5, p2o5=0.3),
    ),
    "shale": Sample(
        name="Shale",
        composition=OxideComposition(sio2=58.0, al2o3=18.0, fe2o3=5.0, feo=4.0, mgo=2.5, cao=3.0, na2o=1.5, k2o=3.5, p2o5=0.2, mno=0.08),
    ),
    "limestone": Sample(
        name="Limestone",
        composition=OxideComposition(sio2=5.0, al2o3=1.5, fe2o3=0.5, feo=0.3, mgo=1.0, cao=52.0, na2o=0.1, k2o=0.3),
    ),
    "sandstone": Sample(
        name="Sandstone",
        composition=OxideComposition(sio2=88.0, al2o3=5.0, fe2o3=1.0, feo=0.8, mgo=0.5, cao=1.5, na2o=0.8, k2o=1.2),
    ),
    "t_o2_type5": Sample(
        name="T-O2",
        composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
            p2o5=0.31, mno=0.157502,
        ),
    ),
    "bk1_type1": Sample(
        name="БК-1",
        composition=OxideComposition(
            sio2=52.31, al2o3=16.46, fe2o3=0.92, feo=4.43,
            mgo=0.11, cao=6.80, na2o=8.08, k2o=4.26,
        ),
    ),
    "extreme_high_al": Sample(
        name="Extreme High Al",
        composition=OxideComposition(
            sio2=45.0, al2o3=35.0, fe2o3=2.0, feo=5.0,
            mgo=3.0, cao=1.0, na2o=2.0, k2o=4.0,
        ),
    ),
    "zero_sample": Sample(
        name="Zero",
        composition=OxideComposition(),
    ),
    "negative_kn": Sample(
        name="Negative Kn",
        composition=OxideComposition(
            sio2=60.0, al2o3=20.0, fe2o3=2.0, feo=5.0,
            mgo=3.0, cao=2.0, na2o=3.0, k2o=4.0,
        ),
    ),
}


@pytest.fixture(scope="session")
def all_samples() -> dict[str, Sample]:
    return SAMPLES


@pytest.fixture(scope="session")
def calculator() -> Calculator:
    return Calculator()


@pytest.fixture(scope="session")
def all_results(calculator) -> dict[str, object]:
    """Pre-compute results for all synthetic samples."""
    results = {}
    for key, sample in SAMPLES.items():
        try:
            results[key] = calculator.calculate_single(sample)
        except Exception:
            pass
    return results


@pytest.fixture(scope="session")
def result_list(all_results) -> list:
    return list(all_results.values())


@pytest.fixture(scope="session")
def save_fixtures(all_results) -> None:
    """Save fixture results to JSON for offline testing."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    for key, r in all_results.items():
        data[key] = {
            "name": r.sample_name,
            "rock_type": int(r.rock_type),
            "F": r.coefficients.F,
            "A": r.coefficients.A,
            "minerals": {k: round(v, 4) for k, v in r.minerals_weight.__dict__.items()
                         if not k.startswith("_")},
        }
    (FIXTURES_DIR / "results.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@pytest.fixture(scope="session")
def sample_xlsx_path() -> Path:
    """Path to the real MINLITH1.xlsx for integration tests."""
    return Path(__file__).resolve().parent.parent / "MINLITH1.xlsx"
