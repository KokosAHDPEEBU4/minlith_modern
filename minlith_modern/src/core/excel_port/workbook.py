"""Рабочая книга: модель данных поверх извлечённого workbook_raw.json.

Даёт доступ к ячейкам листов и именованным диапазонам, умеет вычислять
значение ячейки рекурсивно через FormulaEvaluator (с учётом зависимостей).

Это «сырая» модель для excel_port (точная реплика Excel). VM (Фаза 2) будет
поверх неё выполнять VBA-переходы.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from src.core.excel_port.interpreter import FormulaEvaluator, FormulaError

CALC_SHEETS = ["Нач+Type 12", "Нач+Type 3"]

_A1_RE = re.compile(r"^([A-Za-z]{1,3})(\d+)$")


def a1_to_rc(coord: str) -> tuple[int, int]:
    """Преобразовать 'A1' -> (row, col) 1-индексно. 'D151' -> (151, 4)."""
    m = _A1_RE.match(coord)
    if not m:
        raise ValueError(f"Не A1-координата: {coord}")
    letters, digits = m.group(1), m.group(2)
    col = 0
    for ch in letters.upper():
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(digits), col


def rc_to_a1(row: int, col: int) -> str:
    """Преобразовать (row, col) 1-индексно -> 'A1'."""
    letters = ""
    c = col
    while c > 0:
        c, rem = divmod(c - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return f"{letters}{row}"


class Workbook:
    """Модель расчётной книги на основе JSON-дампа."""

    def __init__(self, raw: dict, round_fn=None):
        self.raw = raw
        self.cells: dict[str, dict[str, dict]] = {}  # sheet -> coord -> entry
        for sn in CALC_SHEETS:
            self.cells[sn] = raw["sheets"][sn]["cells"]
        # имя -> (sheet, coord)
        self.names: dict[str, tuple[str, str]] = {}
        for name, target in raw["names"].items():
            parsed = self._parse_name_target(target)
            if parsed:
                self.names[name] = parsed
        self._resolver = _Resolver(self)
        self.evaluator = FormulaEvaluator(self._resolver, round_fn=round_fn)

    @staticmethod
    def _parse_name_target(target: str) -> Optional[tuple[str, str]]:
        """'='Нач+Type 12'!$F$147' -> ('Нач+Type 12', 'F147')."""
        m = re.match(r"'([^']+)'!\$?([A-Za-z]+\$?\d+)", target)
        if not m:
            return None
        sheet, coord = m.group(1), m.group(2).replace("$", "")
        return sheet, coord

    def get_raw(self, sheet: str, coord: str) -> Optional[dict]:
        """Вернуть запись ячейки ({'formula':...} или {'value':...})."""
        return self.cells.get(sheet, {}).get(coord)

    def set_value(self, sheet: str, coord: str, value) -> None:
        """Перезаписать ячейку значением (как VBA PasteSpecial xlValues)."""
        self.cells.setdefault(sheet, {})[coord] = {"value": value}
        self._resolver.clear_cache()

    def set_input(self, sheet: str, oxide_values: dict[str, float],
                  row_of: dict[str, int] | None = None) -> None:
        """Записать весовые проценты оксидов в B-колонку листа.

        row_of: отображение «имя оксида» -> строка (по умолчанию
        SiO2=2, TiO2=3, ..., SO=19, как в листах).
        """
        default_row = {
            "SiO2": 2, "TiO2": 3, "Al2O3": 4, "Fe2O3": 5, "FeO": 6,
            "MgO": 7, "CaO": 8, "Na2O": 9, "K2O": 10, "P2O5": 11,
            "MnO": 12, "C": 13, "SO3": 14, "F": 15, "Cl": 16,
            "S": 17, "CO2": 18, "SO": 19,
        }
        row_of = row_of or default_row
        for oxide, wt in oxide_values.items():
            row = row_of.get(oxide)
            if row is None:
                continue
            self.set_value(sheet, f"B{row}", wt)

    def formula_of(self, sheet: str, coord: str) -> Optional[str]:
        entry = self.get_raw(sheet, coord)
        if entry and "formula" in entry:
            return entry["formula"]
        return None

    def eval_cell(self, sheet: str, coord: str) -> object:
        """Вычислить значение ячейки (с учётом зависимостей)."""
        return self._resolver._cell_value(sheet, coord)

    def has_cell(self, sheet: str, coord: str) -> bool:
        return coord in self.cells.get(sheet, {})

    def sheet_names(self) -> list[str]:
        return CALC_SHEETS

    def load(self, path: Path):
        self.__init__(json.loads(path.read_text(encoding="utf-8")))
        return self


class _Resolver:
    """Резолвер для FormulaEvaluator: имя или A1 -> значение из Workbook."""

    def __init__(self, wb: Workbook):
        self.wb = wb
        self._cache: dict[tuple, object] = {}
        self._active_sheet: str = "Нач+Type 12"

    def set_active_sheet(self, sheet: str) -> None:
        self._active_sheet = sheet

    def resolve(self, name: str) -> object:
        """Разрешить имя (A1 или именованный диапазон) в значение."""
        name = name.replace("$", "")
        # именованный диапазон?
        if name in self.wb.names:
            sheet, coord = self.wb.names[name]
            return self._cell_value(sheet, coord)
        # A1 в активном листе
        if _A1_RE.match(name):
            return self._cell_value(self._active_sheet, name)
        raise FormulaError(f"Неизвестная ссылка: {name!r}")

    def resolve_range(self, start: str, end: str) -> list:
        """Вернуть список значений ячеек диапазона A1:B2 (в активном листе)."""
        start = start.replace("$", "")
        end = end.replace("$", "")
        if not (_A1_RE.match(start) and _A1_RE.match(end)):
            raise FormulaError(f"Диапазон не-A1: {start}:{end}")
        r1, c1 = a1_to_rc(start)
        r2, c2 = a1_to_rc(end)
        sheet = self._active_sheet
        values = []
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                values.append(self._cell_value(sheet, rc_to_a1(r, c)))
        return values

    def _cell_value(self, sheet: str, coord: str) -> object:
        key = (sheet, coord)
        if key in self._cache:
            return self._cache[key]
        entry = self.wb.get_raw(sheet, coord)
        if entry is None:
            # ячейка пустая -> 0 по семантике Excel (пустая как 0 в формулах)
            self._cache[key] = 0.0
            return 0.0
        if "value" in entry:
            v = entry["value"]
            if v is None:
                # пустая ячейка: в арифметике Excel = 0
                v = 0.0
            self._cache[key] = v
            return v
        formula = entry["formula"]
        # вычисляем в контексте листа ячейки
        prev_sheet = self._active_sheet
        self._active_sheet = sheet
        try:
            val = self.wb.evaluator.eval_formula(formula)
        finally:
            self._active_sheet = prev_sheet
        self._cache[key] = val
        return val

    def clear_cache(self) -> None:
        self._cache.clear()
