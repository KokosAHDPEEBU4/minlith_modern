# Changelog

## [Unreleased]

### Added
- **Отдельный движок `excel_exact` — полная 1:1 копия Excel:** `ExcelExactAlgorithm` (`src/core/excel_exact/algorithm.py`) исполняет формулы+VBA через `excel_port.run_sample(rounding=True)`, воспроизводя пошаговые `ROUND` и накопление ошибки округления книги MINLITH. В отличие от `excel_parity`, который считает те же формулы в float64 без пошаговых округлений. Движку передаются исходные вес.% оксидов (`AlgorithmInput.oxide_wt`), т.к. книга сама пересчитывает вес.% → ф.е. с `ROUND`.
- GUI: в тулбаре «Движки расчёта» и в списках движков (Настройки, диалог расчёта) теперь два «экселевских» варианта — «Excel (корректные округл.)» (`excel_parity`, по умолчанию) и «Excel 1:1 (ROUND)» (`excel_exact`); CLI `--engine` принимает `excel_exact`.
- Тесты: `tests/test_excel_exact_adapter.py` (14 шт.) — протокол, разрешение движка Calculator'ом, совпадение ф.е. с `excel_port(rounding=True)` на 7 образцах, end-to-end через Calculator, проброс `oxide_wt`, ошибка без вес.%.
- **Структурированная траектория веток движка `excel_parity`** (`src/core/excel_parity/branches.py`): `BranchDecision`/`BranchPath`, каталоги `COEFFICIENT_BAND_INFO` (H5/J5/L5/H12/J12/L12), `ROCK_TYPE_INFO` (1-5), `STAGE_VI_INFO` (A/B/C), `TYPE_BRANCH_INFO` (подписи `t_*`/`p_*`/`m_*`). `Stage0` получил поля `coefficient_band` и `type_conditions`; `ExcelRun.path` собирает маршрут образца; `AlgorithmOutput.path` отдаёт его наружу. Чистое добавление — расчёт не менялся. База для графа разветвлений (`docs/planning/BRANCH_GRAPH_SELECTION.md`).
- `DebugTraceCollector.record_branch_path()` — запись маршрута веток в трассировку; `Calculator.calculate_single(debug=True)` подхватывает `AlgorithmOutput.path`.
- Тесты: `tests/test_branch_path.py` (20 шт.) — согласованность зеркальных `coefficient_band`/`classify_conditions` с `coefficients`/`classify` на сетке, структура `ExcelRun.path`, round-trip `to_dict`, запись в трассировку, сквозной путь через `Calculator(debug=True)`.
- `scripts/verify_excel_parity.py`: добавлен подсчёт сходимости **`excel_exact`** (= `excel_port(rounding=True)`) с живым Excel — строка 287 и невязки восстанавливаются прогоном книги; новые колонки `exact_suspect_count`/`exact_bad_count` в `summary.csv` и новые отчёты `row287_exact.csv`/`defect_exact.csv`.
- **Маршрут веток в результатах и GUI:** `CalculationResult.branch_path` (от `excel_parity`), чистый модуль `src/core/branch_report.py` (`describe_branch_path`, `format_branch_path_text`), диалог `src/gui/dialogs/branch_path_dialog.py` и кнопка «Маршрут веток» на странице результатов (`src/gui/pages/results_page.py`) — показывает траекторию решений по выбранному образцу (стадия, ветка, условие, источник) с копированием текста.
- **Закрыты gap-ветки типа 3/4/5** (`src/core/excel_parity/types.py`), совпадение с `excel_port(rounding=False)` ~1e-9:
  - `p_196` (ветка `else` от `p_181`/`p_189`, `d180<=0 и d188>=0`): `si3_3<0 → p_253`, иначе `p_81`; тест `test_type3_p196_branch_implemented`.
  - `type45 m_418t`: Excel вызывает `p_201` напрямую (минуя `p_159`), плюс квирк — `C422` копируется дважды (в `al4_1`, затем в `al3_2`) и пересчитывается, т.е. `na`/`ca` вычитаются дважды. Добавлен флаг `skip_fe_lookup` и двойной вычет; тест `test_type45_m418t_matches_excel`.
  - Оставшиеся два gap'а (`s_274t` при `k2=0`, защитный `stage_vi`) на 200 000 случайных входов недостижимы.
