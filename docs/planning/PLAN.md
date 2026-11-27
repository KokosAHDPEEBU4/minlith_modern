# PLAN.md
# План файлов проекта MINLITH Modern

**Версия:** 1.0
**Дата:** 2026-07-22
**Статус:** Выполнен (исторический план — реализация завершена, см. `minlith_modern/`)

---

## 1. КОРНЕВАЯ СТРУКТУРА

```
minlith_modern/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── build.py
├── README.md
├── .gitignore
├── src/
├── tests/
├── docs/
├── assets/
└── data/
```

---

## 2. ФАЙЛЫ ПРОЕКТА

### 2.1. Корневые файлы

| Файл | Описание | Приоритет |
|------|----------|-----------|
| `pyproject.toml` | Конфигурация проекта, зависимости, tool-ы (pytest, black, mypy) | Критический |
| `requirements.txt` | Основные зависимости ( PyQt6, numpy, pandas, openpyxl, SQLAlchemy, matplotlib, plotly, reportlab, python-docx, alembic) | Критический |
| `requirements-dev.txt` | Зависимости для разработки (pytest, black, mypy, ruff) | Высокий |
| `build.py` | Скрипт сборки .exe через auto-py-to-exe | Средний |
| `../../minlith_modern/README.md` | Описание проекта, установка, запуск | Средний |
| `.gitignore` | Исключения для git | Низкий |

---

## 2.2. `src/core/` — Расчётный движок (без Qt)

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `models.py` | Frozen dataclasses: `OxideComposition`, `FormulaUnits`, `MineralComposition`, `AdaptiveCoefficients`, `CalculationResult`, `RockType` (Enum), `Sample`, `CalculationConfig` | Критический | — |
| `constants.py` | Молярные массы (IUPAC + MINLITH legacy), формульные веса минералов, алиасы оксидов, диапазоны F для k1-k4 | Критический | — |
| `coefficients.py` | Функция `calculate_coefficients(F: float, A: float) -> AdaptiveCoefficients` — 5 диапазонов F, формулы k1-k4 | Критический | `models.py`, `constants.py` |
| `types_logic.py` | Функции `_calculate_type1()` ... `_calculate_type5()`, `_stage_VI()`, `_stage_0()` — ~500+ строк логики ветвления | Критический | `models.py`, `constants.py`, `coefficients.py` |
| `calculator.py` | Класс `Calculator` с методами `calculate()`, `calculate_single()`, `_prepare_data()` (numpy), `_classify_types()` (numpy) | Критический | `models.py`, `types_logic.py` |
| `validation.py` | Функция `validate_sample()` — проверка суммы [98,102], отрицательных, NaN/inf, обязательных оксидов | Критический | `models.py` |
| `debug_tracer.py` | Класс `DebugTraceCollector` — запись промежуточных переменных, условий, переходов. Экспорт в JSON/TXT | Высокий | — |

---

## 2.3. `src/io/` — Ввод-вывод

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `excel_reader.py` | Класс `ExcelReader` — чтение .xlsx (openpyxl, read_only), автоопределение формата (классический/транспонированный), распознавание алиасов оксидов | Критический | `core/models.py`, `core/constants.py` |
| `excel_writer.py` | Класс `ExcelWriter` — запись результатов в .xlsx (новый файл / новый лист / in_place), секции (вес.%, ф.е., defect, параметры) | Критический | `core/models.py` |
| `csv_handler.py` | Класс `CSVHandler` — чтение/запись .csv (разделитель `;`, UTF-8-SIG) | Высокий | `core/models.py` |
| `legacy_import.py` | Класс `LegacyImport` — чтение листа "ИСХ ДАННЫЕ" из MINLITH1.xlsx | Средний | `excel_reader.py` |

---

## 2.4. `src/database/` — База данных (SQLite + SQLAlchemy)

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `engine.py` | Функции `get_engine()`, `get_session()` — подключение к `%APPDATA%/MINLITH/minlith.db`, WAL режим | Критический | — |
| `models.py` | ORM модели: `SampleDB`, `SampleOxideDB`, `CalculationDB`, `CalculationMineralDB`, `CalculationParameterDB`, `TagDB`, `SampleTagDB` | Критический | `sqlalchemy` |
| `repository.py` | Классы `SampleRepository`, `CalculationRepository` — CRUD, поиск, фильтрация, `get_invalid()` | Критический | `database/models.py` |
| `version_tracker.py` | Класс `VersionTracker` — SHA-256 хеш `types_logic.py`, проверка `is_valid`, предложение пересчёта | Критический | — |
| `migrations/` | Папка Alembic миграций | Средний | `alembic` |

---

