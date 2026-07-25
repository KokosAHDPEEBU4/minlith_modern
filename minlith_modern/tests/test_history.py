"""Tests for ChangeHistory — undo/redo."""

from __future__ import annotations

from src.core.models import OxideComposition
from src.utils.history import ChangeHistory


class TestChangeHistory:
    def test_push_and_undo(self):
        h = ChangeHistory()
        s1 = OxideComposition(sio2=50.0, al2o3=20.0)
        s2 = OxideComposition(sio2=55.0, al2o3=22.0)

        h.push(s1)
        result = h.undo(s2)
        assert result is not None
        assert result.sio2 == 50.0
        assert result.al2o3 == 20.0

    def test_undo_empty(self):
        h = ChangeHistory()
        s = OxideComposition(sio2=50.0)
        result = h.undo(s)
        assert result is None

    def test_redo(self):
        h = ChangeHistory()
        s1 = OxideComposition(sio2=50.0)
        s2 = OxideComposition(sio2=55.0)

        h.push(s1)
        h.push(s2)
        # undo s2 (pass current=s3)
        s3 = OxideComposition(sio2=60.0)
        restored = h.undo(s3)
        assert restored is not None
        assert restored.sio2 == 55.0  # returns s2
        # redo: restores s3 (the state we passed to undo)
        restored2 = h.redo(OxideComposition())
        assert restored2 is not None
        assert restored2.sio2 == 60.0  # returns s3

    def test_redo_empty(self):
        h = ChangeHistory()
        result = h.redo(OxideComposition())
        assert result is None

    def test_new_push_clears_redo(self):
        h = ChangeHistory()
        s1 = OxideComposition(sio2=50.0)
        s2 = OxideComposition(sio2=55.0)
        s3 = OxideComposition(sio2=60.0)

        h.push(s1)
        h.push(s2)
        h.undo(s3)
        # push new state — redo should be cleared
        h.push(OxideComposition(sio2=70.0))
        result = h.redo(OxideComposition())
        assert result is None

    def test_clear(self):
        h = ChangeHistory()
        h.push(OxideComposition(sio2=50.0))
        h.push(OxideComposition(sio2=55.0))
        h.clear()
        assert not h.can_undo
        assert not h.can_redo

    def test_suppress(self):
        h = ChangeHistory()
        h.suppress(True)
        h.push(OxideComposition(sio2=50.0))
        assert not h.can_undo
        h.suppress(False)

    def test_can_undo_redo(self):
        h = ChangeHistory()
        assert not h.can_undo
        assert not h.can_redo
        h.push(OxideComposition(sio2=50.0))
        assert h.can_undo
        assert not h.can_redo
