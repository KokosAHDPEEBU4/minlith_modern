"""Извлечение VBA-модулей из .xlsm и структурный разбор.

Шаг 1.1 плана: выгрузить текст всех VBA-модулей и сделать первичный разбор
структуры (Sub-процедуры, вызовы Call, условия If Range, операции
Goto/Select/Copy/PasteSpecial), чтобы построить граф переходов для VM.

Артефакты в data/:
  - vba_modules.json  — сырой текст модулей (по одному на компонент);
  - vba_structure.json — структурный разбор (процедуры и их операции).
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from oletools.olevba import VBA_Parser

# VBA-операции, которые нас интересуют для VM (в порядке важности).
OP_PATTERNS = [
    ("If Range", re.compile(r"If Range\(\"([A-Za-z0-9_]+)\"\)\s*=\s*(True|False)\s*Then", re.I)),
    ("Call", re.compile(r"Call\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)),
    ("Goto", re.compile(r"Application\.Goto\s+Reference:=\"([^\"]*)\"", re.I)),
    ("Select", re.compile(r"Range\(\"([A-Za-z0-9:]+)\"\)\.Select", re.I)),
    ("Copy", re.compile(r"Selection\.Copy", re.I)),
    ("Paste", re.compile(r"PasteSpecial\s+Paste:=\s*xlValues(?:,\s*Operation:=\s*(xl\w+))?", re.I)),
    ("Sheets", re.compile(r"Sheets\(\"([^\"]+)\"\)\.Select", re.I)),
    ("Clear", re.compile(r"Selection\.ClearContents", re.I)),
    ("Formula", re.compile(r"ActiveCell\.FormulaR1C1\s*=\s*\"([^\"]*)\"", re.I)),
    ("RangeSelect", re.compile(r"Range\(\"([A-Za-z0-9:]+)\"\)\.Select", re.I)),
]


def _extract_vba_bin(xlsm_path: Path, out_dir: Path) -> None:
    """Достать vbaProject.bin из xlsm (это ZIP) и сохранить."""
    with zipfile.ZipFile(xlsm_path) as z:
        if "xl/vbaProject.bin" in z.namelist():
            data = z.read("xl/vbaProject.bin")
            (out_dir / "vbaProject.bin").write_bytes(data)
            print(f"  vbaProject.bin: {len(data)} bytes")
        else:
            print("  ! vbaProject.bin не найден в архиве")


def parse_modules(xlsm_path: Path) -> tuple[dict, dict]:
    """Распарсить VBA-проект.

    Returns:
        (modules_text, structure)
        modules_text: {имя_компонента: текст}
        structure: {имя_компонента: [ {sub: str, ops: [ {op, arg, line} ] } ]}
    """
    modules_text: dict[str, str] = {}
    structure: dict[str, list] = {}

    vp = VBA_Parser(str(xlsm_path))
    try:
        for (filename, stream_path, vba_filename, code) in vp.extract_all_macros():
            modules_text[vba_filename] = code
            structure[vba_filename] = _parse_code(code)
    finally:
        vp.close()

    return modules_text, structure


def _parse_code(code: str) -> list[dict]:
    """Разобрать код модуля на процедуры и их операции."""
    procs: list[dict] = []
    lines = code.splitlines()

    current: dict | None = None
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        # Пропускаем пустые строки и комментарии (строки, начинающиеся с ')
        if not line or line.startswith("'"):
            continue
        # Начало Sub/Function
        m = re.match(r"^(?:Public |Private )?(Sub|Function)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
        if m and not line.startswith("Attribute"):
            if current:
                procs.append(current)
            current = {
                "kind": m.group(1),
                "name": m.group(2),
                "start_line": lineno,
                "ops": [],
            }
            continue
        if current is None:
            continue
        if line == "End Sub" or line == "End Function":
            current["end_line"] = lineno
            procs.append(current)
            current = None
            continue
        # Записываем операции
        matched = False
        for op_name, pat in OP_PATTERNS:
            mm = pat.search(line)
            if mm:
                arg = mm.groups()[0] if mm.groups() else ""
                current["ops"].append({"op": op_name, "arg": arg, "line": lineno})
                matched = True
                break
        if not matched:
            # прочие значимые строки (например, Rows/Columns, ActiveSheet.Paste)
            if re.match(
                r"^(Rows|Columns|ActiveSheet\.|Selection\.|Sheets\(|If |Else|End If)",
                line,
            ):
                current["ops"].append({"op": "other", "arg": line[:80], "line": lineno})
    if current:
        procs.append(current)
    return procs


def main(xlsm_path: str, out_dir: str) -> None:
    src = Path(xlsm_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    _extract_vba_bin(src, out)

    modules_text, structure = parse_modules(src)

    (out / "vba_modules.json").write_text(
        json.dumps(modules_text, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out / "vba_structure.json").write_text(
        json.dumps(structure, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    n_subs = sum(len(p) for p in structure.values())
    print(f"  модулей: {len(modules_text)}, процедур: {n_subs}")
    for mod, procs in structure.items():
        print(f"    {mod}: {len(procs)} proc")


if __name__ == "__main__":
    import sys

    xlsm = (sys.argv[1] if len(sys.argv) > 1
            else r"C:\Users\kokos\Desktop\Lene\Ispravlenny_MINLITH1_2010.xlsm")
    outdir = (sys.argv[2] if len(sys.argv) > 2
              else r"C:\Users\kokos\Desktop\Lene\minlith_modern\src\core\excel_port\data")
    main(xlsm, outdir)
