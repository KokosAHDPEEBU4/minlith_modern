"""Извлечение формул, значений и именованных диапазонов из .xlsm.

Это Шаг 1.1 плана: собрать «сырые» данные оригинального MINLITH
(Ispravlenny_MINLITH1_2010.xlsm) в JSON, чтобы порт работал без Excel.

Сохранённые артефакты:
  - все формулы ячеек листов Нач+Type 12 / Нач+Type 3;
  - статические значения ячеек (текст/числа/константы);
  - карту именованных диапазонов → лист/адрес;
  - аудит: какие Excel-функции и стили ссылок встречаются.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

# Листы, содержащие расчётные формулы (портируем только их).
CALC_SHEETS = ["Нач+Type 12", "Нач+Type 3"]


def _sheet_refs(formula: str) -> list[str]:
    """Найти межлистовые ссылки вида 'Имя листа'! в формуле."""
    return re.findall(r"'([^']+)'!", formula)


def _funcs(formula: str) -> list[str]:
    """Найти вызываемые функции Excel (имена перед открывающей скобкой)."""
    return re.findall(r"(?<![A-Za-z0-9_.])([A-Za-z]+)\(", formula)


def _is_ref(token: str) -> bool:
    """Является ли токен ссылкой на ячейку (A1, R1C1) или именем? Приблизительно."""
    return bool(re.match(r"^[A-Za-z]{1,3}[0-9]+$", token))


def extract_workbook(xlsm_path: Path) -> dict:
    """Извлечь формулы/значения/имена из книги.

    Returns:
        dict с ключами: sheets, names, functions_audit, cross_sheet_refs.
    """
    wb = openpyxl.load_workbook(xlsm_path, data_only=False)

    sheets: dict[str, dict] = {}
    for sheet_name in CALC_SHEETS:
        ws = wb[sheet_name]
        cells: dict[str, dict] = {}
        funcs: dict[str, int] = {}
        xrefs: dict[str, int] = {}
        round_uses: list[str] = []
        n_formulas = 0
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if v is None:
                    continue
                entry: dict = {}
                if isinstance(v, str) and v.startswith("="):
                    entry["formula"] = v
                    n_formulas += 1
                    for f in _funcs(v):
                        funcs[f.upper()] = funcs.get(f.upper(), 0) + 1
                    for s in _sheet_refs(v):
                        xrefs[s] = xrefs.get(s, 0) + 1
                    if "ROUND(" in v.upper():
                        round_uses.append(c.coordinate)
                else:
                    entry["value"] = v
                cells[c.coordinate] = entry
        sheets[sheet_name] = {
            "max_row": ws.max_row,
            "max_col": ws.max_column,
            "n_formulas": n_formulas,
            "cells": cells,
            "funcs": funcs,
            "cross_sheet_refs": xrefs,
            "round_cells": round_uses,
        }

    # Именованные диапазоны
    names: dict[str, str] = {}
    for name, definition in wb.defined_names.items():
        # openpyxl: определение может быть DefinedName или иметь .attr_text
        target = getattr(definition, "attr_text", None)
        if target is None:
            # старые версии: str
            target = str(definition)
        names[name] = target

    return {
        "source": str(xlsm_path),
        "sheets": sheets,
        "names": names,
    }


def audit_sheet(sheet: dict) -> dict:
    """Собрать сводку аудита по листу."""
    return {
        "n_formulas": sheet["n_formulas"],
        "functions": dict(sorted(sheet["funcs"].items(), key=lambda x: -x[1])),
        "cross_sheet_refs": sheet["cross_sheet_refs"],
        "n_round_cells": len(sheet["round_cells"]),
    }


def main(xlsm_path: str, out_dir: str) -> None:
    src = Path(xlsm_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = extract_workbook(src)

    # JSON с формулами/значениями
    raw_path = out / "workbook_raw.json"
    raw_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # Краткий аудит (для человека)
    audit = {"source": data["source"], "names_count": len(data["names"]), "sheets": {}}
    for name, sheet in data["sheets"].items():
        audit["sheets"][name] = audit_sheet(sheet)
    # Имена, ссылающиеся на расчётные листы
    calc_audit_names = {}
    for nm, tgt in data["names"].items():
        hit = [s for s in CALC_SHEETS if f"'{s}'" in tgt or (s in tgt and tgt.startswith("'"))]
        if hit or any(s in tgt for s in CALC_SHEETS):
            calc_audit_names[nm] = tgt
    audit["names_on_calc_sheets"] = calc_audit_names

    audit_path = out / "workbook_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Извлечено из: {src}")
    print(f"  формулы Type 12: {data['sheets']['Нач+Type 12']['n_formulas']}")
    print(f"  формулы Type 3 : {data['sheets']['Нач+Type 3']['n_formulas']}")
    print(f"  именованных диапазонов: {len(data['names'])}")
    print(f"  JSON -> {raw_path}")
    print(f"  Audit -> {audit_path}")


if __name__ == "__main__":
    import sys

    xlsm = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\kokos\Desktop\Lene\Ispravlenny_MINLITH1_2010.xlsm"
    outdir = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\kokos\Desktop\Lene\minlith_modern\src\core\excel_port\data"
    main(xlsm, outdir)
