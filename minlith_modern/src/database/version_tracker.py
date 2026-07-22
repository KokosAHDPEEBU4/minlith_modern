"""Version tracker — SHA-256 hash of algorithm code for DB versioning."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Files that define the algorithm
_ALGORITHM_FILES = [
    "src/core/types_logic.py",
    "src/core/coefficients.py",
    "src/core/calculator.py",
]

_CURRENT_HASH: str | None = None


def compute_algorithm_hash(project_root: Path | str | None = None) -> str:
    """Compute SHA-256 hash of algorithm source files."""
    global _CURRENT_HASH
    if _CURRENT_HASH is not None:
        return _CURRENT_HASH

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    hasher = hashlib.sha256()
    for rel_path in sorted(_ALGORITHM_FILES):
        full_path = Path(project_root) / rel_path
        if full_path.exists():
            content = full_path.read_bytes()
            hasher.update(content)
            hasher.update(rel_path.encode())

    _CURRENT_HASH = hasher.hexdigest()[:16]
    logger.debug("Algorithm hash: %s", _CURRENT_HASH)
    return _CURRENT_HASH


def check_validity(
    stored_hash: str,
    project_root: Path | str | None = None,
) -> bool:
    """Check if stored hash matches current algorithm code."""
    current = compute_algorithm_hash(project_root)
    return current == stored_hash


def get_current_version() -> str:
    """Return the current algorithm version string."""
    return f"1.0-{compute_algorithm_hash()}"
