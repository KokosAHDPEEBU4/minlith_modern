"""Unit-тесты для src/gui/widgets/zoom_math (чистая математика, без Qt)."""

import math

import pytest

from src.gui.widgets.zoom_math import (
    DEFAULT_ZOOM_STEP,
    ModifierMode,
    anchor_fraction,
    is_categorical_axis,
    modifier_mode,
    normalize_zoom_step,
    pan_lims,
    value_at_fraction,
    zoom_lims,
)

ACC = 1e-12


class TestZoomLims:
    @pytest.mark.parametrize("factor", [1.5, 2.0, 5.0])
    def test_linear_zoom_in_narrows_range(self, factor: float) -> None:
        lo, hi = 0.0, 10.0
        anchor = 5.0
        new_lo, new_hi = zoom_lims((lo, hi), anchor, factor)
        assert new_hi - new_lo < hi - lo
        assert abs(new_lo + new_hi) / 2 - anchor < ACC  # anchor centre preserved

    @pytest.mark.parametrize("factor", [0.5, 0.25, 0.1])
    def test_linear_zoom_out_widens_range(self, factor: float) -> None:
        lo, hi = 0.0, 10.0
        anchor = 5.0
        new_lo, new_hi = zoom_lims((lo, hi), anchor, factor)
        assert new_hi - new_lo > hi - lo

    def test_anchor_fraction_invariant_linear(self) -> None:
        lim = (0.0, 10.0)
        anchor = 3.0
        lo_f = anchor_fraction(anchor, lim)
        for f in (1.5, 0.5):
            nl, nh = zoom_lims(lim, anchor, f)
            assert abs(anchor_fraction(anchor, (nl, nh)) - lo_f) < ACC

    def test_factor_one_returns_same(self) -> None:
        lim = (2.0, 7.0)
        assert zoom_lims(lim, 4.5, 1.0) == lim

    def test_degenerate_range_returns_same(self) -> None:
        assert zoom_lims((5.0, 5.0), 5.0, 2.0) == (5.0, 5.0)

    @pytest.mark.parametrize("bad_factor", [0.0, -1.0, -0.01])
    def test_nonpositive_factor_returns_same(self, bad_factor: float) -> None:
        lim = (1.0, 5.0)
        assert zoom_lims(lim, 3.0, bad_factor) == lim

    def test_min_range_width_linear(self) -> None:
        nl, nh = zoom_lims((0.0, 1.0), 0.5, 1e6, min_range_width=1e-4)
        assert (nl, nh) == (0.0, 1.0)  # clamp: width would be < min

    def test_linear_can_narrow_to_min(self) -> None:
        # factor подбирается так, чтобы новая ширина была чуть больше min
        min_w = 1e-4
        nl, nh = zoom_lims((0.0, 1.0), 0.5, 1.0 / (min_w * 1.1), min_range_width=min_w)
        assert nh - nl == pytest.approx(min_w * 1.1, rel=1e-6)

    def test_log_anchor_invariant(self) -> None:
        lim = (1e2, 1e4)
        anchor = 1e3
        lo_f = (math.log10(anchor) - math.log10(lim[0])) / (
            math.log10(lim[1]) - math.log10(lim[0])
        )
        for f in (1.5, 0.5):
            nl, nh = zoom_lims(lim, anchor, f, log=True)
            assert abs(
                (math.log10(anchor) - math.log10(nl))
                / (math.log10(nh) - math.log10(nl))
                - lo_f
            ) < ACC

    def test_log_fallback_when_lo_zero(self) -> None:
        nl, nh = zoom_lims((0.0, 10.0), 5.0, 2.0, log=True)
        assert nl == pytest.approx(2.5, abs=ACC)
        assert nh == pytest.approx(7.5, abs=ACC)

    def test_log_clamp_to_min_range(self) -> None:
        # min_range_width in log space (decades)
        lim = (1.0, 10.0)
        anchor = 3.0
        # choose factor so that new range would be too narrow
        nl, nh = zoom_lims(lim, anchor, 1e8, log=True, min_range_width=0.5)
        assert nl == 1.0 and nh == 10.0


