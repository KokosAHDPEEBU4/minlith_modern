"""Configuration manager — reads/writes JSON settings."""

from __future__ import annotations

import json
import logging
import threading
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
    "algorithm_mode": "stub",  # "stub" | "custom"
    "theme": "dark",
    "chart_theme": "dark",  # "dark" | "light" — background for charts
    "language": "ru",
    "recent_files": [],
    "max_recent": 10,
    "window_geometry": None,
    "window_state": None,
}


class ConfigManager:
    """Read/write application settings from JSON file.

    Supports debounced saves to avoid excessive disk writes.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            path = Path.home() / ".minlith" / "settings.json"
        self._path = Path(path)
        self._data: dict[str, Any] = {}
        self._dirty = False
        self._debounce_timer: threading.Timer | None = None
        self._debounce_seconds = 1.0
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

    def save(self, debounce: bool = False) -> None:
        """Persist current settings to disk.

        Args:
            debounce: If True, delay save by _debounce_seconds to batch writes.
        """
        if debounce:
            self._dirty = True
            if self._debounce_timer and self._debounce_timer.is_alive():
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                self._debounce_seconds, self._do_save
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()
        else:
            self._do_save()

    def _do_save(self) -> None:
        """Actually write to disk."""
        self._dirty = False
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to save config: %s", e)

    def flush(self) -> None:
        """Force immediate save if dirty."""
        if self._debounce_timer and self._debounce_timer.is_alive():
            self._debounce_timer.cancel()
        if self._dirty:
            self._do_save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def add_recent_file(self, path: str) -> None:
        """Add a file to the recent files list (debounced save)."""
        recent: list[str] = self._data.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        max_recent = self._data.get("max_recent", 10)
        self._data["recent_files"] = recent[:max_recent]
        self.save(debounce=True)

    def reset(self) -> None:
        """Reset settings to defaults, preserving recent files and window state."""
        recent_files = self._data.get("recent_files", [])
        window_geometry = self._data.get("window_geometry")
        window_state = self._data.get("window_state")
        self._data = dict(DEFAULT_CONFIG)
        self._data["recent_files"] = recent_files
        self._data["window_geometry"] = window_geometry
        self._data["window_state"] = window_state
        self.save()

    def validate(self) -> list[str]:
        """Validate current settings. Returns list of error messages (empty = valid)."""
        errors = []
        src = self._data.get("molar_mass_source", "")
        if src not in ("iupac", "minlith"):
            errors.append(f"Unknown molar_mass_source: {src!r}")

        tol = self._data.get("sum_tolerance", [98, 102])
        if not isinstance(tol, (list, tuple)) or len(tol) != 2:
            errors.append("sum_tolerance must be [lo, hi]")
        elif tol[0] >= tol[1]:
            errors.append(f"sum_tolerance[0] ({tol[0]}) must be < [1] ({tol[1]})")

        dp = self._data.get("decimal_places", 2)
        if not isinstance(dp, int) or dp < 0 or dp > 6:
            errors.append(f"decimal_places must be 0-6, got {dp}")

        timeout = self._data.get("timeout_seconds", 120)
        if not isinstance(timeout, int) or timeout < 1:
            errors.append(f"timeout_seconds must be positive, got {timeout}")

        mode = self._data.get("algorithm_mode", "stub")
        if mode not in ("stub", "custom"):
            errors.append(f"Unknown algorithm_mode: {mode!r}")

        theme = self._data.get("theme", "dark")
        if theme not in ("dark", "light"):
            errors.append(f"Unknown theme: {theme!r}")

        chart_theme = self._data.get("chart_theme", "dark")
        if chart_theme not in ("dark", "light"):
            errors.append(f"Unknown chart_theme: {chart_theme!r}")

        lang = self._data.get("language", "ru")
        if lang not in ("ru", "en"):
            errors.append(f"Unknown language: {lang!r}")

        return errors

    def export_settings(self, path: Path | str) -> None:
        """Export current settings to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def import_settings(self, path: Path | str) -> None:
        """Import settings from a JSON file (merges with current)."""
        with open(path, "r", encoding="utf-8") as f:
            imported = json.load(f)
        self._data.update(imported)
        self.save()

    def get_all(self) -> dict[str, Any]:
        """Return all settings as a copy."""
        return dict(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data
