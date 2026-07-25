"""History — undo/redo support for oxide composition editing."""

from __future__ import annotations

import copy
from collections import deque

from src.core.models import OxideComposition


class ChangeHistory:
    """Maintains undo/redo stacks of OxideComposition states."""

    def __init__(self, max_size: int = 50) -> None:
        self._undo_stack: deque[OxideComposition] = deque(maxlen=max_size)
        self._redo_stack: deque[OxideComposition] = deque(maxlen=max_size)
        self._suppress = False

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def push(self, state: OxideComposition) -> None:
        """Record current state (call before changing)."""
        if self._suppress:
            return
        self._undo_stack.append(copy.deepcopy(state))
        self._redo_stack.clear()

    def undo(self, current: OxideComposition) -> OxideComposition | None:
        """Restore previous state. Returns restored state or None."""
        if not self._undo_stack:
            return None
        self._redo_stack.append(copy.deepcopy(current))
        restored = self._undo_stack.pop()
        return restored

    def redo(self, current: OxideComposition) -> OxideComposition | None:
        """Restore next state. Returns restored state or None."""
        if not self._redo_stack:
            return None
        self._undo_stack.append(copy.deepcopy(current))
        restored = self._redo_stack.pop()
        return restored

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def suppress(self, flag: bool) -> None:
        """Suppress recording (for programmatic changes)."""
        self._suppress = flag
