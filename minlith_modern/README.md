# MINLITH Modern v0.7.0

Нормативный минералогический расчёт из химического состава горных пород.

## Описание

MINLITH Modern — это перезапись легендарной Excel-программы MINLITH на современный Python. Конвертирует весовые проценты оксидов (SiO₂, TiO₂, Al₂O₃, Fe₂O₃, FeO, MgO, CaO, Na₂O, K₂O, P₂O₅, MnO, C, SO₃, F, Cl, S, CO₂, SO) в весовые проценты минералов.

## Возможности

- Полная реализация алгоритма MINLITH (типы 1-5, ~500+ условий ветвления)
- Auto-calibration — автоматическое восстановление параметров алгоритма из Excel через scipy
- PyQt6 GUI с drag-and-drop, предпросмотром, прогресс-барами
- Настройки: сайдбар-навигация (Расчёт / Экспорт / Диаграммы / Интерфейс), поиск настроек, карточки, адаптация под тёмную/светлую тему
- SQLite база данных с версионированием
- 8 типов диаграмм (matplotlib): bar, pie, defect, A-CN-K, heatmap, rock type, box plot, PCA biplot
- 6 интерактивных диаграмм (Plotly HTML): bar, pie, A-CN-K, heatmap, boxplot, rock type (экспорт из GUI: «Диаграммы» → «Интерактивный HTML…», и CLI `--interactive`)
- Диаграммы в GUI: вкладки (кнопка «＋» рядом с последней), три уровня выбора слева-направо (диаграммы | образцы | минералы), подсказка с именем образца при наведении на точку
- Граф разветвлений: дерево решений, подсветка маршрута образца, ручной выбор ветки + пересчёт; сравнение движков `excel_parity` vs `excel_exact` «бок о бок» (страница «Результаты» → «Сравнить движки»)
- Генератор отчётов (PDF, Word, HTML) с встроенными диаграммами
- 5 шаблонов отчётов: brief, standard, full, core, geochemical
- Параллельный расчёт через ProcessPoolExecutor
- Экспорт в Excel (с листом GeoParams), CSV, JSON, LaTeX
- Импорт XRF (Bruker/Panalytical/Rigaku)
- Геохимические параметры: CIA, ICV, PIA, ASI, AI
- AnomalyDetector (10 правил: гипс, сумма, Fe, апатит, дефект, карбонат, полевой шпат, P, отрицательные минералы)
- Explainer — человекочитаемые объяснения расчёта на русском языке
- Резервное копирование и импорт базы данных
- Кэширование с TTL (7 дней)
- Таймаут расчёта на образец
- Debug trace collector
- Property-based тестирование (Hypothesis)
- Светлая и тёмная темы

## Стек технологий

- Python 3.12+
- PyQt6
- numpy, pandas, openpyxl, scipy
- SQLAlchemy + Alembic
- matplotlib + plotly
- reportlab + python-docx + jinja2
- hypothesis (property-based testing)

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### GUI

```bash
python -m src.gui.app
# или
minlith-gui
```

### CLI

```bash
# Расчёт
python -m src calculate input.xlsx -o results.xlsx

# С подробным выводом
python -m src calculate input.xlsx -V --timeout 300

# Диаграмма
python -m src chart input.xlsx --type tas -o chart.png

# Диаграмма (интерактивная)
python -m src chart input.xlsx --type tas --interactive -o chart.html

# Отчёт
python -m src report input.xlsx --template full -o report.pdf
python -m src report input.xlsx --template core -o report.pdf
python -m src report input.xlsx --template geochemical -o report.pdf

# Резервная копия
python -m src backup -o backups/

# Экспорт БД
python -m src export-db -o export.json

# Список диаграмм
python -m src list-charts

# Список шаблонов
python -m src list-templates

# Валидация
python -m src validate input.xlsx

# Инфо об образце
python -m src info input.xlsx
```

### Авто-калибровка

```bash
# Запуск калибровки из Excel
python calibrate.py --input MINLITH1.xlsx --output calibration_config.json --maxiter 1000
```

### Флаги CLI

| Флаг | Описание |
|------|----------|
| `--verbose`, `-V` | Подробный вывод (debug trace) |
| `--timeout N` | Таймаут расчёта на образец (сек, по умолчанию 120) |
| `--config FILE` | Путь к JSON конфигурации |
| `--no-cache` | Не использовать кэш |
| `--force` | Принудительный пересчёт (игнорировать кэш) |
| `--format`, `-f` | Формат вывода (xlsx, csv, json, pdf, docx, html) |
| `--template`, `-t` | Шаблон отчёта (brief, standard, full, core, geochemical) |
| `--dpi N` | Разрешение диаграммы |
| `--interactive` | Экспорт в интерактивный HTML (Plotly) |
| `--engine`, `-e` | Движок расчёта: `excel_parity` (как в Excel с корректными округлениями, по умолчанию), `excel_exact` (полная 1:1 копия Excel с ROUND), `geological_theory` (по геологической теории), `python_rework` (Python-переработка) |

### Python API

