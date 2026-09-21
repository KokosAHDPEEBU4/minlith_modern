"""Проверка паритета «ОРИГИНАЛЬНЫЙ Excel MINLITH vs наш код».

Для каждого из N образцов:
  1. запускаем макросы aut_1/aut_1a в живом Excel (win32com) и читаем
     итог «Нач+Type 12»: строку 287 (минералы, %), невязки D164..D171 (ф.е.),
     именованные переменные и ячейки коэффициентов (G2=F, I2=A, F20..F26=флаги);
  2. считаем тот же образец нашим кодом:
       - excel_parity — чистый движок «Как в Excel» (float64, без округлений);
       - excel_port(rounding=True) — полный порт формул+VBA с ROUND как в оригинале;
  3. сравниваем и печатаем таблицу расхождений + сохраняем CSV-отчёты.

Скрипт пригоден для повторного запуска после правок движка:
    python scripts/verify_excel_parity.py
Код возврата: 0 — достоверных расхождений нет; 1 — есть («!» / «?»).

Метки по |d| = |Excel − excel_parity|:
    "="  совпадает точно
    "+"  в пределах пошагового округления Excel (|d| <= TOL_SUSPECT)
    "?"  подозрение на расхождение (TOL_SUSPECT < |d| <= TOL_BAD)
    "!"  достоверное расхождение (|d| > TOL_BAD)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import win32com.client  # noqa: E402

from src.core.excel_parity.runner import run_sample as py_run  # noqa: E402
from src.core.excel_port.runner import run_sample as port_run  # noqa: E402

XLSM = r"C:\Users\kokos\Desktop\Lene\src_excel\Ispravlenny_MINLITH1_2010.xlsm"

ROW_OF = {"SiO2": 2, "TiO2": 3, "Al2O3": 4, "Fe2O3": 5, "FeO": 6,
          "MgO": 7, "CaO": 8, "Na2O": 9, "K2O": 10, "P2O5": 11,
          "MnO": 12, "C": 13, "SO3": 14, "F": 15, "Cl": 16,
          "S": 17, "CO2": 18, "SO": 19}
ALL_OXIDES = list(ROW_OF)

DEFECT_OXIDES = ["SiO2", "Al2O3", "Na2O", "K2O", "MgO", "FeO", "CaO", "MnO"]
COEFF_PARAMS = ["F", "A", "k1", "k2", "k3", "k4", "achl"]

TOL_SUSPECT = 0.01  # больше — кандидат на расхождение
TOL_BAD = 0.05      # больше — достоверное расхождение

SAMPLES: dict[str, dict[str, float]] = {
    "arkose_t1": {  # тип 1, низкое Al
        "SiO2": 70.0, "Al2O3": 12.0, "Fe2O3": 1.0, "FeO": 0.5, "MgO": 0.3,
        "CaO": 0.5, "Na2O": 3.0, "K2O": 6.0,
    },
    "granite_t2": {  # тип 2, умеренное Al
        "SiO2": 72.0, "Al2O3": 14.0, "Fe2O3": 1.5, "FeO": 1.0, "MgO": 0.5,
        "CaO": 1.5, "Na2O": 3.5, "K2O": 4.5, "P2O5": 0.2,
    },
    "basalt_t3": {  # тип 3, среднее Al, много Fe/Mg
        "SiO2": 50.0, "Al2O3": 14.5, "Fe2O3": 3.0, "FeO": 9.0, "MgO": 8.0,
        "CaO": 10.5, "Na2O": 2.5, "K2O": 0.5, "TiO2": 1.5, "P2O5": 0.3,
    },
    "quartzite_t4": {  # тип 4, кремнезём
        "SiO2": 95.0, "Al2O3": 2.5, "Fe2O3": 0.5, "FeO": 0.3, "MgO": 0.2,
        "CaO": 0.1, "Na2O": 0.2, "K2O": 0.5,
    },
    "highal_t5": {  # тип 5, высокое Al
        "SiO2": 45.0, "Al2O3": 35.0, "Fe2O3": 2.0, "FeO": 5.0, "MgO": 3.0,
        "CaO": 1.0, "Na2O": 2.0, "K2O": 4.0,
    },
    "BK1_pyrocl": {  # типовой песчаник/вулканогенка: C, SO3, F
        "SiO2": 52.31, "TiO2": 0.66, "Al2O3": 16.46, "Fe2O3": 0.91941,
        "FeO": 4.43, "MgO": 0.11, "CaO": 6.8, "Na2O": 8.08, "K2O": 4.26,
        "P2O5": 1.85, "MnO": 0.12, "C": 0.0, "SO3": 3.54, "F": 0.41,
        "Cl": 0.0, "S": 0.0, "CO2": 0.0, "SO": 0.0,
    },
    "TO2_shale": {  # высокое MnO, углерод
        "SiO2": 52.5, "TiO2": 1.01, "Al2O3": 23.41, "Fe2O3": 1.71,
        "FeO": 8.06, "MgO": 2.35, "CaO": 0.28, "Na2O": 0.94, "K2O": 3.45,
        "P2O5": 0.31, "MnO": 0.157502, "C": 0.44, "SO3": 0.0, "F": 0.0,
        "Cl": 0.0, "S": 0.0, "CO2": 0.0, "SO": 0.0,
    },
    "shale_lowAl_highK": {  # низкое Al, очень высокое K
        "SiO2": 55.0, "TiO2": 0.5, "Al2O3": 7.0, "Fe2O3": 1.0, "FeO": 1.5,
        "MgO": 1.2, "CaO": 1.0, "Na2O": 2.5, "K2O": 8.0, "P2O5": 0.1,
    },
    "carbonate_dolomite": {  # карбонат/доломит: анкерит, кальцит
        "SiO2": 8.0, "TiO2": 0.2, "Al2O3": 1.5, "Fe2O3": 0.5, "FeO": 1.0,
        "MgO": 15.0, "CaO": 38.0, "Na2O": 0.2, "K2O": 0.4, "P2O5": 0.05,
        "MnO": 0.3, "C": 0.5, "SO3": 0.5, "F": 0.0, "Cl": 0.0, "S": 0.4,
        "CO2": 3.5, "SO": 0.0,
    },
    "ferro_magnesial": {  # железисто-магнезиальная: ht/sd/srp/mst
        "SiO2": 55.0, "TiO2": 0.8, "Al2O3": 10.0, "Fe2O3": 1.0, "FeO": 12.0,
        "MgO": 12.0, "CaO": 3.0, "Na2O": 1.0, "K2O": 1.0, "P2O5": 0.2,
        "MnO": 2.0,
    },
}


def norm(comp: dict[str, float]) -> dict[str, float]:
    """Полный профиль оксидов (недостающие = 0) для обеих сторон."""
    return {o: float(comp.get(o, 0.0) or 0.0) for o in ALL_OXIDES}


def _scalar(v):
    """Распаковать значение ячейки COM (1x1 / 1xN / NxM)."""
    while isinstance(v, tuple):
        v = v[0]
    return v


def _num(v, default=None):
    try:
        x = _scalar(v)
        return float(x) if isinstance(x, (int, float)) else default
    except (TypeError, ValueError):
        return default


class ExcelSession:
    """Один запущенный экземпляр Excel: книга открыта один раз, образцы гоняются
    в ней подряд (макросы aut_1/aut_1a перезапускаются для каждого входа)."""

    def __init__(self) -> None:
        self.excel = win32com.client.DispatchEx("Excel.Application")
        self.excel.Visible = False
        self.excel.DisplayAlerts = False
        self.excel.EnableEvents = False
        self.wb = self.excel.Workbooks.Open(XLSM, UpdateLinks=0)

    def run(self, comp: dict[str, float]) -> dict:
        ws = self.wb.Worksheets("ИСХ ДАННЫЕ")
        for r in range(2, 20):
            ws.Cells(r, 2).Value = 0.0
        for oxide, wt in comp.items():
            if wt:
                ws.Cells(ROW_OF[oxide], 2).Value = wt

        self.excel.Application.Run("aut_1")
        self.excel.Application.Run("aut_1a")
        self.excel.CalculateFullRebuild()

        names = {}
        for i in range(1, self.wb.Names.Count + 1):
            nm = self.wb.Names(i)
            try:
                names[nm.Name] = _num(nm.RefersToRange.Value)
            except Exception:
                names[nm.Name] = None

        ws3 = self.wb.Worksheets("Нач+Type 3")
        cells = {}
        coords = ["G2", "I2"] + [f"{ch}{r}" for ch in ("E", "F")
                                 for r in range(20, 27)]
        for coord in coords:
            letters = "".join(ch for ch in coord if ch.isalpha())
            row = int(coord[len(letters):])
            col = 0
            for ch in letters.upper():
                col = col * 26 + (ord(ch) - 64)
            cells[coord] = ws3.Cells(row, col).Value

        ws12 = self.wb.Worksheets("Нач+Type 12")
        row287 = [ws12.Cells(287, c).Value for c in range(2, 36)]
        defect = [ws12.Cells(r, 4).Value for r in range(164, 172)]
        return {"names": names, "cells": cells, "row287": row287, "defect": defect}

    def close(self) -> None:
        try:
            self.wb.Close(SaveChanges=False)
        except Exception:
            pass
        self.excel.Quit()


def mark(d: float) -> str:
    ad = abs(d)
    if ad < 5e-4:          # одинаковая точность хранения
        return "="
    if ad <= TOL_SUSPECT:
        return "+"
    if ad <= TOL_BAD:
        return "?"
    return "!"


def fmt(v) -> str:
    if v is None:
        return "-"
    return f"{v:.4f}"


def compare_sample(name: str, comp: dict[str, float], session: ExcelSession) -> dict:
    ox = norm(comp)

    py = py_run(ox)
    port = port_run(ox)
    ex = session.run(ox)

    # ---- коэффициенты и тип ----
    our = {
        "F": py.st0.F, "A": py.st0.A, "k1": py.st0.k1, "k2": py.st0.k2,
        "k3": py.st0.k3, "k4": py.st0.k4, "achl": py.st0.achl,
    }
    ex_coeff = {
        "F": _num(ex["cells"].get("G2")),
        "A": _num(ex["cells"].get("I2")),
        "k1": ex["names"].get("k_1"),
        "k2": ex["names"].get("k_2"),
        "k3": ex["names"].get("k_3"),
        "k4": ex["names"].get("k_4"),
        "achl": ex["names"].get("achl"),
    }
    def _port_coeff(p: str):
        if p == "achl" or not p.startswith("k"):
            return port.get(p)
        v = port.get("k_" + p[1:])
        return v if isinstance(v, (int, float)) else None

    coeff = []
    for p in COEFF_PARAMS:
        ev, ov = ex_coeff.get(p), our.get(p)
        coeff.append((p, ev, ov, _port_coeff(p),
                      ev - ov if ev is not None and ov is not None else None))

    # ---- именованные переменные (ф.е.) ----
    vars_rows = []
    for v, ov in py.names.items():
        if not isinstance(ov, (int, float)):
            continue
        ev = ex["names"].get(v)
        if ev is None:
            continue
        pv = port.get(v) if isinstance(port.get(v), (int, float)) else None
        vars_rows.append((v, ev, ov, pv, ev - ov))
    vars_rows.sort(key=lambda r: -abs(r[4]))

    # ---- row287 (%)
    row287 = []
    for i, ev in enumerate(ex["row287"]):
        x = i + 2
        col = ""
        while x:
            x, r = divmod(x - 1, 26)
            col = chr(65 + r) + col
        ov = py.out.row287[i]
        num = _num(ev)
        row287.append((col, num, ov,
                       num - ov if ov is not None and num is not None else None))

    # ---- невязки и их запись по столбцам (Excel D164..D171 vs наш defect) ----
    defect = []
    for i, oxide in enumerate(DEFECT_OXIDES):
        ev = _num(ex["defect"][i])
        ov = py.out.defect.get(oxide)
        defect.append((oxide, ev, ov, ev - ov if ev is not None and ov is not None else None))

    return {
        "ox": ox, "py": py, "ex": ex,
        "coeff": coeff, "vars": vars_rows, "row287": row287, "defect": defect,
        "rock": py.st0.rock_type,
        "flags": {k: _num(ex["cells"].get(k)) for k in
                  [f"{ch}{r}" for ch in ("E", "F") for r in range(20, 27)]},
    }


def count_bad(tables: dict, key: str) -> tuple[int, int]:
    n_q, n_b = 0, 0
    for row in tables[key]:
        d = row[-1]
        if d is None:
            continue
        m = mark(d)
        if m == "?":
            n_q += 1
        elif m == "!":
            n_b += 1
    return n_q, n_b


def main() -> int:
    out_root = ROOT.parent / "reports" / "comparison_live"
    out_root.mkdir(parents=True, exist_ok=True)

    summary = []
    n_bad_total = 0
    session = ExcelSession()
    try:
        for name, comp in SAMPLES.items():
            print("=" * 78, flush=True)
            print(f"== {name}", flush=True)
            t = compare_sample(name, comp, session)

            print(f"   тип: наш={t['rock']}  флаги Excel: "
                  + " ".join(f"{k}{int(v) if v is not None else '-'}"
                             for k, v in t["flags"].items()))
            print("   коэффициенты (F,A,k1..k4,achl):")
            print("     {:<5} {:>12} {:>12} {:>12} {:>10} {}".format(
                "пар", "Excel", "ours", "port", "|d|", "метка"))
            for p, ev, ov, pv, d in t["coeff"]:
                m = mark(d) if d is not None else "="
                print(f"     {p:<5} {fmt(ev):>12} {fmt(ov):>12} "
                      f"{fmt(pv):>12} "
                      f"{(abs(d) if d is not None else '-') :>10.4f}  {m}")

            nq_r, nb_r = count_bad(t, "row287")
            nq_d, nb_d = count_bad(t, "defect")
            nq_v, nb_v = count_bad(t, "vars")
            nq, nb = nq_r + nq_d + nq_v, nb_r + nb_d + nb_v
            n_bad_total += nb

            print(f"   row287: отличий >{TOL_SUSPECT}: {nq_r + nb_r} "
                  f"(достоверных: {nb_r})")
            for col, ev, ov, d in t["row287"]:
                if d is not None and abs(d) > TOL_SUSPECT:
                    print(f"     {col}287: Excel={fmt(ev)}  ours={fmt(ov)}  "
                          f"|d|={abs(d):.4f}  {mark(d)}")
            print(f"   defect:  отличий >{TOL_SUSPECT}: {nq_d + nb_d} "
                  f"(достоверных: {nb_d})")
            for oxide, ev, ov, d in t["defect"]:
                if d is not None and abs(d) > TOL_SUSPECT:
                    print(f"     {oxide:<6} Excel={fmt(ev)}  ours={fmt(ov)}  "
                          f"|d|={abs(d):.4f}  {mark(d)}")
            print(f"   vars (ф.е.): подозрительных {nq_v}, достоверных {nb_v}; "
                  f"топ-10 по |d|:")
            for v, ev, ov, pv, d in t["vars"][:10]:
                print(f"     {v:<8} Excel={fmt(ev)}  ours={fmt(ov)}  "
                      f"port={fmt(pv)}  |d|={abs(d):.4f}  {mark(d)}")

            summary.append((name, t["rock"], nq, nb))

            d = out_root / name
            d.mkdir(parents=True, exist_ok=True)
            with (d / "coeff.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["param", "excel", "excel_parity", "excel_port", "d_abs"])
                for p, ev, ov, pv, dd in t["coeff"]:
                    w.writerow([p, ev, ov, pv, abs(dd) if dd is not None else ""])
            with (d / "vars.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["variable", "excel", "excel_parity", "excel_port", "d_abs"])
                for v, ev, ov, pv, dd in t["vars"]:
                    w.writerow([v, ev, ov, pv, abs(dd) if dd is not None else ""])
            with (d / "row287.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["cell", "excel", "excel_parity", "d_abs"])
                for col, ev, ov, dd in t["row287"]:
                    w.writerow([col + "287", ev, ov, abs(dd) if dd is not None else ""])
            with (d / "defect.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["oxide", "excel", "excel_parity", "d_abs"])
                for oxide, ev, ov, dd in t["defect"]:
                    w.writerow([oxide, ev, ov, abs(dd) if dd is not None else ""])
    finally:
        session.close()

    with (out_root / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample", "rock_type", "suspect_count", "bad_count"])
        w.writerows(summary)

    print("=" * 78)
    print("ИТОГ")
    for name, rock, nq, nb in summary:
        print(f"  {name:<22} тип={rock}  подозрительных={nq}  "
              f"достоверных расхождений={nb}")
    print(f"Достоверных расхождений всего: {n_bad_total}")
    print(f"Отчёты: {out_root}")
    return 1 if n_bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
