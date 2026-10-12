"""Рабочая книга: модель данных поверх извлечённого workbook_raw.json.

Даёт доступ к ячейкам листов и именованным диапазонам, умеет вычислять
значение ячейки рекурсивно через FormulaEvaluator (с учётом зависимостей).

Это «сырая» модель для excel_port (точная реплика Excel). VM (Фаза 2) будет
поверх неё выполнять VBA-переходы.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from src.core.excel_port.interpreter import FormulaError, FormulaEvaluator

CALC_SHEETS = ["Нач+Type 12", "Нач+Type 3"]

_A1_RE = re.compile(r"^([A-Za-z]{1,3})(\d+)$")


@lru_cache(maxsize=16384)
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


@lru_cache(maxsize=16384)
def rc_to_a1(row: int, col: int) -> str:
    """Преобразовать (row, col) 1-индексно -> 'A1'."""
    letters = ""
    c = col
    while c > 0:
        c, rem = divmod(c - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return f"{letters}{row}"


# Защита от аномально больших диапазонов при построении графа зависимостей.
_MAX_RANGE_CELLS = 4096

# Граф зависимостей зависит только от статичных формул raw, поэтому
# разделяется между всеми Workbook на одном raw (run_sample создаёт
# экземпляр на каждый образец). Храним ссылку на raw рядом с ключом-id,
# чтобы id не переиспользовался после сборки мусора.
_DepsMap = dict[tuple[str, str], set[tuple[str, str]]]
_CoordSet = set[tuple[str, str]]
_ClosuresMap = dict[tuple[str, str], frozenset]
_DEP_GRAPH_CACHE: dict[int, tuple[dict, _DepsMap, _CoordSet, _ClosuresMap]] = {}
_DEP_GRAPH_CACHE_MAX = 8


def _formula_refs(formula: str, wb: Workbook, sheet: str) -> set[tuple[str, str]]:
    """Координаты (sheet, coord), которые читает формула.

    Используется только для инвалидации кэша, поэтому логика обязана
    зеркалить _Resolver.resolve/resolve_range: голая ссылка — на листе
    самой формулы, диапазон разворачивается ровно так же (включая случай
    «перевёрнутого» диапазона, который resolve_range читает как пустой).
    Незнакомые ссылки/синтаксис дают FormulaError -> формула попадает в
    консервативный набор «инвалидируем при любой записи».
    """
    from src.core.excel_port.interpreter import (
        BinOpNode,
        FormulaError,
        FuncNode,
        NegNode,
        RangeNode,
        RefNode,
        _parse_cached,
    )

    body = formula.strip()
    if body.startswith("="):
        body = body[1:]
    ast = _parse_cached(body)
    out: set[tuple[str, str]] = set()

    def ref_key(node: RefNode) -> tuple[str, str]:
        name = node.name
        if name in wb.names:
            return wb.names[name]
        if _A1_RE.match(name):
            return sheet, name
        raise FormulaError(f"Неизвестная ссылка: {name!r}")

    def walk(node: object) -> None:
        if isinstance(node, RefNode):
            out.add(ref_key(node))
        elif isinstance(node, RangeNode):
            ks, ke = ref_key(node.start), ref_key(node.end)
            if ks[0] != ke[0]:
                raise FormulaError("Диапазон между листами")
            r1, c1 = a1_to_rc(ks[1])
            r2, c2 = a1_to_rc(ke[1])
            # как в resolve_range: без нормализации границ
            if (r2 - r1 + 1) * (c2 - c1 + 1) > _MAX_RANGE_CELLS:
                raise FormulaError("Слишком большой диапазон")
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    out.add((ks[0], rc_to_a1(r, c)))
        elif isinstance(node, FuncNode):
            for arg in node.args:
                walk(arg)
        elif isinstance(node, BinOpNode):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, NegNode):
            walk(node.operand)

    walk(ast)
    return out


class Workbook:
    """Модель расчётной книги на основе JSON-дампа."""

    def __init__(self, raw: dict, round_fn=None):
        self.raw = raw
        self.cells: dict[str, dict[str, dict]] = {}  # sheet -> coord -> entry
        for sn in CALC_SHEETS:
            # Поверхностная копия: raw переиспользуется между прогонами
            # (runner._load_raw), записи VM идут заменой entry-словарей,
            # поэтому самого raw экземпляры не касаются.
            self.cells[sn] = dict(raw["sheets"][sn]["cells"])
        # имя -> (sheet, coord)
        self.names: dict[str, tuple[str, str]] = {}
        for name, target in raw["names"].items():
            parsed = self._parse_name_target(target)
            if parsed:
                self.names[name] = parsed
        self._resolver = _Resolver(self)
        self.evaluator = FormulaEvaluator(self._resolver, round_fn=round_fn)
        # Обратный граф зависимостей «ячейка -> зависимые от неё формулы»
        # и мемо транзитивных замыканий; строятся лениво при первой записи.
        self._dependents: dict[tuple[str, str], set[tuple[str, str]]] | None = None
        self._unknown_dep_cells: set[tuple[str, str]] | None = None
        self._closures: dict[tuple[str, str], frozenset] | None = None

    @staticmethod
    def _parse_name_target(target: str) -> tuple[str, str] | None:
        """'='Нач+Type 12'!$F$147' -> ('Нач+Type 12', 'F147')."""
        m = re.match(r"'([^']+)'!\$?([A-Za-z]+\$?\d+)", target)
        if not m:
            return None
        sheet, coord = m.group(1), m.group(2).replace("$", "")
        return sheet, coord

    def get_raw(self, sheet: str, coord: str) -> dict | None:
        """Вернуть запись ячейки ({'formula':...} или {'value':...})."""
        return self.cells.get(sheet, {}).get(coord)

    def set_value(self, sheet: str, coord: str, value) -> None:
        """Перезаписать ячейку значением (как VBA PasteSpecial xlValues)."""
        self.cells.setdefault(sheet, {})[coord] = {"value": value}
        self._resolver.invalidate_from(sheet, coord)

    def _ensure_dependency_graph(self) -> None:
        """Построить обратный граф зависимостей формул (однократно на raw)."""
        if self._dependents is not None:
            return
        raw_key = id(self.raw)
        cached = _DEP_GRAPH_CACHE.get(raw_key)
        if cached is not None and cached[0] is self.raw:
            _, shared_deps, shared_unknown, shared_closures = cached
            self._dependents = shared_deps
            self._unknown_dep_cells = shared_unknown
            self._closures = shared_closures
            return

        deps: dict[tuple[str, str], set[tuple[str, str]]] = {}
        unknown: set[tuple[str, str]] = set()
        for sn, cells in self.cells.items():
            for coord, entry in cells.items():
                formula = entry.get("formula") if isinstance(entry, dict) else None
                if not formula:
                    continue
                try:
                    refs = _formula_refs(formula, self, sn)
                except Exception:  # noqa: BLE001 — незнакомая формула: инвалидируем консервативно
                    unknown.add((sn, coord))
                    continue
                for key in refs:
                    deps.setdefault(key, set()).add((sn, coord))

        if len(_DEP_GRAPH_CACHE) >= _DEP_GRAPH_CACHE_MAX:
            _DEP_GRAPH_CACHE.clear()
        closures: dict[tuple[str, str], frozenset] = {}
        _DEP_GRAPH_CACHE[raw_key] = (self.raw, deps, unknown, closures)
        self._dependents = deps
        self._unknown_dep_cells = unknown
        self._closures = closures

    def _transitive_dependents(self, key: tuple[str, str]) -> frozenset:
        """Все формулы, транзитивно зависящие от ячейки key (memo на графе)."""
        memo = self._closures
        if memo is None:  # граф ещё не построен — считаем без memo
            self._ensure_dependency_graph()
            memo = self._closures or {}
        cached = memo.get(key)
        if cached is not None:
            return cached
        result: set[tuple[str, str]] = set()
        dependents = self._dependents or {}
        for dep in dependents.get(key, ()):
            result.add(dep)
            result |= self._transitive_dependents(dep)
        frozen = frozenset(result)
        memo[key] = frozen
        return frozen

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
        written: list[tuple[str, str]] = []
        cells = self.cells.setdefault(sheet, {})
        for oxide, wt in oxide_values.items():
            row = row_of.get(oxide)
            if row is None:
                continue
            coord = f"B{row}"
            cells[coord] = {"value": wt}
            written.append((sheet, coord))
        # одна инвалидация на весь вход: каждый оксид тянет почти все формулы
        self._resolver.invalidate_many(written)

    def formula_of(self, sheet: str, coord: str) -> str | None:
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

    def invalidate_from(self, sheet: str, coord: str) -> None:
        """Сбросить кэш для записанной ячейки и её транзитивных зависимых.

        Точечная замена clear_cache(): формулы, не зависящие от записи,
        остаются закэшированными и не пересчитываются.
        """
        self.invalidate_many([(sheet, coord)])

    def invalidate_many(self, keys: list[tuple[str, str]]) -> None:
        """Сбросить кэш для нескольких записанных ячеек и их зависимых."""
        self.wb._ensure_dependency_graph()
        cache = self._cache
        for key in keys:
            cache.pop(key, None)
            for dep in self.wb._transitive_dependents(key):
                cache.pop(dep, None)
        # формулы с не разобранными зависимостями инвалидируем при любой записи
        unknown = self.wb._unknown_dep_cells
        if unknown:
            for key in unknown:
                cache.pop(key, None)

    def clear_cache(self) -> None:
        self._cache.clear()
