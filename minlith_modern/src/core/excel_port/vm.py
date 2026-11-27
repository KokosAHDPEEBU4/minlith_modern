"""VM, исполняющая VBA-макросы MINLITH поверх формульного движка.

Оригинальные макросы — это поток управления: они копируют значения ячеек
(результаты формул) в именованные диапазоны, выбирают ветки по булевым флагам
и переносят блоки между листами. Здесь этот поток воспроизводится точно.

Операции (из vba_structure.json):
  - Sheets(name)  -> выбрать активный лист
  - Goto(ref)     -> выбрать ячейку/имя (R1C1 'R5C8', A1 'H5', имя 'k_1')
  - Select(range) -> выбрать диапазон ('H5:H9')
  - Copy          -> скопировать значения выделения в буфер
  - Paste(op)     -> вставить буфер в выделение (xlNone | xlMultiply)
  - Clear         -> очистить выделение
  - If Range(f)   -> ветвление по булеву значению ячейки f
  - Call(name)    -> вызвать подпрограмму
  - other         -> ActiveSheet.Paste / Rows / Columns (частично)
"""

from __future__ import annotations

import re

from src.core.excel_port.workbook import Workbook, a1_to_rc, rc_to_a1

_R1C1_RE = re.compile(r"^R(\d+)C(\d+)$")
_A1_RE = re.compile(r"^([A-Za-z]{1,3})(\d+)$")
_RANGE_RE = re.compile(r"^([A-Za-z]{1,3}\d+):([A-Za-z]{1,3}\d+)$")


