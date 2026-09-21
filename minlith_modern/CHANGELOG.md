# Changelog

## [0.7.0] — 2026-09-21

### Changed
- **Стилевая чистка кода:** ruff `check` (src + tests) приведён к нулю ошибок по правилам E/F/I/N/W/UP — авто-исправления `ruff --fix`, явные ренеймы по PEP8 (`A/F` → `a_vals`/`f_vals`, `F_values` → `f_vals`, `_DERIVED` → `derived`, `_output_to_mineralComposition` → `_output_to_mineral_composition` и др.), перенос длинных строк; для публичных доменных параметров `F`/`A` (коэффициенты, модели, мапперы) и Qt-оверрайдов drag & drop добавлены `per-file-ignores`; для тестов файл-исключения `N801`/`N802`/`N803`/`N806`
- **Переименование движков расчёта в понятные имена:** ключ `algorithm_mode` → `calculation_engine`, значения `clean|stub|custom` → `excel_parity|geological_theory|python_rework`; пакет `clean_engine` → `excel_parity`, класс `CleanEngineAlgorithm` → `ExcelParityAlgorithm`, модуль `theory_algorithm.py` → `geological_theory.py`, класс `TheoryAlgorithm` → `GeologicalTheoryAlgorithm`; GUI-тулбар «Движки расчёта» (`_set_engine`, кнопки «Как в Excel» / «Геол. теория» / «Python-переработка»), CLI `--engine/-e`; старые ключ `algorithm_mode` и значения `clean`/`stub`/`custom` мигрируют автоматически
- **Полный паритет с Excel-движком:** `excel_parity` == `excel_port(rounding=False)` на всей решётке 16000/16000 (n_ok=16000, n_gap=0, n_mis=0) — устранены все расхождения по типам T-1/T-2 и дефектам
- База данных: потокобезопасный пул `NullPool`, CRUD-репозиторий (`src/database/repository.py`), мапперы domain ↔ db
- Валидация настроек `ConfigManager`: `include_*`, `batch_size`, `custom_molar_masses`
- Отчёты: единое построение `ChartData` и рендера диаграмм (было: 3 дублирующихся билдера с разным набором полей → превью и экспорт могли расходиться); ликвидированы хрупкие подборы плагинов по имени
- Диаграммы: построение `ChartData` вынесено в `src/charts/data_builder.py` (единая точка для GUI, отчётов и CLI); GUI-билдер также заполняет `metadata["k_values"]` — исправлен латентный баг: «Коэффициенты хлорита vs F» и Coefficient Heatmap из GUI не отрисовывались
- **Рефакторинг plotly_charts.py:** каждая интерактивная диаграмма разделена на `fig_*` (билдер фигуры, возвращает `go.Figure`) и `interactive_*` (обёртка для standalone HTML). Добавлен реестр `PLOTLY_FIG_BUILDERS` — позволяет объединять несколько диаграмм в один HTML-отчёт
- **Plotly-экспорт:** `export_plotly_html()` теперь принимает `str | list[str]` — при выборе нескольких диаграмм генерируется единый HTML-файл со сводкой
- **Mineral Radar:** запрещён зум/pan для radar-диаграммы; адаптивные подписи тиков при малых значениях
- **Harker:** увеличен figsize, шрифты, точки `s=62`, суptitle; широкие диаграммы занимают всю строку сетки (`FULL_WIDTH_TYPE_IDS`)
- **Дата/время в сохранениях:** штамп генерации (`_now_stamp`, `_savefig_with_stamp`) в именах файлов PNG/SVG/PDF и подписях пер-tile экспорта
- **Блок выбора минералов:** боковая панель MultiChartView — чекбоксы 19 минералов (из `MINERAL_LABELS`), кнопки «Все/Снять»; рендер и экспорт фильтруют только отмеченные минералы; `set_data` заполняет минералы автоматически из ненулевых

