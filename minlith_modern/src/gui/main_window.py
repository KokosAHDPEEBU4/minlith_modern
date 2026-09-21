"""Main application window — sidebar navigation + page stack."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.core.calculator import Calculator
from src.core.models import LEGACY_ENGINE_ALIASES, CalculationConfig, Sample
from src.gui.dialogs.calculation_dialog import CalculationDialog
from src.gui.pages.charts_page import ChartsPage
from src.gui.pages.files_page import FilesPage
from src.gui.pages.history_page import HistoryPage
from src.gui.pages.input_page import InputPage
from src.gui.pages.logs_page import LogsPage
from src.gui.pages.output_page import OutputPage
from src.gui.pages.reports_page import ReportsPage
from src.gui.pages.results_page import ResultsPage
from src.gui.pages.settings_page import SettingsPage
from src.gui.pages.welcome_page import WelcomePage
from src.io.excel import save_results
from src.utils.cache import ResultCache
from src.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window with sidebar navigation and stacked pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MINLITH Modern v0.6.8 — Нормативный минералогический расчёт")
        self.setMinimumSize(1100, 650)

        self._config = ConfigManager()
        self._cache = ResultCache()
        self._calculator = self._create_calculator()

        # Apply chart theme from settings
        from src.charts.engines.matplotlib_engine import set_chart_theme
        set_chart_theme(self._config.get("chart_theme", "dark"))

        # ── Тулбар движков расчёта ──
        self._engine_bar = QToolBar("Движки расчёта")
        self._engine_bar.setStyleSheet("QToolBar { spacing: 4px; padding: 4px; }")
        self._engine_bar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._engine_bar)

        self._btn_excel_parity = QToolButton()
        self._btn_excel_parity.setText("Как в Excel")
        self._btn_excel_parity.setCheckable(True)
        self._btn_excel_parity.setToolTip(
            "excel_parity — точный паритет с Excel-версией (без округлений)")
        self._btn_excel_parity.clicked.connect(
            lambda: self._set_engine("excel_parity"))
        self._engine_bar.addWidget(self._btn_excel_parity)

        self._btn_geological_theory = QToolButton()
        self._btn_geological_theory.setText("Геол. теория")
        self._btn_geological_theory.setCheckable(True)
        self._btn_geological_theory.setToolTip(
            "geological_theory — самостоятельная попытка по геологической теории")
        self._btn_geological_theory.clicked.connect(
            lambda: self._set_engine("geological_theory"))
        self._engine_bar.addWidget(self._btn_geological_theory)

        self._btn_python_rework = QToolButton()
        self._btn_python_rework.setText("Python-переработка")
        self._btn_python_rework.setCheckable(True)
        self._btn_python_rework.setToolTip(
            "python_rework — реализация, переработанная под Python (плейсхолдер)")
        self._btn_python_rework.clicked.connect(
            lambda: self._set_engine("python_rework"))
        self._engine_bar.addWidget(self._btn_python_rework)

        self._update_engine_buttons()

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
            ("Вывод", "\U0001f4e2"),
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
        self._files_page.calculate_requested.connect(self._on_calculate_from_files)

        self._input_page = InputPage(self._calculator)
        self._input_page.calculation_done.connect(self._on_calculation_done)
        self._input_page.batch_calculate_requested.connect(self.calculate_batch)

        self._results_page = ResultsPage()
        self._charts_page = ChartsPage()
        self._output_page = OutputPage()
        self._reports_page = ReportsPage()
        self._charts_page.dataChanged.connect(self._output_page.set_data)
        self._apply_zoom_step()

        self._settings_page = SettingsPage(self._config)
        self._settings_page.settings_changed.connect(self._on_settings_changed)
        self._history_page = HistoryPage()
        self._logs_page = LogsPage()

        self._stack.addWidget(self._welcome_page)
        self._stack.addWidget(self._files_page)
        self._stack.addWidget(self._input_page)
        self._stack.addWidget(self._results_page)
        self._stack.addWidget(self._charts_page)
        self._stack.addWidget(self._output_page)
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
        QShortcut(QKeySequence("Ctrl+U"), self, lambda: self._switch_page(5))  # Output
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self._switch_page(6))  # Reports
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
            self, "Экспорт результатов", "minlith_results.xlsx",
            "Excel (*.xlsx);;CSV (*.csv);;JSON (*.json)",
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
                save_results(
                    path, results,
                    include_defect=self._config.get("include_defect", True),
                    include_formula_units=self._config.get("include_formula_units", False),
                    include_parameters=self._config.get("include_parameters", True),
                )
            self.statusBar().showMessage(f"Экспортировано: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    # ── Signal handlers ──

    def _on_samples_loaded(self, samples: list) -> None:
        if samples:
            s = samples[0]
            self._input_page.set_composition(s.composition, s.name)
            self._input_page.set_all_samples(samples)
            self.statusBar().showMessage(f"Загружено: {len(samples)} образцов")

    def _on_calculate_from_files(self, samples: list) -> None:
        self.calculate_batch(samples)

    def _on_calculation_done(self, result) -> None:
        self._results_page.add_result(result)
        self._charts_page.set_results(self._results_page._results)
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
            # Update UI first, then persist in background so the GUI never blocks.
            self._switch_page(3)
            self._charts_page.set_results(dialog.results)
            self._reports_page.set_results(dialog.results)
            self.statusBar().showMessage(f"Рассчитано {len(dialog.results)} образцов")
            self._persist_results(dialog.results)

    def _persist_results(self, results: list) -> None:
        """Save results to DB without blocking the UI thread."""

        def _run(repo_results: list) -> None:
            from src.database.repository import SampleRepository
            repo = SampleRepository()
            for result in repo_results:
                try:
                    repo.save_result(result)
                except Exception as e:
                    logger.warning("Failed to save result to DB: %s", e)

        from PyQt6.QtCore import QThread
        from PyQt6.QtWidgets import QApplication

        class _SaveThread(QThread):  # noqa: N801
            def run(self) -> None:  # type: ignore[override]
                _run(results)

        thread = _SaveThread(self)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._save_thread = thread

    def closeEvent(self, event) -> None:  # noqa: N802  # PyQt override
        geom = self.saveGeometry().toHex().data().decode()
        self._config["window_geometry"] = geom
        self._config.save()
        super().closeEvent(event)

    def _build_config(self) -> CalculationConfig:
        """Build CalculationConfig from ConfigManager settings."""
        return CalculationConfig(
            molar_mass_source=self._config.get("molar_mass_source", "iupac"),
            custom_molar_masses=self._config.get("custom_molar_masses", {}),
            sum_tolerance=tuple(self._config.get("sum_tolerance", [98.0, 102.0])),
            warn_negative=self._config.get("warn_negative", True),
            auto_correct_sum=self._config.get("auto_correct_sum", False),
            decimal_places=self._config.get("decimal_places", 2),
            include_formula_units=self._config.get("include_formula_units", False),
            include_defect=self._config.get("include_defect", True),
            include_parameters=self._config.get("include_parameters", True),
            timeout_seconds=self._config.get("timeout_seconds", 120),
            batch_size=self._config.get("batch_size", "auto"),
            calculation_engine=self._config.get("calculation_engine", "excel_parity"),
        )

    def _create_calculator(self) -> Calculator:
        """Create Calculator with current config and calculation engine."""
        config = self._build_config()
        logger.info("Calculation engine: %s", config.calculation_engine)
        return Calculator(config=config)

    def _apply_zoom_step(self) -> None:
        """Распространить ``chart.zoom_step`` из конфига на страницы диаграмм.

        Шаг применяется мгновенно ко всем существующим плиткам без пересоздания.
        """
        step = self._config.get("chart.zoom_step", 1.2)
        for page in (self._charts_page, self._output_page):
            page._view.set_zoom_step(step)

    def _on_settings_changed(self) -> None:
        """Rebuild calculator and apply all settings immediately."""
        # 0. Apply chart interaction settings (zoom step)
        self._apply_zoom_step()

        # 1. Rebuild calculator with new config
        self._calculator = self._create_calculator()
        self._input_page._calculator = self._calculator
        logger.info("Calculator rebuilt with new settings")

        # 2. Invalidate cache (settings may change results)
        invalidated = self._cache.invalidate_config()
        if invalidated:
            logger.info("Cache invalidated: %d entries removed", invalidated)

        # 3. Apply chart theme
        from src.charts.engines.matplotlib_engine import set_chart_theme
        set_chart_theme(self._config.get("chart_theme", "dark"))

        # 4. Hot-reload theme stylesheet
        from src.main import _resolve_theme_path
        theme = self._config.get("theme", "dark")
        qss_path = _resolve_theme_path(theme)
        if qss_path.exists():
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
                logger.info("Theme reloaded: %s", theme)

        # 5. Clear stale results/charts since config changed
        if self._results_page._results:
            self._results_page.clear()
            self._charts_page.set_data(None)
            self._output_page.set_data(None)
            logger.info("Results cleared due to settings change")

        # 6. Sync engine toolbar buttons with config
        self._update_engine_buttons()

    def _set_engine(self, engine: str) -> None:
        """Переключить движок расчёта из тулбара."""
        self._config["calculation_engine"] = engine
        self._config.save()
        self._on_settings_changed()
        self._update_engine_buttons()
        if hasattr(self._settings_page, "_calculation_engine"):
            self._settings_page._calculation_engine.setCurrentText(engine)

    def _update_engine_buttons(self) -> None:
        """Синхронизировать состояние кнопок тулбара с конфигом."""
        engine = self._config.get("calculation_engine", "excel_parity")
        engine = LEGACY_ENGINE_ALIASES.get(engine, engine)
        self._btn_excel_parity.setChecked(engine == "excel_parity")
        self._btn_geological_theory.setChecked(engine == "geological_theory")
        self._btn_python_rework.setChecked(engine == "python_rework")