## 2.5. `src/charts/` — Диаграммы

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `base.py` | Абстрактный класс `ChartPlugin(ABC)` — `get_name()`, `render()`, `export()` | Критический | `abc`, `matplotlib.figure` |
| `built_in/bar_chart.py` | Столбчатая диаграмма — минералы по образцам | Критический | `base.py` |
| `built_in/pie_chart.py` | Круговая диаграмма — доля минералов в образце (plotly) | Критический | `base.py` |
| `built_in/qapf.py` | QAPF — треугольник классификации магматических | Критический | `base.py` |
| `built_in/acnk.py` | A-CN-K — треугольник ветеринга/происхождения | Критический | `base.py` |
| `built_in/afm.py` | A-F-M — треугольник метаморфических | Критический | `base.py` |
| `built_in/tas.py` | TAS — SiO₂ vs Na₂O+K₂O | Критический | `base.py` |
| `engines/matplotlib_engine.py` | Движок matplotlib — статичные диаграммы | Критический | — |
| `engines/plotly_engine.py` | Движок plotly — интерактивные диаграммы | Средний | — |
| `custom/` | Папка для пользовательских диаграмм (автоподхват) | Низкий | `base.py` |

---

## 2.6. `src/reports/` — Отчёты

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `template_builder.py` | Класс `TemplateBuilder` — drag-and-drop блоков, сохранение/загрузка шаблонов | Критический | — |
| `pdf_generator.py` | Класс `PDFGenerator` — reportlab, титул, таблицы, диаграммы | Критический | `reportlab`, `matplotlib` |
| `word_generator.py` | Класс `WordGenerator` — python-docx, редактируемый .docx | Критический | `python-docx` |
| `html_generator.py` | Класс `HTMLGenerator` — jinja2 шаблоны | Средний | `jinja2` |
| `templates/` | Шаблоны: краткий, стандартный, полный, пользовательский | Средний | — |

---

## 2.7. `src/gui/` — Пользовательский интерфейс (PyQt6)

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `app.py` | Класс `App` — QApplication, инициализация, запуск | Критический | `PyQt6` |
| `main_window.py` | Класс `MainWindow(QMainWindow)` — главное окно, sidebar, навигация по страницам | Критический | `PyQt6` |
| `pages/welcome_page.py` | Страница приветствия, быстрый старт | Высокий | — |
| `pages/files_page.py` | Страница файлов — drag-and-drop, превью, список файлов | Критический | `io/excel_reader.py` |
| `pages/settings_page.py` | Страница настроек — чтение/запись JSON | Критический | `utils/config.py` |
| `pages/results_page.py` | Страница результатов — таблица, фильтры, экспорт | Критический | `core/models.py` |
| `pages/charts_page.py` | Страница диаграмм — выбор образцов, настройки | Средний | `charts/` |
| `pages/compare_page.py` | Страница сравнения — two-file comparison, статистика | Средний | — |
| `pages/database_page.py` | Страница БД — история, поиск, фильтры | Средний | `database/` |
| `pages/logs_page.py` | Страница логов — фильтр по уровню, поиск | Средний | `utils/logger.py` |
| `dialogs/calculation_dialog.py` | Диалог расчёта — прогресс-бар, отмена | Критический | `workers/` |
| `widgets/oxide_table.py` | Виджет таблицы оксидов | Критический | `core/models.py` |
| `widgets/mineral_table.py` | Виджет таблицы минералов | Критический | `core/models.py` |
| `widgets/log_widget.py` | Виджет логов (QTextEdit + GUILogHandler) | Средний | `utils/logger.py` |
| `widgets/drag_drop_widget.py` | Виджет drag-and-drop | Критический | — |
| `styles/default.qss` | Стили по умолчанию | Средний | — |

---

## 2.8. `src/workers/` — Параллельность

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `calculation_worker.py` | Класс `CalculationWorker(QObject)` — QThread + ProcessPoolExecutor, сигналы progress/finished/error/cancelled | Критический | `core/calculator.py`, `PyQt6` |

---

## 2.9. `src/utils/` — Утилиты

| Файл | Описание | Приоритет | Зависимости |
|------|----------|-----------|-------------|
| `config.py` | Класс `ConfigManager` — чтение/запись JSON, импорт/экспорт, сброс на defaults | Критический | — |
| `logger.py` | Функция `setup_logging()`, класс `GUILogHandler` — QueueHandler для multiprocessing, RotatingFileHandler | Критический | `logging` |
| `helpers.py` | Вспомогательные функции (пути, форматирование) | Низкий | — |

---

## 2.10. `data/` — Данные

| Файл | Описание | Приоритет |
|------|----------|-----------|
| `default_settings.json` | Настройки по умолчанию (из ТЗ раздел 6.2) | Критический |
| `mineral_weights.json` | Формульные веса минералов (для пользователя) | Средний |
| `oxide_aliases.json` | Алиасы оксидов (для пользователя) | Средний |

---