### Added
- GUI: выбор образцов для диаграмм — `SampleSelectorDialog` (все/снять/инверсия), обновление по сигналу от страницы результатов
- GUI: кнопка «Экспорт LaTeX» на странице отчётов
- GUI: опции экспорта результата `include_formula_units` / `include_parameters` / `include_defect` на страницах Ввод → Результаты
- Настройки расчёта: `batch_size` (запуск только через CLI)
- Документация: `docs/CHART_ZOOM.md`, `docs/CHART_INTERACTIONS_*` — интерактивный зум и взаимодействия с диаграммами
- Отчёты: диаграммы встраиваются в HTML (раньше — только Word/PDF); единый рендер `src/reports/chart_renderer.py`
- GUI: в списке шаблонов отчётов все 5 пресетов (ранее 3): + «Керн», «Геохимический паспорт»
- GUI: экспорт интерактивных Plotly-диаграмм (все 14) — кнопка «Интерактивный HTML…» на странице диаграмм (`src/gui/pages/charts_page.py`), обёртка `export_plotly_html()` в `src/charts/engines/plotly_engine.py` + русские подписи `PLOTLY_LABELS`
- GUI: редизайн страницы настроек (`src/gui/pages/settings_page.py`) — сайдбар-навигация по секциям (Расчёт / Экспорт / Диаграммы / Интерфейс), карточки с описаниями, поиск настроек, тумблеры-переключатели, toast при сохранении/сбросе, QSS-тема адаптируется под светлый/тёмный режим (идеи из прототипов «эдавыбджа.py» / «Новый текстовый документ.html»)
- GUI: наполнение секции «Настройки» переструктурировано — Расчёт разбит на карточки «Основные параметры» / «Допуски и точность» / «Пользовательские молярные массы», тумблеры без дублирования текста, у всех строк подписи, тултипы и единый выравнивание контролов вправо; тумблеры — капсула 34×18 с белым ползунком (PNG генерируется под тему), отступы карточек/контента приведены к гайдлайну
- GUI: страница «Файлы» — список образцов стал отмечаемым галочками; добавлен чекбокс «Выбрать все» (с частичным состоянием); «Рассчитать все» считает только отмеченные образцы, при пустом выборе — подсказка
- **GUI: вкладки диаграмм** — `QTabWidget` с кнопкой «+» (closable, movable), каждая вкладка содержит независимый `MultiChartView` со своим набором минералов
- **GUI: мультивыбор Plotly-диаграмм** — диалог «Интерактивный HTML (Plotly)» с чекбоксами всех 14 типов и «Выбрать все/Снять все»; выбранные диаграммы объединяются в один HTML-отчёт
- **HTML-отчёт со сводкой** — блок «Дата и время генерации», «Анализируемых образцов», «Использованные минералы» (из `MINERAL_LABELS`), «Диаграммы в отчёте»
- **`MINERAL_LABELS`** — 19 минералов с русскими краткими названиями (`src/charts/data_builder.py`), переиспользуются в GUI и HTML-сводке
- Тесты: `tests/test_report_generators.py` (18 шт.) — шаблоны, рендер диаграмм, экспорт HTML/Word/PDF
- Тесты: `tests/test_chart_export.py` (19 шт.) — экспорт всех 14 Plotly-диаграмм в HTML, мультивыбор, пустой список, частично неизвестные типы, полнота `PLOTLY_LABELS`
- Тесты: `tests/test_calculation_engine.py` (4 шт.) — имена/алиасы движков, разрешение `excel_parity`/`geological_theory`, обратная совместимость `clean`, миграция старого ключа `algorithm_mode`

### Removed
- Legacy-заглушки `src/core/algorithm_stub.py` (невалидный Python: сырой текст без `#`) и `src/core/algorithm_real.py` — перенесены в `_trash/minlith_modern/src/core/`; убраны из `src/core/__init__.py` и из `hidden-import` в `scripts/build.py`

## [0.6.8] — 2026-07-24

### Added
- `tests/test_charts.py` — 29 tests for all 23 matplotlib chart plugins (render without errors, empty data handling, stacked/grouped/sample variants)
- `tests/test_plotly_charts.py` — 14 tests for all Plotly interactive charts (HTML file creation, content validation, empty data handling)

### Fixed
- Plotly ternary charts (QAPF, A-CN-K, AFM): `fig.update_ternary()` → `fig.update_layout(ternary=...)` (Plotly 6.x API)

## [0.6.7] — 2026-07-24

### Fixed
- P0: `_build_chart_data()` now adds `k_values` to `metadata` — CoefficientHeatmap renders in preview
- P0: QAPF Plotly formula fixed — A=Ab+Or, P=An (was incorrectly including An in A)
- P1: AFM Plotly formula fixed — now matches matplotlib version (Irvine & Baragar 1971): A=Na₂O+K₂O, F=FeOᵀ+MgO
- P1: Removed duplicate imports in 5 chart files (coefficient_heatmap, radar_chart, harker, correlation, heatmap)
- P1: Chart preview now uses `get_name()` lookup instead of fragile magic indices `BUILTIN_CHARTS[N]`
- P2: `pca_biplot.py` — added `n_minerals >= 2` check to prevent singular matrix error

## [0.6.6] — 2026-07-24

### Fixed
- Arrow buttons for block reorder: now show "▲ Вверх" and "▼ Вниз" labels (fixed width 80px)
- Report preview now renders charts as base64 PNG images in real-time
- Each CHART block in the template shows its actual diagram in the preview

### Changed
- ReportsPage: preview includes embedded charts (bar, pie, defect, boxplot, heatmap, correlation, harker, qapf, tas, radar)
- Chart rendering is lazy — only shown in preview, not on page load

## [0.6.5] — 2026-07-24

### Changed
- ReportsPage completely redesigned:
  - Preview moved to top (~40% height) — shows live HTML preview of the report
  - Template selector row simplified — preset combo, rename/delete, save/load
  - Left panel: block list with add/remove/reorder controls
  - Right panel: inline editor (no more dialog) — fields change based on selected block type
  - Selected block's title, text, chart type, sample index, min wt% are editable directly
  - Drag-drop reorder, arrow buttons, double-click selection all work
  - Removed BlockEditDialog — all editing is inline now

## [0.6.4] — 2026-07-24

### Fixed
- ALL 16 remaining charts converted from static `BG_COLOR`/`FG_COLOR`/`GRID_COLOR` imports to `get_bg_color()`/`get_fg_color()`/`get_grid_color()` — theme switch now works for every chart
- Heatmap: colormap changes between light/dark themes
- ReportsPage: HTML preview now renders actual report content (tables, parameters) in QTextBrowser instead of showing just block names

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
