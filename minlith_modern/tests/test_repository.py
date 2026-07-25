"""Tests for database/repository.py — CRUD operations."""

from __future__ import annotations

import pytest

from src.core.models import (
    AdaptiveCoefficients,
    CalculationResult,
    MineralComposition,
    OxideComposition,
    RockType,
    Sample,
)
from src.database.repository import SampleRepository


def _make_sample(name: str = "TestRock") -> Sample:
    return Sample(
        name=name,
        composition=OxideComposition(
            sio2=52.5, al2o3=23.41, feo=8.06, mgo=2.35, cao=0.28,
            na2o=0.94, k2o=3.45, p2o5=0.31,
        ),
    )


def _make_result(name: str = "TestRock") -> CalculationResult:
    return CalculationResult(
        sample_name=name,
        input_composition=_make_sample(name).composition,
        formula_units=None,
        coefficients=AdaptiveCoefficients(k1=4.42, k2=0.0, k3=1.58, k4=2.42, F=0.5, A=0.5),
        rock_type=RockType.TYPE_5,
        minerals_formula=MineralComposition(ab=5.0, q=40.0),
        minerals_weight=MineralComposition(ab=7.82, q=31.38),
        defect={"sio2": 1.0},
        warnings=["test warning"],
    )


@pytest.fixture
def repo():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.database.models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return SampleRepository(session=Session())


class TestSampleRepository:
    def test_save_and_get_sample(self, repo):
        sample = _make_sample("MyRock")
        sid = repo.save_sample(sample)
        assert sid > 0
        loaded = repo.get_sample(sid)
        assert loaded is not None
        assert loaded.name == "MyRock"
        assert loaded.composition.sio2 == 52.5

    def test_list_samples(self, repo):
        repo.save_sample(_make_sample("A"))
        repo.save_sample(_make_sample("B"))
        samples = repo.list_samples()
        assert len(samples) == 2

    def test_delete_sample(self, repo):
        sid = repo.save_sample(_make_sample("ToDelete"))
        repo.delete_sample(sid)
        assert repo.get_sample(sid) is None

    def test_save_and_get_result(self, repo):
        result = _make_result("ResultRock")
        cid = repo.save_result(result)
        assert cid > 0

    def test_search_samples(self, repo):
        repo.save_sample(_make_sample("Alpha"))
        repo.save_sample(_make_sample("Beta"))
        found = repo.search_samples("Alp")
        assert len(found) >= 1

    def test_get_stats(self, repo):
        repo.save_sample(_make_sample("S1"))
        stats = repo.get_stats()
        assert stats["samples"] == 1
