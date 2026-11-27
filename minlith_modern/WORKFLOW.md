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
# Все тесты (1323 passed, 4 skipped)
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=src --cov-report=term-missing

# Только quick-check
python -m pytest tests/ -x -q

# Property-based тесты
python -m pytest tests/test_property.py -v

# Сверка синтетической сетки 16 000 составов с excel_port (≈10 мин)
python -m scripts.verify_synthetic_grid --n 16000

# Быстрая проверка на 200 составах без excel_port (≈1 с)
python -m scripts.verify_synthetic_grid --n 200 --skip-port
```

Скрипт `scripts/verify_synthetic_grid.py` — воспроизводимый корпус: 60 %
типичных составов, 30 % граничных, 10 % с суммой 85/115 мас. %; критерий —
совпадение именованных переменных и строки 287 с допуском 1e-6. Отчёт
пишется в `reports/synthetic_grid/summary.json` (статусы, max|Δ|, покрытие
каталога веток, распределение типов и полос).

### 3. Линтер/типы

```bash
python -m ruff check src/ tests/
python -m mypy src/ --ignore-missing-imports
```

`ruff` — обязателен и должен быть чист. `mypy` установлен (dev-зависимость),
но конфиг строгий (`disallow_untyped_defs=true`): на текущем коде он даёт
**~354 замечания в 77 файлах** (в основном отсутствующие аннотации и
Optional-поля PyQt) — это предсуществующий долг, целенаправленно не обнулён.
Команда запускается для контроля новых ошибок.

## Структура проекта

```
src/
├── core/                  # Расчётный движок
│   ├── algorithm.py       # Protocol + AlgorithmInput/AlgorithmOutput (+path)
│   ├── excel_parity/      # Движок «как в Excel» (корректные округления, без ROUND)
│   │   └── branches.py    # Структурированная траектория веток (BranchPath)
│   ├── excel_exact/       # Движок «Excel 1:1» (адаптер к excel_port, с ROUND)
│   ├── excel_port/        # Реплика Excel-версии (бит-в-бит, со всеми ROUND)
│   ├── geological_theory.py # Движок по геологической теории (файлы 00-07)
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
├── charts/                # 8 matplotlib + 6 plotly диаграмм
├── utils/                 # Кэш, конфиг, логгер
│   ├── config.py          # ConfigManager (debounce)
│   ├── cache.py           # ResultCache (TTL)
│   └── helpers.py
├── cli.py                 # CLI интерфейс
└── main.py                # Entry point
```

## Ключевые паттерны

### Движки расчёта (`calculation_engine`)
Четыре значения в конфиге (`algorithm_mode` → `calculation_engine`):

| Значение | Класс | Как считает |
| --- | --- | --- |
| `excel_parity` | `ExcelParityAlgorithm` | «как в Excel» с корректными округлениями: те же формулы в float64 без пошаговых ROUND |
| `excel_exact` | `ExcelExactAlgorithm` | «Excel 1:1»: формулы + VBA + пошаговые ROUND, включая накопление ошибки округления книги |
| `geological_theory` | `GeologicalTheoryAlgorithm` | «самостоятельная попытка»: по геологической теории (файлы 00-07) |
| `python_rework` | — (плейсхолдер) | «переработанный под Python»: пользовательская реализация, пока fallback на теорию |

- Вход: `AlgorithmInput` (composition, co2, so, f_total, cl, s + `oxide_wt` — исходные вес.% для `excel_exact`)
- Выход: `AlgorithmOutput` (FormulaUnits, MineralComposition, defects)
- `excel_exact` принимает исходные вес.% (`AlgorithmInput.oxide_wt`, кладёт `Calculator._build_algorithm_input`), т.к. книга сама пересчитывает вес.% → ф.е. с ROUND; при отсутствии `oxide_wt` движок поднимает `ValueError`.
- Старые значения `clean`/`stub`/`custom` автоматически мигрируют на новые.

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
| `chart` | Диаграмма (8 статических типов) |
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
├── built_in/                        # 8 matplotlib-плагинов
│   ├── bar_chart.py                 # stacked, normalized
│   ├── pie_chart.py                 # sample_idx
│   ├── defect_chart.py              # stacked
│   ├── acnk.py                      # A-CN-K ternary
│   ├── heatmap.py                   # mineral heatmap
│   ├── rock_type_chart.py           # type distribution
│   ├── box_plot.py                  # mineral distribution
│   └── pca_biplot.py                # PCA 2D
├── engines/
│   ├── matplotlib_engine.py         # create_figure(), COLORS
│   ├── plotly_engine.py             # save_html()
│   └── plotly_charts.py             # 6 Plotly interactive
└── custom/                          # пусто
```