## 2.11. `tests/` — Тесты

| Файл | Описание | Приоритет |
|------|----------|-----------|
| `__init__.py` | — | — |
| `test_calculator.py` | Тесты расчёта: БК-1, T-O2, чистые минералы, граничные случаи | Критический |
| `test_types_logic.py` | Тесты каждой ветки Type 1-5, Этап VI | Критический |
| `test_io.py` | Тесты чтения/записи Excel, CSV | Критический |
| `test_coefficients.py` | Тесты k1-k4 для всех диапазонов F | Высокий |
| `test_validation.py` | Тесты валидации входных данных | Высокий |
| `data/bk1_expected.json` | Ожидаемый результат БК-1 (после верификации) | Критический |
| `data/t_o2_expected.json` | Ожидаемый результат T-O2 (после верификации) | Критический |
| `data/synthetic/` | Синтетические тесты (чистый кварц, кальцит и т.д.) | Высокий |

---

## 3. ПОРЯДОК РЕАЛИЗАЦИИ

### Критический путь

```
Этап 1: src/core/models.py + src/core/constants.py
    ↓
Этап 2: src/core/coefficients.py + src/core/types_logic.py
    ↓
Этап 3: src/core/calculator.py + src/core/validation.py + src/core/debug_tracer.py
    ↓
Этап 4: tests/test_calculator.py + tests/test_types_logic.py (валидация на оригинале)
    ↓
Этап 5: src/io/excel_reader.py + src/io/excel_writer.py
    ↓
Этап 6: src/database/ (SQLAlchemy + Alembic)
    ↓
Этап 7: src/gui/ (PyQt6)
    ↓
Этап 8: src/workers/ (параллельность)
    ↓
Этап 9: src/charts/ (6 базовых)
    ↓
Этап 10: src/reports/ (PDF/Word/HTML)
    ↓
Этап 11: build.py (сборка .exe)
    ↓
Этап 12: Интеграционное тестирование
```

### Оценка времени

| Этап | Файлы | Дни |
|------|-------|-----|
| 1. Модели + константы | 2 | 1 |
| 2. Алгоритм Type 1-5 | 3 | 3-5 |
| 3. Интеграция движка | 3 | 2 |
| 4. Тесты | 3+ | 2 |
| 5. I/O | 4 | 2 |
| 6. База данных | 5 | 2 |
| 7. GUI | 15+ | 3-5 |
| 8. Параллельность | 1 | 2 |
| 9. Диаграммы | 9+ | 3 |
| 10. Отчёты | 5+ | 2 |
| 11. Сборка | 1 | 1 |
| 12. Тестирование | — | 2 |
| **Итого** | **~50 файлов** | **~20-25 дней** |

---

## 4. ЗАВИСИМОСТИ МЕЖДУ МОДУЛЯМИ

```
core/models.py ←────────────────────────────── ВСЁ
core/constants.py ←─────────────────────────── core/, io/
core/coefficients.py ←──────────────────────── core/types_logic.py
core/types_logic.py ←───────────────────────── core/calculator.py
core/calculator.py ←────────────────────────── workers/, tests/
core/validation.py ←────────────────────────── core/calculator.py, io/
core/debug_tracer.py ←──────────────────────── core/calculator.py

io/excel_reader.py ←────────────────────────── gui/pages/files_page.py
io/excel_writer.py ←────────────────────────── gui/pages/results_page.py

database/engine.py ←────────────────────────── database/repository.py
database/models.py ←────────────────────────── database/repository.py
database/repository.py ←────────────────────── gui/pages/database_page.py
database/version_tracker.py ←───────────────── app startup

charts/base.py ←────────────────────────────── charts/built_in/*
charts/built_in/* ←─────────────────────────── gui/pages/charts_page.py
charts/engines/* ←───────────────────────────── charts/built_in/*

reports/template_builder.py ←───────────────── gui/
reports/*_generator.py ←────────────────────── reports/template_builder.py

gui/app.py ←────────────────────────────────── main
gui/main_window.py ←────────────────────────── gui/app.py
gui/pages/* ←───────────────────────────────── gui/main_window.py
gui/dialogs/* ←─────────────────────────────── gui/pages/*
gui/widgets/* ←─────────────────────────────── gui/pages/*

workers/calculation_worker.py ←─────────────── gui/dialogs/calculation_dialog.py

utils/config.py ←───────────────────────────── gui/pages/settings_page.py, core/
utils/logger.py ←───────────────────────────── всё приложение
```

---

## 5. ОБЩИЙ ИТОГ

| Параметр | Значение |
|----------|----------|
| Всего файлов | ~50 |
| Python-модулей | ~35 |
| Тестов | 5+ |
| Конфигов | 4+ |
| Шаблонов | 3+ |
| Стилей | 1 |
| Документов | 6 (уже есть) |
