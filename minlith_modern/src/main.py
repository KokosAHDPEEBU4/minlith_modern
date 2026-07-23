"""MINLITH Modern — entry point."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    from src.utils.logger import setup_logging
    from src.utils.config import ConfigManager

    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("MINLITH Modern")
    app.setOrganizationName("MINLITH")

    # Load QSS stylesheet based on theme
    config = ConfigManager()
    theme = config.get("theme", "dark")
    qss_path = Path(__file__).resolve().parent / "gui" / "styles" / f"{theme}.qss"
    if not qss_path.exists():
        qss_path = Path(__file__).resolve().parent / "gui" / "styles" / "default.qss"
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
    main()
