"""Универсальный автоимпорт таблиц с оксидами (Excel/CSV).

Не требуя точного шаблона MINLITH, модуль сам находит:

  * **строку заголовка** (может быть не первой — есть шапки/комментарии);
  * **колонки оксидов** по алиасам (регистр, ``SiO₂``, ``SiO2 (%)``, ``AL2O3``,
    ``мас.%``, названия элементов XRF и т.п.);
  * **ориентацию**: образцы в строках (оксиды — колонки) или образцы в
    столбцах (оксиды — строки, как «ИСХ ДАННЫЕ»);
  * **колонку/строку с именем образца** (name/sample/образец/номер/id);
  * значения с запятой-разделителем, ``%``, ``<0.01``; отсутствующие оксиды → 0.

Чистые функции (`normalize_header`, `parse_grid`) тестируются без файлов;
тонкие обёртки читают 2D-сетку из Excel/CSV.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from src.core.constants import OXIDE_ALIASES
from src.core.models import OxideComposition, Sample

logger = logging.getLogger(__name__)

# Названия колонки/строки с именем образца.
NAME_ALIASES = {"name", "sample", "образец", "проба", "номер", "id", "sample name"}

# Символ элемента → оксид (XRF в режиме элементов).
_ELEMENT_TO_FIELD = {
    "si": "sio2", "ti": "tio2", "al": "al2o3", "fe": "fe2o3",
    "mg": "mgo", "ca": "cao", "na": "na2o", "k": "k2o", "p": "p2o5",
    "mn": "mno", "s": "s", "f": "f", "cl": "cl",
}

_SUBSCRIPT = str.maketrans("₂₃₅", "235")


def _norm(text: object) -> str:
    """Нормализовать текст заголовка: нижний регистр, убрать %, скобки, пробелы."""
    s = str(text).strip().lower().translate(_SUBSCRIPT)
    s = re.sub(r"\(.*?\)", "", s)          # (%), (мас.%), (III) и т.п.
    s = s.replace("%", "").replace("мас", "").replace("об", "")
    s = re.sub(r"[\s_\-.]+", "", s)
    return s


def _build_alias_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for field, aliases in OXIDE_ALIASES.items():
        for alias in aliases:
            m.setdefault(_norm(alias), field)
    for element, field in _ELEMENT_TO_FIELD.items():
        m.setdefault(element, field)
    return m


_ALIAS_MAP = _build_alias_map()


def normalize_header(text: object) -> str | None:
    """Вернуть поле OxideComposition по заголовку или ``None``."""
    if text is None:
        return None
    key = _norm(text)
    return _ALIAS_MAP.get(key)


def _is_name_header(text: object) -> bool:
    return _norm(text) in {_norm(a) for a in NAME_ALIASES}


def to_float(value: object) -> float | None:
    """Разобрать число: запятая, %, пробелы, ``<0.01`` (→ половина порога)."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip().replace(",", ".").replace("%", "").replace(" ", "")
    if not s:
        return None
    if s.startswith("<"):
        try:
            return float(s[1:]) / 2.0
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def _row_hits(row: list) -> int:
    return sum(1 for cell in row if normalize_header(cell) is not None)


def _col_hits(grid: list[list], col: int) -> int:
    return sum(1 for row in grid
               if col < len(row) and normalize_header(row[col]) is not None)


def detect_layout(grid: list[list]) -> str:
    """``"rows"`` (оксиды-колонки) | ``"cols"`` (оксиды-строки) | ``"unknown"``."""
    if not grid:
        return "unknown"
    best_row = max((_row_hits(r) for r in grid), default=0)
    width = max((len(r) for r in grid), default=0)
    best_col = max((_col_hits(grid, c) for c in range(width)), default=0)
    if best_row < 2 and best_col < 2:
        return "unknown"
    return "rows" if best_row >= best_col else "cols"


def _empty_field() -> dict[str, float]:
    return {field: 0.0 for field in OXIDE_ALIASES}


def _sample(name: str, fields: dict[str, float], index: int) -> Sample:
    return Sample(name=name or f"Sample_{index}",
                  composition=OxideComposition(**fields))


