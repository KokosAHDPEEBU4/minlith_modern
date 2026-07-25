# Changelog

## [0.6.3] — 2026-07-24

### Fixed
- Chart theme: all charts now use `get_bg_color()` / `get_fg_color()` getters (not static imports) — theme switch works immediately
- correlation.py, harker.py, coefficient_heatmap.py, radar_chart.py: no longer hardcode dark colors
- Plotly engine: `_get_layout_template()` reads current theme dynamically

### Changed
- ReportsPage redesigned: visual block constructor with preview, drag-drop reorder, double-click to edit
- Template management: rename, delete, save/load custom templates (JSON)
- Block summary shows type + title + extras (chart type, min wt%)

## [0.6.2] — 2026-07-24

### Added
- Chart theme setting: "Фон диаграмм" in Settings — choose between dark (Catppuccin) and light (white) background
- `set_chart_theme()` / `get_chart_theme()` in matplotlib_engine.py
- All charts now respect the active theme (BG_COLOR, FG_COLOR, GRID_COLOR, ACCENT)
- Theme applied on startup and when settings change

## [0.6.1] — 2026-07-24

### Added
- FilesPage: "Рассчитать все" button — calculates all loaded samples with one click
- ReportsPage: full report customization UI — add/remove/reorder blocks, edit block properties, drag-drop, save/load custom templates
- Block types: Header, Text, Oxide Table, Mineral Table, Parameters, Defect, Chart (10 types), Page Break

### Fixed
- HTML export: `path` converted to `Path` object (was "str has no attribute write_text")
- Matplotlib: Cyrillic font auto-detection for Russian text (no more black squares)

## [0.6.0] — 2026-07-24

### Added
- 8 new matplotlib charts: BoxPlot, Radar, CoefficientHeatmap, DefectAccumulation, PCABiplot, Dendrogram, ParallelCoordinates, Mg-Fe-Al Ternary
- BarChart `stacked=True` and `normalized=True` kwargs
- DefectChart `stacked=True` kwargs
- 10 new Plotly interactive charts: qapf, acnk, afm, heatmap, correlation, kf, boxplot, violin, parallel, rock_type (total 14)
- Total chart count: 23 matplotlib + 14 Plotly = 37

### Fixed
- Correlation: `std==0` now returns NaN instead of 0.0; 1 sample shows placeholder message
- BlandAltman: empty data returns empty figure with grid (not text overlay)
- Plotly interactive_bar: shows all minerals (was hardcoded to 9)
- Plotly interactive_pie: shows all minerals (was hardcoded to 7)

## [0.5.2] — 2026-07-24

### Added
- Undo/redo for oxide composition editing (InputPage) with Ctrl+Z/Ctrl+Y
- `ChangeHistory` class in `src/utils/history.py`
- CLI file-level progress `[i/N] file.xlsx`
- `WORKFLOW.md` — developer documentation

### Fixed
- `main_window.py:49`: version synced to 0.5.2
- `conftest.py:96-97`: bare `except Exception: pass` replaced with `pytest.fail()` with error message
- CLI: file progress now shows `[1/3]` per file, not just per sample

## [0.5.1] — 2026-07-24

### Added
- CLI `--force` flag to bypass cache and force recalculation
- CLI progress display `[i/n]` when calculating multiple samples
- Excel import warnings when required oxide labels are missing (set to 0.0)
- WORKFLOW.md documentation

### Fixed
- `test_cli.py`: encoding fix for Windows cp1251 (now uses UTF-8)

## [0.5.0] — 2026-07-24

### Added
- **Auto-calibration system** (`src/core/calibrator.py`, `calibrate.py`) — reverse-engineers VBA algorithm parameters via `scipy.optimize.differential_evolution`
- `calibration_config.json` — saved calibrated parameters (RMSE 66.15 → 0.09)
- Property-based tests with Hypothesis (26 tests, `tests/test_property.py`)
- Coverage-boost tests for calibrator, cache, CSV, types_logic (`tests/test_coverage_boost.py`)
- pytest-cov integration for coverage measurement

### Fixed
- `src/utils/cache.py`: `time.fromisoformat()` → `datetime.fromisoformat()` (Python has no `time.fromisoformat`)
- `src/database/repository.py:222`: `import DB_PATH` → `import _DB_PATH as DB_PATH` (private variable)
- `src/cli.py:457,493`: `--template` now accepts core/geochemical (was only brief/standard/full)
- `src/core/calculator.py:49`: `timeout=0` now raises `CalculationTimeoutError` (was silently ignored)

## [0.4.0] — 2026-07-23

### Added
- Smart anomaly detector (10 rules: gypsum, low/high sum, iron-rich, apatite, critical defect, carbonate, feldspar anomaly, phosphorus, negative mineral)
- k1-k4 vs F chart (15th chart type) — visualize adaptive chlorite coefficients
- Explainer module — generate human-readable explanations of calculation process
- lru_cache(1024) for calculate_coefficients() — faster repeated calculations
- PyInstaller spec for portable build (minlith.spec)
- LaTeX exporter (publication-ready tables with \textsubscript, booktabs)
- XRF importer — auto-detect Bruker/Panalytical/Rigaku CSV/TXT formats
- 2 new report templates: "core" (отчёт по керну), "geochemical" (геохимический паспорт)
- AnomalyDetector integrated into CalculationResult.anomalies field

## [0.3.0] — 2026-07-23

### Added
- Geochemical parameters (CIA, ICV, PIA, ASI, AI) in calculator + ResultsPage + Excel export
- DebugTraceCollector integrated into Calculator (trace recording at key stages)
- Timeout enforcement via threading (_TimeoutWrapper)
- FormulaUnits.fe1 now populated from original FeO
- Sorting (setSortingEnabled) + search (QLineEdit filter) in ResultsTable and MineralTable
- CLI flags: --verbose, --timeout, --config
- DB backup, export-results-json, import-results-json (CLI subcommands)
- Cache TTL (7 days default), cleanup_expired(), invalidate_config()
- Light theme QSS (light.qss)
- minlith-gui entry point
- New CLI subcommands: backup, export-db, import-db
- Clipboard support (Ctrl+C) in ResultsTable
- Input validation in OxideTable

### Changed
- Version bumped to 0.3.0
- Cache index now tracks timestamps for TTL
- `__init__.py` version synced to 0.3.0

### Fixed
- Cache deserialization (formula_units/coefficients)
- Worker formula/weight deserialization
- History delete_sample (filter().first() instead of deprecated .get())
- CLI report fmt operator precedence
- Settings_page ValueError guard
- Calculator div-by-zero fix
- repository.py: deprecated `.get()` replaced with `session.get()`
- helpers.py: "or" → "or_", "dol" → "dl" field name mapping

## [0.2.0] — 2026-07-22

### Added
- Full MINLITH Modern infrastructure
- 14 chart types (matplotlib + 4 Plotly interactive)
- 3 report templates (brief, standard, full)
- SQLite database with ORM
- GUI: 9 pages (Welcome, Files, Input, Results, Charts, Reports, History, Settings, Logs)
- All UI in Russian
- 58 tests passing
- USAGE_SCENARIOS.md documentation
