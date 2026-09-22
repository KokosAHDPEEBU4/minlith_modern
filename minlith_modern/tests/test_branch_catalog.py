"""Тесты статического каталога решений (этап 1).

Проверяют:
  * уникальность id решений и id веток внутри решения;
  * у каждого решения >= 2 ветки;
  * ветки MUST-решений совпадают с ключами соответствующего ``*_INFO``
    в ``branches.py`` (защита от рассинхрона);
  * каталог сериализуется в JSON через ``catalog_to_dict()``.
"""
import json

import pytest

from src.core.excel_parity.branch_catalog import (
    DECISIONS,
    BranchInfo,
    DecisionSpec,
    branch_ids,
    catalog_to_dict,
    find_decision,
)
from src.core.excel_parity.branches import (
    COEFFICIENT_BAND_INFO,
    ROCK_TYPE_INFO,
    STAGE_VI_INFO,
)


def test_decision_ids_unique():
    ids = list(DECISIONS)
    assert len(ids) == len(set(ids))


def test_branch_ids_unique_within_decision():
    for spec in DECISIONS.values():
        ids = [b.id for b in spec.branches]
        assert len(ids) == len(set(ids)), spec.id


def test_each_decision_has_at_least_two_branches():
    for spec in DECISIONS.values():
        assert len(spec.branches) >= 2, spec.id


def test_coefficient_band_ids_match_info():
    assert branch_ids("coefficient_band") == tuple(COEFFICIENT_BAND_INFO)


def test_coefficient_band_branch_payload():
    spec = find_decision("coefficient_band")
    assert spec.overridable is True
    assert spec.stage == "stage0"
    for b in spec.branches:
        cond, src = COEFFICIENT_BAND_INFO[b.id]
        assert b.condition == cond
        assert b.source == src


def test_rock_type_ids_match_info():
    assert branch_ids("rock_type") == tuple(str(n) for n in sorted(ROCK_TYPE_INFO))


def test_rock_type_branch_payload():
    spec = find_decision("rock_type")
    assert spec.overridable is True
    assert spec.stage == "stage0"
    for b in spec.branches:
        n = int(b.id)
        cond, src = ROCK_TYPE_INFO[n]
        assert b.condition == cond
        assert b.source == src
        assert "Тип" in b.title


def test_stage_vi_ids_match_info():
    assert branch_ids("stage_vi") == tuple(STAGE_VI_INFO)


def test_stage_vi_branch_payload():
    spec = find_decision("stage_vi")
    assert spec.overridable is True
    assert spec.stage == "stage_vi"
    for b in spec.branches:
        cond, src = STAGE_VI_INFO[b.id]
        assert b.condition == cond
        assert b.source == src


def test_find_decision_unknown_raises():
    with pytest.raises(KeyError):
        find_decision("no_such_decision")


def test_branch_ids_unknown_raises():
    with pytest.raises(KeyError):
        branch_ids("no_such_decision")


def test_catalog_to_dict_serializes_to_json():
    text = json.dumps(catalog_to_dict(), ensure_ascii=False)
    assert "coefficient_band" in text
    assert "rock_type" in text
    assert "stage_vi" in text
    assert len(catalog_to_dict()["decisions"]) == len(DECISIONS)


def test_catalog_to_dict_matches_decisions():
    ids = {d["id"] for d in catalog_to_dict()["decisions"]}
    assert ids == set(DECISIONS)


def test_decisions_are_frozen_dataclasses():
    for spec in DECISIONS.values():
        assert isinstance(spec, DecisionSpec)
        assert isinstance(spec.branches, tuple)
        for b in spec.branches:
            assert isinstance(b, BranchInfo)
