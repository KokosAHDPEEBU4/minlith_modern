"""Result cache — avoid re-calculating unchanged files (SHA-256 hash)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.utils.helpers import sha256_file, now_iso

logger = logging.getLogger(__name__)


class ResultCache:
    """Cache calculation results by file SHA-256 hash."""

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".minlith" / "cache"
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index: dict[str, dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                self._index = json.loads(self._index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, file_path: Path | str) -> list[dict] | None:
        """Return cached results for file if hash matches, else None."""
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        file_hash = sha256_file(file_path)
        entry = self._index.get(file_hash)
        if not entry:
            return None

        result_path = self._dir / entry["result_file"]
        if not result_path.exists():
            self._index.pop(file_hash, None)
            return None

        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
            logger.info("Cache hit for %s (hash=%s)", file_path.name, file_hash[:12])
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, file_path: Path | str, results: list) -> None:
        """Store results in cache keyed by file hash."""
        file_path = Path(file_path)
        file_hash = sha256_file(file_path)

        # Serialize results
        from src.core.models import CalculationResult
        data = []
        for r in results:
            if isinstance(r, CalculationResult):
                data.append({
                    "sample_name": r.sample_name,
                    "rock_type": int(r.rock_type),
                    "F": r.coefficients.F,
                    "A": r.coefficients.A,
                    "minerals": {k: v for k, v in r.minerals_weight.__dict__.items()
                                 if not k.startswith("_")},
                    "defect": r.defect,
                })
            elif isinstance(r, dict):
                data.append(r)

        result_file = f"{file_hash}.json"
        result_path = self._dir / result_file
        result_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        self._index[file_hash] = {
            "file": str(file_path.name),
            "result_file": result_file,
            "timestamp": now_iso(),
            "samples": len(results),
        }
        self._save_index()
        logger.info("Cached %d results for %s", len(results), file_path.name)

    def invalidate(self, file_path: Path | str) -> bool:
        """Remove cache entry for a file."""
        file_path = Path(file_path)
        file_hash = sha256_file(file_path) if file_path.exists() else None
        if file_hash and file_hash in self._index:
            entry = self._index.pop(file_hash)
            result_path = self._dir / entry.get("result_file", "")
            if result_path.exists():
                result_path.unlink()
            self._save_index()
            return True
        return False

    def clear(self) -> int:
        """Clear entire cache. Returns number of entries removed."""
        count = len(self._index)
        for entry in self._index.values():
            result_path = self._dir / entry.get("result_file", "")
            if result_path.exists():
                result_path.unlink()
        self._index.clear()
        self._save_index()
        return count

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "entries": len(self._index),
            "cache_dir": str(self._dir),
        }