def _parse_rows(grid: list[list]) -> list[Sample]:
    """Оксиды — в колонках: строка заголовка + образцы в строках."""
    header_i = max(range(len(grid)), key=lambda i: _row_hits(grid[i]))
    if _row_hits(grid[header_i]) < 2:
        return []
    header = grid[header_i]
    oxide_cols: dict[int, str] = {}
    for c in range(len(header)):
        field = normalize_header(header[c])
        if field is not None:
            oxide_cols[c] = field

    # Колонка имени: по заголовку-алиасу, иначе первая колонка с текстом.
    name_col = None
    for c in range(len(header)):
        if c not in oxide_cols and _is_name_header(header[c]):
            name_col = c
            break
    if name_col is None:
        for c in range(len(header)):
            if c in oxide_cols:
                continue
            if any(c < len(row) and str(row[c]).strip()
                   and to_float(row[c]) is None
                   for row in grid[header_i + 1:]):
                name_col = c
                break

    samples: list[Sample] = []
    for i, row in enumerate(grid[header_i + 1:], start=1):
        if all((c >= len(row) or not str(row[c]).strip()) for c in oxide_cols):
            continue
        fields = _empty_field()
        for c, field in oxide_cols.items():
            val = to_float(row[c]) if c < len(row) else None
            if val is not None:
                fields[field] = val
        name = str(row[name_col]).strip() if (name_col is not None
                                              and name_col < len(row)) else ""
        samples.append(_sample(name, fields, i))
    return samples


def _parse_cols(grid: list[list]) -> list[Sample]:
    """Оксиды — в строках: колонки = образцы (формат «ИСХ ДАННЫЕ»)."""
    width = max((len(r) for r in grid), default=0)
    label_col = max(range(width), key=lambda c: _col_hits(grid, c))
    if _col_hits(grid, label_col) < 2:
        return []
    label_rows: dict[int, str] = {}
    for i in range(len(grid)):
        if label_col < len(grid[i]):
            field = normalize_header(grid[i][label_col])
            if field is not None:
                label_rows[i] = field

    sample_cols = [c for c in range(width) if c != label_col]

    # Имя образца: первый текст выше первой строки-метки.
    first_label = min(label_rows) if label_rows else len(grid)
    names: dict[int, str] = {}
    for c in sample_cols:
        for i in range(first_label):
            if c < len(grid[i]) and str(grid[i][c]).strip():
                names[c] = str(grid[i][c]).strip()
                break

    samples: list[Sample] = []
    for c in sample_cols:
        if all((c >= len(grid[i]) or not str(grid[i][c]).strip())
               for i in label_rows):
            continue
        fields = _empty_field()
        for i, field in label_rows.items():
            val = to_float(grid[i][c]) if c < len(grid[i]) else None
            if val is not None:
                fields[field] = val
        samples.append(_sample(names.get(c, ""), fields, c))
    return samples


def parse_grid(grid: list[list]) -> list[Sample]:
    """Автоопределить ориентацию и собрать образцы из 2D-сетки.

    Возвращает ``list[Sample]``; пустой список — если оксиды не распознаны.
    """
    layout = detect_layout(grid)
    if layout == "rows":
        return _parse_rows(grid)
    if layout == "cols":
        return _parse_cols(grid)
    return []


# ── Чтение 2D-сеток из файлов ────────────────────────────────────────────

def read_excel_grid(path: Path, sheet: int | str | None = None) -> list[list]:
    """Сетка значений листа Excel (по умолчанию — первый лист)."""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        ws = wb.worksheets[sheet] if isinstance(sheet, int) else (
            wb[sheet] if sheet else wb.active)
        if ws is None:
            return []
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def read_excel_grids(path: Path) -> list[tuple[str, list[list]]]:
    """Сетки всех листов книги (имя, сетка)."""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)])
                for ws in wb.worksheets]
    finally:
        wb.close()


def _decode_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv_grid(path: Path, separator: str | None = None) -> list[list]:
    """Сетка CSV: автоопределение кодировки и разделителя (``;``/``,``/tab)."""
    text = _decode_text(path)
    if separator is None:
        sample = "\n".join(line for line in text.splitlines()[:10] if line.strip())
        counts = {cand: sample.count(cand) for cand in (";", "\t", ",", "|")}
        separator = (max(counts, key=lambda c: counts[c])
                     if max(counts.values()) else ",")
    return [row for row in csv.reader(text.splitlines(), delimiter=separator)]


# ── Высокоуровневые загрузчики ───────────────────────────────────────────

def load_samples_excel(path: str | Path) -> list[Sample]:
    """Загрузить образцы из Excel, перебирая листы и выбирая лучший."""
    path = Path(path)
    best: list[Sample] = []
    best_score = 0
    for _title, grid in read_excel_grids(path):
        samples = parse_grid(grid)
        score = sum(1 for s in samples
                    if any(getattr(s.composition, f) for f in ("sio2", "al2o3")))
        if score > best_score:
            best, best_score = samples, score
    if best:
        logger.info("Auto-import: %d samples from %s", len(best), path.name)
    return best


def load_samples_csv(path: str | Path) -> list[Sample]:
    """Загрузить образцы из CSV с автоопределением структуры."""
    csv_path = Path(path)
    samples = parse_grid(read_csv_grid(csv_path))
    if samples:
        logger.info("Auto-import CSV: %d samples from %s",
                    len(samples), csv_path.name)
    return samples
