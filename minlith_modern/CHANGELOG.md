# Changelog

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
