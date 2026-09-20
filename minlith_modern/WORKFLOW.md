# MINLITH Modern — Рабочий процесс

## Цикл разработки

### 1. Запуск приложения

```bash
# GUI
python src\main.py        (или: python -m src)
python -m src.gui.main_window

# CLI
python -m src.cli calculate input.xlsx -o results.xlsx
```

### 2. Тестирование

```bash
# Все тесты (1151)
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=src --cov-report=term-missing

# Только quick-check
python -m pytest tests/ -x -q

# Property-based тесты
python -m pytest tests/test_property.py -v
```

### 3. Линтер/типы

```bash
python -m ruff check src/ tests/
python -m mypy src/ --ignore-missing-imports
```

## Структура проекта

```
src/
├── core/                  # Расчётный движок
│   ├── algorithm.py       # Protocol + AlgorithmInput
│   ├── algorithm_real.py  # RealAlgorithm (вся логика)
│   ├── algorithm_stub.py  # Deprecated заглушка
│   ├── calculator.py      # Оркестратор + calculate_batch()
│   ├── calibrator.py      # Авто-калибровка через scipy
│   ├── coefficients.py    # k1-k4 по 5 диапазонам F
│   ├── constants.py       # OXIDE_ORDER, MOLAR_MASSES
│   ├── models.py          # FormulaUnits, MineralComposition
│   ├── types_logic.py     # Types 1-5 + Stage VI
│   ├── validation.py      # Проверка полей
│   ├── anomaly_detector.py # 10 правил (синглтон)
│   ├── explainer.py       # Текстовые объяснения
│   └── debug_tracer.py    # Trace collector
├── io/                    # Ввод-вывод
│   ├── excel.py           # load_samples, save_results
│   ├── template.py        # create_template, load_template
│   ├── csv_handler.py     # CSV reader/writer
│   └── xrf_importer.py    # XRF импорт
├── gui/                   # PyQt6 GUI
│   ├── app.py             # QApplication
│   ├── main_window.py     # QMainWindow
│   ├── pages/
│   │   ├── welcome_page.py
│   │   ├── files_page.py
│   │   ├── input_page.py
│   │   ├── results_page.py
│   │   ├── charts_page.py
│   │   ├── output_page.py  # Multi-chart export
│   │   ├── reports_page.py
│   │   ├── history_page.py
│   │   ├── settings_page.py
│   │   └── logs_page.py
│   └── widgets/           # ResultsTable, OxideTable
├── database/              # SQLite + ORM
│   ├── models.py          # DB ORM
│   ├── repository.py      # CRUD операции
│   └── mappers.py         # domain ↔ db mappers
├── reports/               # Генераторы отчётов
├── charts/                # 23 matplotlib + 14 plotly диаграмм
├── utils/                 # Кэш, конфиг, логгер
│   ├── config.py          # ConfigManager (debounce)
│   ├── cache.py           # ResultCache (TTL)
│   └── helpers.py
├── cli.py                 # CLI интерфейс
└── main.py                # Entry point
```

## Ключевые паттерны

### RealAlgorithm
- Вход: `AlgorithmInput` (composition, co2, so, f_total, cl, s)
- Выход: `AlgorithmOutput` (FormulaUnits, MineralComposition, defects)
- Логика: `types_logic.py` — Types 1-5 + Stage VI

### Coefficients
- `calculate_coefficients(f, a)` — k1..k4 + F + A
- Кэширование через `@lru_cache(1024)`
- 5 диапазонов F: 0-4, 4-8, 8-12, 12-16, 16+

### AnomalyDetector (синглтон)
- `AnomalyDetector.instance()` — глобальный доступ
- 10 правил: гипс, сумма, Fe, апатит, дефект, карбонат, полевой шпат, P, отрицательные минералы
- `severity` берётся из `_RULES` (не вычисляется из имени)

### ConfigManager
- `save(debounce=True)` — 1с задержка для дублирующихся вызовов
- `flush()` — немедленная запись
- `validate()` — проверка всех настроек

### ResultCache
- `put()` — исключает derived-поля (pl, fsp, pel, pel_fsp, carsd, ill_kn, chl_mm_srp)
- TTL 7 дней

## Команды CLI

| Команда | Описание |
|---------|----------|
| `calculate` | Расчёт Excel → Excel/CSV/JSON/PDF |
| `chart` | Диаграмма (23 типов) |
| `report` | Отчёт (5 шаблонов) |
| `validate` | Валидация Excel |
| `info` | Инфо об образце |
| `backup` | Резервная копия БД |
| `export-db` | Экспорт БД в JSON |
| `import-db` | Импорт БД из JSON |
| `list-charts` | Список диаграмм |
| `list-templates` | Список шаблонов |

### Флаги

| Флаг | Описание |
|------|----------|
| `--verbose`, `-V` | Debug trace |
| `--timeout N` | Таймаут (сек) |
| `--no-cache` | Без кэша |
| `--force` | Принудительный пересчёт |
| `--format`, `-f` | Формат вывода |
| `--template`, `-t` | Шаблон отчёта |
| `--dpi N` | Разрешение диаграммы |
| `--interactive` | Интерактивный HTML |

## Добавление нового типа минерала

1. Добавить поле в `models.py` → `MineralComposition`
2. Добавить оксид → минерал соотношение в `types_logic.py`
3. Добавить расчёт в `_stage_*` функции
4. Добавить поле в `MINERAL_FIELD_MAP` в `excel.py`
5. Добавить в `ResultCache` exclusion list
6. Добавить тест

## Добавление нового правила аномалий

1. Добавить в `_RULES` в `anomaly_detector.py`
2. Добавить `_check_*` метод
3. Добавить тест в `test_coverage_boost.py`

## Структура диаграмм

```
src/charts/
├── base.py                          # ChartPlugin ABC + ChartData
├── built_in/                        # 23 matplotlib-плагинов
│   ├── bar_chart.py                 # stacked, normalized
│   ├── pie_chart.py                 # sample_idx
│   ├── defect_chart.py              # stacked
│   ├── qapf.py                      # IUGS ternary
│   ├── tas.py                       # TAS scatter
│   ├── acnk.py                      # A-CN-K ternary
│   ├── heatmap.py                   # mineral heatmap
│   ├── rock_type_chart.py           # type distribution
│   ├── feldspar_triangle.py         # Ab-An-Or ternary
│   ├── harker.py                    # SiO₂ vs 10 oxides
│   ├── afm.py                       # AFM ternary
│   ├── sio2_k2o.py                  # Peccerillo-Taylor
│   ├── bland_altman.py              # agreement plot
│   ├── correlation.py               # Pearson heatmap (NaN-safe)
│   ├── kf_chart.py                  # k1-k4 lines
│   ├── box_plot.py                  # mineral distribution
│   ├── radar_chart.py               # spider diagram
│   ├── coefficient_heatmap.py       # k1-k4 heatmap
│   ├── defect_accumulation.py       # stacked defect
│   ├── pca_biplot.py                # PCA 2D
│   ├── dendrogram.py                # hierarchical clustering
│   ├── parallel_coordinates.py      # parallel axes
│   └── mineral_mg_fe_al.py          # Mg-Fe-Al ternary
├── engines/
│   ├── matplotlib_engine.py         # create_figure(), COLORS
│   ├── plotly_engine.py             # save_html()
│   └── plotly_charts.py             # 14 Plotly interactive
└── custom/                          # пусто
```
