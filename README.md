# Lene — MINLITH

Репозиторий проекта **MINLITH**: нормативный минералогический расчёт по результатам
силикатного анализа, перенесённый с оригинального Excel-файла с VBA-макросами на Python.

## Содержимое

| Папка | Что это |
|-------|---------|
| [`minlith_modern/`](minlith_modern/README.md) | **Рабочий проект**: PyQt6 GUI + CLI + расчётный движок (Python) |
| [`docs/`](docs/README.md) | Документация: теория (`algorithm/`), справочники (`reference/`), планы/статусы (`planning/`) |
| [`src_excel/`](src_excel/) | Оригинальные Excel-исходники MINLITH (xlsm/xls/xlsx/zip, txt-дампы) — только как эталон, в коде не используются |
| [`pdf/`](pdf/) | Печатная документация и методички |
| [`reports/`](reports/) | Результаты сверки движка с оригиналом (CSV) |
| [`_trash/`](_trash/) | Удалённое/дубликаты — чистится пользователем вручную |

## Быстрый старт

```bash
cd minlith_modern
pip install -r requirements.txt
python -m src.gui.app        # GUI
python -m src.cli calculate input.xlsx -o results.xlsx   # CLI
```

Подробнее: [`minlith_modern/README.md`](minlith_modern/README.md).

## Лицензирование

- Community-версия — **AGPL-3.0-only** ([`LICENSE`](LICENSE)).
- Для компаний доступна **платная коммерческая лицензия** — условия и
  порядок оформления в [`LICENSING.md`](LICENSING.md).
- Внешние вклады — по [`CLA.md`](CLA.md).

Контакт для коммерческих запросов: **[укажите e-mail]**.

## Статус

- Полный паритет расчётного движка с Excel-оригиналом: **16000/16000** (2026-09-16);
  воспроизводится скриптом `minlith_modern/scripts/verify_synthetic_grid.py`.
- Тесты: **1323 passed, 4 skipped** (`minlith_modern/` → `python -m pytest -q`).
- Правило работы с репо — в [`AGENTS.md`](AGENTS.md).