- **Устранены расхождения `excel_parity` с `excel_port(rounding=False)` на экстремальных входах** (фаззинг: 106 → 1 из 4000; было сосредоточено в типах 4/5):
  - `excel_parity` type45 (`mg0`): `mg0` — отдельная именованная ячейка `J272`, НЕ базовый MgO. Для типа 4 её пишет `aType_4` (`mg0=mg`), для типа 5 — не трогает (`mg0=0`), а коридор `m_528` задаёт её через `m_531`. Исправлен проброс `mg0` в `_t45_513`/`_t45_m279` (ветки `m_322t`/`m_281`); тест `test_type5_m322t_mg0_matches_excel`.
  - type1 `t_74t`: `si_n` остаётся `= C70 = si_r` (записан в `t_68t`), а не обнуляется; тест `test_type1_t74_si_n_matches_excel`.
  - `_t45_513`: в `m_279` передаётся исходный `fe3_1` (m_513 пишет только `fe3_2`), а не `fe4_2`; тест `test_type45_m346_fe3_1_matches_excel`.
  - type5→type3 (`al3_3` через `I51`): при входе в `aType_3` из коридора `aType_5→m_528→m_531` Excel сохраняет `al3_3 = C534 = al4_1`. `type3()` теперь принимает `al3_3_in`, коридор передаёт `al4_1`; тест `test_type5_corridor_to_type3_carries_al3_3`. Фаззинг: 0 расхождений на 4000 экстремальных входах.
- **Подсказка имени образца при наведении на точку диаграммы** (в приложении, как в интерактивном Plotly-HTML): плитка диаграммы находит ближайшую точку под курсором и показывает имя образца в строке статуса. Реализация: `_ChartTile._connect_point_hover/_on_point_hover`, чистый помощник `src/gui/widgets/hover_math.py`; плитке передаётся `sample_names`. Работает для точечных/линейных диаграмм (числи точек == числу образцов); у круговой — своя подсказка.

### Added
- **Ручной выбор веток — модель и проброс (этап 2 ТЗ `docs/planning/TZ_BRANCH_GRAPH.md`):** `src/core/branch_overrides.py` (`BranchOverrides`, `validate_overrides` — валидация по каталогу `branch_catalog`); `CalculationConfig.branch_overrides`/`forced_path`; `AlgorithmInput.overrides`; `Stage0.overrides`; `Calculator._build_algorithm_input` собирает и валидирует override; проброс в `excel_parity` (`run_sample(..., overrides=)`). Поведение по умолчанию не менялось (пустой выбор == авто). Тесты: `tests/test_branch_overrides.py` (9 шт.).

### Added
- **Override внутренних веток типов (этап 6 ТЗ, подмножество):** переопределяемые решения в каталоге (`overridable=True`) и их поддержка в движке:
  - `type3.p_114` — хлорит по Al `F119+` / по Mg `F126-`;
  - `type45.d418` — Fe-путь `m_418t` / `m_424->t5`;
  - `type1.t_49` — `t_52~53` / `t_58` / `t_67` / `t_83`;
  - `type3.d61` — анортит `D61` / `D68`;
  - `type3.d200` — Fe-путь `3333a` / `3333b`;
  - `type3.p_142` — `p_142` (ill = mg) / `no_p_142` (ill = k/2);
  - `type2.fe_ill` — иллит по Fe `fe-ill` / по Mg `fe-ill-mg` (s_221);
  - `type3.d180` — Fe-путь `3332a` (chl по Al) / `no_3332a` (3332b / p_196);
  - `type2.an` — анортит `an=0.2na` / `an=ca` / `an=0.2na(I)`;
  - `type2.s204` — `s208` / `s271`; `type2.ill_or` — `ill+or` / `no_ill_or`;
  - `type3.d162` — `3331` / `no_3331`; `type3.d188` — `3332b` / `no_3332b`;
  - `type3.p_53` — `p_53t` / `no_p_53`; `type3.p_97` — `D106` / `D109-fe` / `p253->t5`;
  - `type45.d334` — `mm-path` / `no_mm`; `type45.d346` — `m_346` / `m_360`;
  - `type1.t_73` — `t_74t` / `t_78`;
  - `type45.d287` — `m287` / `m334`; `type45.d302` — `m302` / `m311`; `type45.d322` — `m322` / `m296`.
  Override для хелперов type4/5 проносится через поле `TypeSolution.overrides`.
  Форсированные внутренние ветки помечаются `forced` в маршруте (по id из `overrides.choices`). Остальные внутренние решения типов — заглушки `overridable=False`. Тесты: `test_type3_p114_override`, `test_type45_d418_override`, `test_type1_t49_override`, `test_type3_d61_override`, `test_validate_accepts_internal_overrides`.
