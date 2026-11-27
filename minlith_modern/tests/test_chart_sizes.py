"""Tests for per-chart display size standards (chart_sizes)."""

from __future__ import annotations

import pytest

from src.gui.widgets.chart_interactions import BUILTIN_TYPE_IDS
from src.gui.widgets.chart_sizes import (
    BUILTIN_SIZE_IDS,
    DEFAULT_SIZE_SPEC,
    STANDARDS,
    ChartSizeSpec,
    aspect_for,
    get_size_spec,
)


def test_registry_covers_all_builtin_types() -> None:
    assert len(BUILTIN_SIZE_IDS) == 8
    assert BUILTIN_SIZE_IDS == BUILTIN_TYPE_IDS
    assert set(STANDARDS) == set(BUILTIN_TYPE_IDS)


@pytest.mark.parametrize("tid", BUILTIN_TYPE_IDS)
def test_spec_values_are_sane(tid: str) -> None:
    spec = STANDARDS[tid]
    if spec.aspect is not None:
        assert spec.aspect > 0
    assert 0 < spec.min_aspect <= spec.max_aspect
    assert 0 < spec.min_height <= spec.max_height
    if spec.max_width is not None:
        assert spec.max_width > 0


def test_unknown_and_none_get_default() -> None:
    assert get_size_spec(None) is DEFAULT_SIZE_SPEC
    assert get_size_spec("__nope__") is DEFAULT_SIZE_SPEC


def test_explicit_aspect_wins() -> None:
    spec = ChartSizeSpec(aspect=1.0, min_aspect=0.5, max_aspect=4.0)
    assert aspect_for(spec, 3.0) == 1.0


def test_native_aspect_is_clamped() -> None:
    spec = ChartSizeSpec(min_aspect=0.8, max_aspect=2.4)
    assert aspect_for(spec, 1.33) == pytest.approx(1.33)
    assert aspect_for(spec, 10.0) == 2.4
    assert aspect_for(spec, 0.1) == 0.8


def test_invalid_native_falls_back_to_max() -> None:
    spec = ChartSizeSpec(min_aspect=0.8, max_aspect=2.4)
    assert aspect_for(spec, None) == 2.4
    assert aspect_for(spec, 0.0) == 2.4
    assert aspect_for(spec, -1.0) == 2.4
