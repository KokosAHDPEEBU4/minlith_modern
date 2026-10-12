"""MINLITH Modern — entry point."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _resolve_theme_path(theme: str) -> Path:
    """Resolve theme name to QSS file path (работает и в PyInstaller-сборке)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "gui" / "styles",          # запуск из исходников (src/main.py)
        here / "src" / "gui" / "styles",  # frozen: main.py в корне _MEIPASS
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "src" / "gui" / "styles")

    for base in candidates:
        themed = base / f"{theme}.qss"
        if themed.exists():
            return themed
        default = base / "default.qss"
        if default.exists():
            return default
    return here / "gui" / "styles" / "default.qss"


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    from src.utils.config import ConfigManager
    from src.utils.logger import setup_logging

    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("MINLITH Modern")
    app.setOrganizationName("MINLITH")

    # Load QSS stylesheet based on theme
    config = ConfigManager()
    theme = config.get("theme", "dark")
    qss_path = _resolve_theme_path(theme)
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # Initialize database
    try:
        from src.database.engine import init_db
        init_db()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Database init failed: %s", e)

    from src.gui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # В PyInstaller-сборке дочерние процессы ProcessPoolExecutor стартуют как
    # повторный запуск exe; freeze_support() обязан выполниться первым, иначе
    # вместо расчёта каждый воркер открывает новое окно приложения.
    import multiprocessing

    multiprocessing.freeze_support()
    main()