- **Экспорт и сравнение маршрутов (этап 5 ТЗ):** чистые функции `branch_report.branch_path_json` и `branch_report.diff_branch_paths`; на странице «Граф» — кнопки «Экспорт маршрута (JSON)» и «Сравнить с авто» (различия авто-маршрута и принудительного). Тест: `test_branch_path_json_and_diff`.
- **GUI-страница «Граф разветвлений» (этап 4 ТЗ):** `src/gui/pages/branch_graph_page.py` — дерево решений из каталога, подсветка пройденного маршрута (✓) и принудительных веток (★), выбор образца, кнопки «Принудительно выбрать ветку» / «Снять выбор» / «Пересчитать с выбранными ветками». Встроена в `MainWindow` (сайдбар «Граф», индекс перед «Журналом»), получает результаты расчёта. Чистые помощники `branch_report.path_branch_ids/forced_branch_ids`. Заодно адаптер `stage0_from_input` теперь применяет override полосы/типа (раньше только `compute_stage0`). Тесты: +3 (`test_branch_graph_page_override_and_recalc`, `test_main_window_has_branch_graph_page`, `test_path_branch_id_helpers`).
- **Применение ручного выбора веток в движке (этап 3 ТЗ):** `coefficients(f,a,override=)` и `classify(fe,k1,k3,override=)` выбирают полосу/тип по override; `solve_stage_vi(st0,tsol,override=)` — ветку A/B/C-srp/C-mst/C-mst2; `compute_stage0` прокидывает override и валидирует; в `ExcelRun.path` форсированные решения помечаются `forced=True`. Авто-поведение (без override) не изменилось — паритет зелёный. Тесты: `tests/test_branch_overrides_engine.py` (16 шт.).

### Fixed
- **Падение приложения при старте:** `MainWindow._apply_zoom_step` обращался к `page._view`, но у `ChartsPage` после перехода на вкладки такого атрибута нет (`AttributeError: 'ChartsPage' object has no attribute '_view'`). Добавлены методы `set_zoom_step()` в `ChartsPage` (применяет шаг ко всем вкладкам) и `OutputPage` (делегирует в `_view`); `main_window` вызывает `page.set_zoom_step(step)`.
- **Вылет при добавлении вкладки диаграмм:** кнопка «+» была подключена к `_add_tab` напрямую, а `clicked` передаёт `checked=False` → `_add_tab(name=False)` падал с `TypeError` в `QTabWidget.addTab`. Кнопка переделана: теперь это вкладка-«＋» последней вкладкой.
- Тесты: `tests/test_gui_smoke.py` — offscreen-смоук: страницы диаграмм и `MainWindow` конструируются, `_apply_zoom_step` не падает, «＋» добавляет вкладку и остаётся последней, диалог расчёта умеет выбирать все образцы.

### Changed
- **Вкладки диаграмм:** кнопка создания новой вкладки теперь оформлена как в браузере — отдельная вкладка «＋» сразу после последней открытой (вместо угловой кнопки справа); «＋» не закрывается и при перетаскивании остаётся последней. Логика вкладок: `ChartsPage._add_plus_tab/_on_tab_bar_clicked/_on_tab_moved`, `set_data`/`set_zoom_step` пропускают вкладку-заглушку.
- **Диалог «Расчёт…»:** добавлены кнопки «Выбрать все образцы» и «Снять выделение» (`src/gui/dialogs/calculation_dialog.py`).
- **Панель выбора на странице диаграмм — три уровня слева направо:** «Диаграммы | Образцы | Минералы» (было: диаграммы+минералы в один столбец, образцы — кнопкой сверху). Выбор образцов перенесён в панель чекбоксами, синхронизируется между вкладками (`MultiChartView.set_sample_names/selected_sample_indexes/samplesChanged`, `ChartsPage._on_samples_changed`). На странице «Вывод» уровень образцов скрыт (`set_samples_visible(False)`).
- `CALCULATION_ENGINES` теперь `("excel_parity", "excel_exact", "geological_theory", "python_rework")`; дефолт остался `excel_parity`. `AlgorithmInput` получил необязательное поле `oxide_wt: dict[str, float] | None`, `AlgorithmOutput` — поле `path: dict | None`, `CalculationResult` — поле `branch_path: dict | None` (все с дефолтами, обратно совместимо).

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
