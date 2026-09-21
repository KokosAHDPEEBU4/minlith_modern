"""Result cache — avoid re-calculating unchanged files (SHA-256 hash)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from src.utils.helpers import now_iso, sha256_file

logger = logging.getLogger(__name__)

# Default TTL: 7 days in seconds
DEFAULT_TTL = 7 * 24 * 3600


class ResultCache:
    """Cache calculation results by file SHA-256 hash."""

    def __init__(self, cache_dir: Path | str | None = None, ttl_seconds: int = DEFAULT_TTL) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".minlith" / "cache"
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._index: dict[str, dict] = {}
        self._ttl = ttl_seconds
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
        """Return cached results for file if hash matches and not expired."""
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        file_hash = sha256_file(file_path)
        entry = self._index.get(file_hash)
        if not entry:
            return None

        # TTL check
        if self._ttl > 0 and "timestamp" in entry:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                age = time.time() - entry_time.timestamp()
                if age > self._ttl:
                    self.invalidate(file_path)
                    logger.info("Cache expired for %s (age=%.0fs)", file_path.name, age)
                    return None
            except (ValueError, TypeError):
                pass

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
        # Fields derived from other minerals (always 0, excluded from cache)
        derived = frozenset({"pl", "fsp", "pel", "pel_fsp", "carsd", "ill_kn", "chl_mm_srp"})

        data = []
        for r in results:
            if isinstance(r, CalculationResult):
                data.append({
                    "sample_name": r.sample_name,
                    "rock_type": int(r.rock_type),
                    "F": r.coefficients.F,
                    "A": r.coefficients.A,
                    "minerals": {k: v for k, v in r.minerals_weight.__dict__.items()
                                 if not k.startswith("_") and k not in derived},
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
            "ttl_seconds": self._ttl,
        }

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        if self._ttl <= 0:
            return 0
        expired_keys = []
        now = time.time()
        for file_hash, entry in self._index.items():
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                age = now - entry_time.timestamp()
                if age > self._ttl:
                    expired_keys.append(file_hash)
            except (ValueError, TypeError, KeyError):
                continue
        for key in expired_keys:
            entry = self._index.pop(key, None)
            if entry:
                result_path = self._dir / entry.get("result_file", "")
                if result_path.exists():
                    result_path.unlink()
        if expired_keys:
            self._save_index()
            logger.info("Cleaned up %d expired cache entries", len(expired_keys))
        return len(expired_keys)

    def invalidate_config(self) -> int:
        """Invalidate all cache entries (e.g., when config changes)."""
        count = self.clear()
        logger.info("Invalidated entire cache (%d entries) due to config change", count)
        return count