```python
from src.core.models import OxideComposition, Sample
from src.core.calculator import Calculator

comp = OxideComposition(
    sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
    mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
)
sample = Sample(name="T-O2", composition=comp)
calc = Calculator()
result = calc.calculate_single(sample)

print(result.rock_type)          # RockType.TYPE_5
print(result.minerals_weight.ab) # 7.82
print(result.defect)             # oxide residuals
print(result.anomalies)          # list[AnomalyHypothesis]

# Движок расчёта:
#   excel_parity      — «как в Excel» с корректными округлениями: тот же алгоритм
#                       в float64 без пошаговых ROUND (по умолчанию)
#   excel_exact       — полная 1:1 копия Excel: формулы + VBA + пошаговые ROUND,
#                       включая накопление ошибки округления книги MINLITH
#   geological_theory — «самостоятельная попытка»: расчёт по геологической теории
#   python_rework     — «переработанный под Python»: пользовательская реализация
#                       (пока не подключена)
calc_excel = Calculator(config=CalculationConfig(calculation_engine="excel_parity"))
calc_exact = Calculator(config=CalculationConfig(calculation_engine="excel_exact"))
```

> В GUI движок выбирается на странице «Настройки» → «Движок расчёта», а также на
> тулбаре «Движки расчёта» («Excel (корректные округл.)» / «Excel 1:1 (ROUND)» /
> «Геол. теория» / «Python-переработка»).

## Сборка

Portable-сборка (windowed) — автоматический скрипт:

```bat
build_exe.bat              :: onedir (по умолчанию) — быстрый запуск
build_exe.bat --onefile    :: один файл (медленнее стартует — распаковка в temp)
```

Результат по умолчанию: **`../minlith_exe/MINLITH/MINLITH.exe`** (папка; для
переноса на другое устройство копируйте её целиком). При `--onefile` — один
`../minlith_exe/MINLITH.exe`. Python на целевой машине не нужен (Windows x64).

> **Почему onedir по умолчанию:** `--onefile` при каждом запуске распаковывает
> ~180 МБ во временную папку (+сканирование антивирусом) — старт долгий.
> `onedir` запускается почти сразу.

Сборка включает ресурсы `src/gui/styles/*.qss` и `src/core/excel_port/data/*`;
Python/PyInstaller проверяются автоматически (PyInstaller ставится при отсутствии).

Ручные варианты: `python build.py` (старый, onedir) или `pyinstaller minlith.spec`.

## Тесты

```bash
# Все тесты (1323 passed, 4 skipped)
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=src --cov-report=term-missing

# Только property-based тесты
python -m pytest tests/test_property.py -v

# Scenario тесты
python -m pytest tests/test_scenarios.py -v
```

## Структура проекта

```
minlith_modern/
├── src/
│   ├── core/           # Расчётный движок
│   │   ├── calculator.py       # Оркестратор
│   │   ├── excel_parity/       # Движок «как в Excel» (корректные округления, без ROUND)
│   │   │   └── branches.py     # Траектория веток (BranchPath) — база графа разветвлений
│   │   ├── excel_exact/        # Движок «Excel 1:1» (адаптер к excel_port, с ROUND)
│   │   ├── excel_port/         # Реплика Excel-версии (бит-в-бит, со всеми ROUND)
│   │   ├── geological_theory.py # Движок по геологической теории (файлы 00-07)
│   │   ├── algorithm.py        # Протокол алгоритма
│   │   ├── models.py           # Датаклассы
│   │   ├── coefficients.py     # k1-k4 коэффициенты
│   │   ├── constants.py        # Молярные массы
│   │   ├── validation.py       # Валидация
│   │   ├── types_logic.py      # Логика типов 1-5
│   │   ├── calibrator.py       # Авто-калибровка
│   │   ├── anomaly_detector.py # Детектор аномалий
│   │   ├── explainer.py        # Объяснения
│   │   └── debug_tracer.py     # Trace collector
│   ├── io/             # Ввод-вывод
│   │   ├── excel.py            # Excel reader/writer
│   │   ├── csv_handler.py      # CSV reader/writer
│   │   └── xrf_importer.py     # XRF импорт
│   ├── charts/         # Диаграммы
│   ├── reports/        # Генераторы отчётов
│   ├── database/       # SQLite + ORM
│   ├── gui/            # PyQt6 GUI
│   ├── utils/          # Кэш, конфиг, логгер
│   └── cli.py          # CLI интерфейс
├── tests/              # 1323 тестов (4 skipped)
│   ├── test_property.py       # Hypothesis property-based
│   ├── test_scenarios.py      # 75 scenario тестов
│   ├── test_coverage_boost.py # Покрытие калибратора/кэша
│   ├── test_types_logic.py    # 20 тестов типов 1-5
│   ├── test_coefficients.py   # 11 тестов коэффициентов
│   ├── test_excel.py          # 5 тестов Excel export
│   ├── test_repository.py     # 6 тестов CRUD
│   ├── test_cli.py            # 2 теста CLI
│   └── ...
├── calibrate.py        # CLI для калибровки
├── calibration_config.json
└── minlith.spec        # PyInstaller
```