class TestPanLims:
    def test_pan_right(self) -> None:
        lo, hi = 0.0, 10.0
        plo, phi = pan_lims((lo, hi), 0.1)
        assert abs(plo - 1.0) < ACC and abs(phi - 11.0) < ACC
        assert abs((phi - plo) - (hi - lo)) < ACC  # width preserved

    def test_pan_left(self) -> None:
        lo, hi = 5.0, 15.0
        plo, phi = pan_lims((lo, hi), -0.2)
        assert plo == pytest.approx(3.0)
        assert phi == pytest.approx(13.0)
        assert abs((phi - plo) - 10.0) < ACC

    def test_pan_log(self) -> None:
        lo, hi = 1e2, 1e4
        plo, phi = pan_lims((lo, hi), 1.0, log=True)
        width_before = math.log10(hi) - math.log10(lo)
        width_after = math.log10(phi) - math.log10(plo)
        assert abs(width_before - width_after) < ACC
        assert phi > hi and plo > lo

    def test_pan_log_fallback_to_linear(self) -> None:
        # lo=0 -> linear fallback
        plo, phi = pan_lims((0.0, 10.0), 0.5)
        assert plo == pytest.approx(5.0)
        assert phi == pytest.approx(15.0)

    def test_pan_degenerate(self) -> None:
        assert pan_lims((3.0, 3.0), 0.5) == (3.0, 3.0)


class TestAnchorFraction:
    def test_endpoints(self) -> None:
        lim = (0.0, 10.0)
        assert anchor_fraction(0.0, lim) == pytest.approx(0.0)
        assert anchor_fraction(10.0, lim) == pytest.approx(1.0)

    def test_midpoint(self) -> None:
        assert anchor_fraction(5.0, (0.0, 10.0)) == pytest.approx(0.5)

    def test_degenerate(self) -> None:
        assert anchor_fraction(3.0, (3.0, 3.0)) == pytest.approx(0.5)

    def test_roundtrip(self) -> None:
        lim = (-10.0, 20.0)
        for v in (-5.0, 0.0, 12.5):
            f = anchor_fraction(v, lim)
            assert value_at_fraction(f, lim) == pytest.approx(v)


class TestNormalizeZoomStep:
    def test_valid(self) -> None:
        for v in (1.1, 1.2, 3.0, 5.0):
            assert normalize_zoom_step(v) == v

    def test_boundary(self) -> None:
        assert normalize_zoom_step(1.0 + 1e-12) == pytest.approx(1.0 + 1e-12, rel=1e-6)

    @pytest.mark.parametrize("bad", [1.0, 0.0, -1.0, 7.0, float("inf"), float("nan")])
    def test_out_of_range(self, bad: float) -> None:
        assert normalize_zoom_step(bad) == DEFAULT_ZOOM_STEP


class TestModifierMode:
    def test_none_when_outside_axes(self) -> None:
        class FakeEvent:
            inaxes = None
        assert modifier_mode(FakeEvent()) is ModifierMode.NONE

    def test_no_gui_event_defaults_to_xy(self) -> None:
        class FakeEvent:
            inaxes = True

        setattr(FakeEvent, "guiEvent", None)
        assert modifier_mode(FakeEvent()) is ModifierMode.ZOOM_XY


class TestIsCategoricalAxis:
    def test_with_str_category_locator(self) -> None:
        class FakeLocator:
            pass
        FakeLocator.__name__ = "StrCategoryLocator"

        class FakeAxis:
            def get_major_locator(self):
                return FakeLocator()

        class FakeAxes:
            xaxis = FakeAxis()

        assert is_categorical_axis(FakeAxes(), "x") is True

    def test_with_noncategory_locator(self) -> None:
        class FakeLocator:
            pass

        class FakeAxis:
            def get_major_locator(self):
                return FakeLocator()

        class FakeAxes:
            xaxis = FakeAxis()

        assert is_categorical_axis(FakeAxes(), "x") is False

    def test_invalid_axis_returns_false(self) -> None:
        assert is_categorical_axis(object(), "x") is False
