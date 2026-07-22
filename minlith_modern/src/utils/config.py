"""Configuration manager — reads/writes JSON settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "molar_mass_source": "iupac",
    "sum_tolerance": [98.0, 102.0],
    "warn_negative": True,
    "auto_correct_sum": False,
    "decimal_places": 2,
    "include_formula_units": False,
    "include_defect": True,
    "timeout_seconds": 120,
    "theme": "dark",
    "language": "ru",
    "recent_files": [],
    "max_recent": 10,
    "window_geometry": None,
    "window_state": None,
}


class ConfigManager:
    """Read/write application settings from JSON file."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            path = Path.home() / ".minlith" / "settings.json"
        self._path = Path(path)
        self._data: dict[str, Any] = {}
        self.load()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        """Load settings from disk, falling back to defaults."""
        self._data = dict(DEFAULT_CONFIG)
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load config from %s: %s", self._path, e)

    def save(self) -> None:
        """Persist current settings to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to save config: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def add_recent_file(self, path: str) -> None:
        """Add a file to the recent files list."""
        recent: list[str] = self._data.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        max_recent = self._data.get("max_recent", 10)
        self._data["recent_files"] = recent[:max_recent]
        self.save()
