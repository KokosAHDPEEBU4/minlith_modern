"""Отчёт сравнения чистого движка с полным графом excel_port.

Фаза 4: для каждого образца сверяем `excel_parity` с `excel_port(rounding=False)`
по трём независимым срезам выхода:
  * vars      — значения именованных переменных (ф.е.);
  * row287    — итоговая строка B..AI листа «Нач+Type 12» (нормированные %);
  * defect    — невязки D164..D171 (ф.е.).

Результат — CSV в `reports/comparison/<sample>/` и сводка `summary.csv`
плюс печать максимумов отклонений на консоль. Ожидание: 0 расхождений.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.core.excel_parity.runner import run_sample as excel_run
from src.core.excel_port.runner import load_structure, load_workbook
from src.core.excel_port.vm import VbaVM

SKIP_VARS = {"f", "z", "n_1", "n_2", "n_3", "_calls", "_assignments"}

DATA = Path(__file__).resolve().parent.parent / "excel_port" / "data"
OUT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "reports" \
    / "comparison"

# колонки строки 287: B..AI (2..35)
COLS287 = []
_n = 2
while len(COLS287) < 34:
    c = ""
    x = _n
    while x:
        x, r = divmod(x - 1, 26)
        c = chr(65 + r) + c
    COLS287.append(c + "287")
    _n += 1

DEFECT_CELLS = {"D164": "SiO2", "D165": "Al2O3", "D166": "Na2O", "D167": "K2O",
                "D168": "MgO", "D169": "FeO", "D170": "CaO", "D171": "MnO"}


def excel_common(ox: dict[str, float], rounding: bool = False) -> dict[str, float]:
    """Все именованные переменные excel_port (режим без округлений)."""
    return {k: v for k, v in __excel_run(ox, rounding).items()
            if isinstance(v, int | float)}


def excel_cells(ox: dict[str, float], coords: list[str], rounding: bool = False):
    """Значения произвольных ячеек после полного прогона VBA."""
    wb, vm = __excel_run(ox, rounding, return_ctx=True)
    out = []
    for c in coords:
        v = wb.eval_cell("Нач+Type 12", c)
        out.append(v[0] if isinstance(v, tuple) else v)
    return out


def __excel_run(ox: dict[str, float], rounding: bool,
                return_ctx: bool = False):
    wb = load_workbook(DATA, rounding=rounding)
    struct = load_structure(DATA)
    wb.set_input("Нач+Type 3", ox)
    vm = VbaVM(wb, struct)
    vm.active_sheet = "Нач+Type 3"
    vm.run("aDefin")
    result = {}
    for name, (sheet, coord) in wb.names.items():
        try:
            result[name] = wb.eval_cell(sheet, coord)
        except Exception as e:  # noqa: BLE001
            result[name] = f"ERR:{e}"
    return (wb, vm) if return_ctx else result


def _el(o):
    return o[0] if isinstance(o, tuple) else o


def compare_sample(ox: dict[str, float]) -> dict:
    cr = excel_run(ox)
    excel_vars = excel_common(ox)

    rows_vars = []
    max_var = 0.0
    for name in sorted(set(cr.names) & set(excel_vars) - SKIP_VARS):
        b = cr.names[name]
        a = excel_vars[name]
        if not isinstance(b, int | float) or not isinstance(a, int | float):
            continue
        d = abs(a - b)
        max_var = max(max_var, d)
        rows_vars.append((name, a, b, d))

    excel287 = excel_cells(ox, COLS287)
    rows_287 = [(c, _el(e), w, abs(_el(e) - w))
                for c, e, w in zip(COLS287, excel287, cr.out.row287)]
    max_287 = max((r[3] for r in rows_287), default=0.0)

    excel_def = excel_cells(ox, list(DEFECT_CELLS))
    rows_def = [(oxide, _el(e), cr.out.defect[oxide],
                 abs(_el(e) - cr.out.defect[oxide]))
                for cell, oxide in DEFECT_CELLS.items()
                for e in [excel_def[list(DEFECT_CELLS).index(cell)]]]
    max_def = max((r[3] for r in rows_def), default=0.0)

    return {
        "vars": rows_vars, "row287": rows_287, "defect": rows_def,
        "max_var": max_var, "max_287": max_287, "max_def": max_def,
    }


def write_report(name: str, ox: dict[str, float]) -> dict:
    rep = compare_sample(ox)
    d = OUT_ROOT / name
    d.mkdir(parents=True, exist_ok=True)

    with (d / "vars.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variable", "excel_full", "excel_parity", "delta_abs"])
        w.writerows(rep["vars"])
    with (d / "row287.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cell", "excel_full", "excel_parity", "delta_abs"])
        w.writerows(rep["row287"])
    with (d / "defect.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["oxide", "excel_full", "excel_parity", "delta_abs"])
        w.writerows(rep["defect"])
    return rep


def main() -> None:
    multi = json.loads((DATA / "reference_multi.json").read_text(encoding="utf-8"))
    one = json.loads((DATA / "reference.json").read_text(encoding="utf-8"))
    comps: dict[str, dict[str, float]] = {
        "BK-1": one["BK-1"]["input"], "T-O2": one["T-O2"]["input"],
    }
    for k, v in multi.items():
        comps[k] = v["input"]

    summary = []
    for name, ox in comps.items():
        rep = write_report(name, ox)
        summary.append((name, rep["max_var"], rep["max_287"], rep["max_def"]))
        print(f"{name:13s} max|d| vars={rep['max_var']:.2e} "
              f"row287={rep['max_287']:.2e} defect={rep['max_def']:.2e}")

    with (OUT_ROOT / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample", "max_delta_vars", "max_delta_row287", "max_delta_defect"])
        w.writerows(summary)
    print(f"\nОтчёты -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