class VbaVM:
    """Исполнитель VBA-операций поверх Workbook."""

    def __init__(self, workbook: Workbook, structure: dict, max_calls: int = 2_000_000):
        self.wb = workbook
        self.procs: dict[str, dict] = {}
        for mod, procs in structure.items():
            for p in procs:
                self.procs[p["name"]] = p
        self.active_sheet = "Нач+Type 12"
        self.selection: list[tuple[str, str]] = [("Нач+Type 12", "A1")]
        self.selection_shape = (1, 1)
        self.clipboard: list = []
        self.clipboard_shape = (1, 1)
        self.call_log: list[str] = []
        self.assignments: list[str] = []  # имена в порядке первого присваивания
        self._assigned: set[str] = set()
        self.max_calls = max_calls
        self._calls = 0
        # обратная карта: (лист, координата) -> имя
        self._cell_to_name: dict[tuple[str, str], str] = {}
        for nm, (sheet, coord) in self.wb.names.items():
            self._cell_to_name.setdefault((sheet, coord), nm)

    # ------------------------------------------------------------------ API

    def run(self, entry: str) -> None:
        """Запустить процедуру по имени."""
        self._call(entry)

    # -------------------------------------------------------------- helpers

    def _resolve_ref(self, ref: str) -> tuple[str, str]:
        """Разрешить ссылку в (лист, координата)."""
        ref = ref.strip()
        # ссылка с указанием листа: 'Имя листа'!R305C3  или  Sheet!A1
        if "!" in ref:
            sheet_part, coord_part = ref.split("!", 1)
            sheet = sheet_part.strip().strip("'")
            coord_part = coord_part.strip().replace("$", "")
            m = _R1C1_RE.match(coord_part)
            if m:
                return sheet, rc_to_a1(int(m.group(1)), int(m.group(2)))
            m = _A1_RE.match(coord_part)
            if m:
                return sheet, coord_part.upper()
            raise ValueError(f"Не удалось разрешить ссылку: {ref!r}")
        # именованный диапазон
        if ref in self.wb.names:
            return self.wb.names[ref]
        m = _R1C1_RE.match(ref)
        if m:
            return self.active_sheet, rc_to_a1(int(m.group(1)), int(m.group(2)))
        m = _A1_RE.match(ref)
        if m:
            return self.active_sheet, ref.upper()
        raise ValueError(f"Не удалось разрешить ссылку: {ref!r}")

    def _resolve_selection(self, ref: str) -> list[tuple[str, str]]:
        """Разрешить ссылку/диапазон в список ячеек (строка за строкой)."""
        ref = ref.strip()
        # квалификатор листа
        sheet = self.active_sheet
        if "!" in ref:
            sheet_part, ref = ref.split("!", 1)
            sheet = sheet_part.strip().strip("'")
            ref = ref.strip()
        m = _RANGE_RE.match(ref)
        if m:
            r1, c1 = a1_to_rc(m.group(1).upper())
            r2, c2 = a1_to_rc(m.group(2).upper())
            cells = []
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    cells.append((sheet, rc_to_a1(r, c)))
            return cells
        return [self._resolve_ref(ref) if sheet == self.active_sheet
                else self._resolve_ref(f"'{sheet}'!{ref}")]

    def _read_cells(self, cells: list[tuple[str, str]]) -> list:
        return [self.wb.eval_cell(s, c) for s, c in cells]

    def _flag_value(self, ref: str) -> bool:
        s, c = self._resolve_ref(ref)
        v = self.wb.eval_cell(s, c)
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0.0
        return bool(v)

    def _write_cells(self, cells: list[tuple[str, str]], values: list, op: str) -> None:
        """Записать значения в ячейки. op: xlNone | xlMultiply."""
        if op and op.lower() == "xlmultiply":
            for i, (s, c) in enumerate(cells):
                cur = self.wb.eval_cell(s, c)
                cur = 0.0 if cur is None else cur
                factor = values[i] if i < len(values) else values[-1] if values else 1.0
                factor = 0.0 if factor is None else factor
                self.wb.set_value(s, c, float(cur) * float(factor))
        else:
            for i, (s, c) in enumerate(cells):
                v = values[i] if i < len(values) else (values[-1] if values else None)
                self.wb.set_value(s, c, v)
                self._record_assignment(s, c)

    def _record_assignment(self, sheet: str, coord: str) -> None:
        """Зафиксировать первое присваивание именованной переменной."""
        name = self._cell_to_name.get((sheet, coord))
        if name is not None and name not in self._assigned:
            self._assigned.add(name)
            self.assignments.append(name)

    # ------------------------------------------------------------ execution

    def _call(self, name: str) -> None:
        self._calls += 1
        if self._calls > self.max_calls:
            raise RuntimeError(f"Превышен лимит вызовов ({self.max_calls})")
        p = self.procs.get(name)
        if p is None:
            # нет такой процедуры (например, clean_3) — пропускаем
            self.call_log.append(f"?{name}")
            return
        self.call_log.append(name)
        self._exec_ops(p["ops"])

    def _exec_ops(self, ops: list[dict]) -> None:
        i = 0
        n = len(ops)
        while i < n:
            op = ops[i]
            kind = op["op"]
            if kind == "If Range":
                else_i, end_i = self._find_branch(ops, i)
                cond = self._flag_value(op["arg"])
                if cond:
                    body = ops[i + 1:else_i] if else_i is not None else ops[i + 1:end_i]
                    self._exec_ops(body)
                else:
                    if else_i is not None:
                        self._exec_ops(ops[else_i + 1:end_i])
                i = end_i + 1
                continue
            self._exec_op(op)
            i += 1

    @staticmethod
    def _find_branch(ops: list[dict], start: int) -> tuple[int | None, int]:
        """Найти индексы Else (на уровне 1) и End If для If Range на позиции start."""
        depth = 0
        else_i = None
        j = start + 1
        n = len(ops)
        while j < n:
            o = ops[j]
            if o["op"] == "If Range":
                depth += 1
            elif o["op"] == "other" and o["arg"] == "End If":
                if depth == 0:
                    return else_i, j
                depth -= 1
            elif o["op"] == "other" and o["arg"] == "Else":
                if depth == 0:
                    else_i = j
            j += 1
        return else_i, n  # End If не найден

    def _exec_op(self, op: dict) -> None:
        kind = op["op"]
        arg = op["arg"]
        if kind == "Sheets":
            self.active_sheet = arg
        elif kind == "Goto":
            self.selection = self._resolve_selection(arg)
            self.selection_shape = _shape(self.selection)
        elif kind == "Select":
            self.selection = self._resolve_selection(arg)
            self.selection_shape = _shape(self.selection)
        elif kind == "Copy":
            self.clipboard = self._read_cells(self.selection)
            self.clipboard_shape = self.selection_shape
        elif kind == "Paste":
            target = self._expand_target(self.selection, self.clipboard_shape)
            self._write_cells(target, self.clipboard, arg)
        elif kind == "Clear":
            for s, c in self.selection:
                self.wb.set_value(s, c, None)
        elif kind == "Formula":
            for s, c in self.selection:
                self.wb.set_value(s, c, arg if arg else None)
        elif kind == "Call":
            self._call(arg)
        elif kind == "other":
            self._exec_other(arg)
        else:
            # неизвестная операция — игнорируем
            pass

    def _exec_other(self, line: str) -> None:
        if line.startswith("ActiveSheet.Paste"):
            target = self._expand_target(self.selection, self.clipboard_shape)
            self._write_cells(target, self.clipboard, "xlNone")
        # Rows/Columns/Selection.Insert/Delete/Cut — операции вывода,
        # для расчёта минералов не критичны; игнорируем.
        return

    def _expand_target(self, selection: list[tuple[str, str]],
                       shape: tuple[int, int]) -> list[tuple[str, str]]:
        """Расширить выделение от левого верхнего угла до формы буфера.

        Excel при вставке заполняет область размером с буфер, начиная с
        активной ячейки. Например, буфер 5x1 (H5:H9) в F12 -> F12:F16.
        """
        if not selection:
            return selection
        nr, nc = shape
        if nr <= 1 and nc <= 1:
            return selection
        sheet, coord = selection[0]
        r0, c0 = a1_to_rc(coord)
        cells = []
        for r in range(r0, r0 + nr):
            for c in range(c0, c0 + nc):
                cells.append((sheet, rc_to_a1(r, c)))
        return cells


def _shape(cells: list[tuple[str, str]]) -> tuple[int, int]:
    """Определить форму диапазона (nrows, ncols) по координатам."""
    if not cells:
        return (0, 0)
    coords = [c for _, c in cells]
    rows = []
    cols = []
    for c in coords:
        r, col = a1_to_rc(c)
        rows.append(r)
        cols.append(col)
    nr = max(rows) - min(rows) + 1
    nc = max(cols) - min(cols) + 1
    return (nr, nc)
