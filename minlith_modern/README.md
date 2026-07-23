# MINLITH Modern v0.3.0

Нормативный минералогический расчёт из химического состава горных пород.

## Описание

MINLITH Modern — это перезапись легендарной Excel-программы MINLITH на современный Python. Конвертирует весовые проценты оксидов (SiO₂, TiO₂, Al₂O₃, Fe₂O₃, FeO, MgO, CaO, Na₂O, K₂O, P₂O₅, MnO, C, SO₃, F, Cl, S, CO₂, SO) в весовые проценты минералов.

## Возможности

- Полная реализация алгоритма MINLITH (типы 1-5, ~500+ условий ветвления)
- PyQt6 GUI с drag-and-drop, предпросмотром, прогресс-барами
- SQLite база данных с версионированием
- 14 типов диаграмм (bar, pie, QAPF, A-CN-K, A-F-M, TAS, defect, heatmap, feldspar, harker, afm, sio2_k2o, bland_altman, correlation)
- 4 интерактивные диаграммы (Plotly HTML): bar, tas, harker, pie
- Генератор отчётов (PDF, Word, HTML) с встроенными диаграммами
- Параллельный расчёт через ProcessPoolExecutor
- Экспорт в Excel (с листом GeoParams), CSV, JSON
- Геохимические параметры: CIA, ICV, PIA, ASI, AI
- Резервное копирование и импорт базы данных
- Кэширование с TTL (7 дней)
- Таймаут расчёта на образец
- Debug trace collector
- Светлая и тёмная темы

## Стек технологий

- Python 3.12+
- PyQt6
- numpy, pandas, openpyxl
- SQLAlchemy + Alembic
- matplotlib + plotly
- reportlab + python-docx + jinja2

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

# Резервная копия
python -m src backup -o backups/

# Экспорт БД
python -m src export-db -o export.json

# Список диаграмм
python -m src list-charts

# Список шаблонов
python -m src list-templates
```

### Флаги CLI

| Флаг | Описание |
|------|----------|
| `--verbose`, `-V` | Подробный вывод (debug trace) |
| `--timeout N` | Таймаут расчёта на образец (сек, по умолчанию 120) |
| `--config FILE` | Путь к JSON конфигурации |
| `--no-cache` | Не использовать кэш |
| `--format`, `-f` | Формат вывода (xlsx, csv, json, pdf, docx, html) |
| `--template`, `-t` | Шаблон отчёта (brief, standard, full) |
| `--dpi N` | Разрешение диаграммы |
| `--interactive` | Экспорт в интерактивный HTML (Plotly) |

## Сборка

```bash
python build.py
```

## Тесты

```bash
python -m pytest tests/ -v
```
