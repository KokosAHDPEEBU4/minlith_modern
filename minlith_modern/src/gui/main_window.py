"""Main application window — sidebar navigation + page stack."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.calculator import Calculator
from src.core.models import Sample
from src.io.excel import load_samples, save_results
from src.utils.config import ConfigManager
from src.gui.pages.welcome_page import WelcomePage
from src.gui.pages.files_page import FilesPage
from src.gui.pages.input_page import InputPage
from src.gui.pages.results_page import ResultsPage
from src.gui.pages.settings_page import SettingsPage
from src.gui.pages.history_page import HistoryPage
from src.gui.pages.charts_page import ChartsPage
from src.gui.pages.reports_page import ReportsPage
from src.gui.pages.logs_page import LogsPage
from src.gui.dialogs.calculation_dialog import CalculationDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window with sidebar navigation and stacked pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MINLITH Modern v0.2.0 — Normative Mineralogy")
        self.setMinimumSize(1100, 650)

        self._config = ConfigManager()
        self._calculator = Calculator()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(2)

        title = QLabel("MINLITH")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa; padding: 8px 4px;")
        sidebar_layout.addWidget(title)

        self._nav_buttons: list[QPushButton] = []
        self._page_names = [
            ("Начало", "\U0001f3e0"),
            ("Файлы", "\U0001f4c2"),
            ("Ввод", "\u270f\ufe0f"),
            ("Результаты", "\U0001f4ca"),
            ("Диаграммы", "\U0001f4c8"),
            ("Отчёты", "\U0001f4c4"),
            ("История", "\U0001f4c1"),
            ("Настройки", "\u2699\ufe0f"),
            ("Журнал", "\U0001f4dd"),
        ]

        for label, icon in self._page_names:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setCheckable(True)
            btn.setObjectName("nav_btn")
            self._nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for i, btn in enumerate(self._nav_buttons):
            self._nav_group.addButton(btn, i)
            btn.clicked.connect(lambda checked, idx=i: self._switch_page(idx))

        main_layout.addWidget(sidebar)

        # ── Pages ──
        self._stack = QStackedWidget()

        self._welcome_page = WelcomePage()
        self._welcome_page.open_files.connect(lambda: self._switch_page(1))

        self._files_page = FilesPage(self._config)
        self._files_page.samples_loaded.connect(self._on_samples_loaded)

        self._input_page = InputPage(self._calculator)
        self._input_page.calculation_done.connect(self._on_calculation_done)

        self._results_page = ResultsPage()
        self._charts_page = ChartsPage()
        self._reports_page = ReportsPage()
        self._settings_page = SettingsPage(self._config)
        self._history_page = HistoryPage()
        self._logs_page = LogsPage()

        self._stack.addWidget(self._welcome_page)
        self._stack.addWidget(self._files_page)
        self._stack.addWidget(self._input_page)
        self._stack.addWidget(self._results_page)
        self._stack.addWidget(self._charts_page)
        self._stack.addWidget(self._reports_page)
        self._stack.addWidget(self._history_page)
        self._stack.addWidget(self._settings_page)
        self._stack.addWidget(self._logs_page)

        main_layout.addWidget(self._stack)

        # Default to Welcome page
        self._switch_page(0)

        # ── Keyboard shortcuts ──
        QShortcut(QKeySequence("Ctrl+O"), self, self._files_page._on_import_click)
        QShortcut(QKeySequence("Ctrl+S"), self, self._on_save)
        QShortcut(QKeySequence("Ctrl+E"), self, lambda: self._switch_page(1))  # Files
        QShortcut(QKeySequence("Ctrl+I"), self, lambda: self._switch_page(2))  # Input
        QShortcut(QKeySequence("Ctrl+R"), self, lambda: self._switch_page(3))  # Results
        QShortcut(QKeySequence("Ctrl+D"), self, lambda: self._switch_page(4))  # Charts
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self._switch_page(5))  # Reports
        QShortcut(QKeySequence("F5"), self, self._input_page._on_calculate)

        # Status bar
        self.statusBar().showMessage("Готово")

        # Restore geometry
        geom = self._config.get("window_geometry")
        if geom:
            try:
                self.restoreGeometry(bytes.fromhex(geom))
            except Exception:
                pass

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    def _on_save(self) -> None:
        """Ctrl+S — quick export results."""
        results = self._results_page._results
        if not results:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export results", "minlith_results.xlsx",
            "Excel Files (*.xlsx);;CSV (*.csv);;JSON (*.json)",
        )
        if not path:
            return
        try:
            if path.endswith(".csv"):
                from src.io.csv_handler import write_csv
                write_csv(path, results)
            elif path.endswith(".json"):
                from src.io.excel import save_results_json
                save_results_json(path, results)
            else:
                save_results(path, results)
            self.statusBar().showMessage(f"Экспортировано: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    # ── Signal handlers ──

    def _on_samples_loaded(self, samples: list) -> None:
        if samples:
            s = samples[0]
            self._input_page.set_composition(s.composition, s.name)
            self.statusBar().showMessage(f"Загружен: {s.name}")

    def _on_calculation_done(self, result) -> None:
        self._results_page.add_result(result)
        chart_data = self._charts_page.build_data_from_results(self._results_page._results)
        self._charts_page.set_data(chart_data)
        self._reports_page.set_results(self._results_page._results)
        self._switch_page(3)  # Results
        self.statusBar().showMessage(
            f"{result.sample_name} -> {result.rock_type.name}  "
            f"(F={result.coefficients.F:.3f})"
        )

    # ── Batch calculation ──

    def calculate_batch(self, samples: list[Sample]) -> None:
        if not samples:
            return
        dialog = CalculationDialog(self._calculator, samples, self)
        if dialog.exec():
            for result in dialog.results:
                self._results_page.add_result(result)
                try:
                    from src.database.repository import SampleRepository
                    repo = SampleRepository()
                    repo.save_result(result)
                except Exception as e:
                    logger.warning("Failed to save result to DB: %s", e)
            self._switch_page(3)
            chart_data = self._charts_page.build_data_from_results(dialog.results)
            self._charts_page.set_data(chart_data)
            self._reports_page.set_results(dialog.results)
            self.statusBar().showMessage(f"Рассчитано {len(dialog.results)} образцов")

    def closeEvent(self, event) -> None:
        geom = self.saveGeometry().toHex().data().decode()
        self._config["window_geometry"] = geom
        self._config.save()
        super().closeEvent(event)
