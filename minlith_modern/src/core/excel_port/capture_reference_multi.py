"""Захват эталона для образцов всех 5 типов (Type 1-5) через макросы Excel."""
import json
from pathlib import Path

import win32com.client

XLSM = r"C:\Users\kokos\Desktop\Lene\Ispravlenny_MINLITH1_2010.xlsm"
OUT = Path(r"C:\Users\kokos\Desktop\Lene\minlith_modern\src\core\excel_port\data\reference_multi.json")

SAMPLES = {
    "arkose_t1":    {"SiO2":70.0,"Al2O3":12.0,"Fe2O3":1.0,"FeO":0.5,"MgO":0.3,"CaO":0.5,"Na2O":3.0,"K2O":6.0},
    "granite_t2":   {"SiO2":72.0,"Al2O3":14.0,"Fe2O3":1.5,"FeO":1.0,"MgO":0.5,"CaO":1.5,"Na2O":3.5,"K2O":4.5,"P2O5":0.2},
    "basalt_t3":    {"SiO2":50.0,"Al2O3":14.5,"Fe2O3":3.0,"FeO":9.0,"MgO":8.0,"CaO":10.5,"Na2O":2.5,"K2O":0.5,"TiO2":1.5,"P2O5":0.3},
    "quartzite_t4": {"SiO2":95.0,"Al2O3":2.5,"Fe2O3":0.5,"FeO":0.3,"MgO":0.2,"CaO":0.1,"Na2O":0.2,"K2O":0.5},
    "highal_t5":    {"SiO2":45.0,"Al2O3":35.0,"Fe2O3":2.0,"FeO":5.0,"MgO":3.0,"CaO":1.0,"Na2O":2.0,"K2O":4.0},
}

ROW_OF = {"SiO2":2,"TiO2":3,"Al2O3":4,"Fe2O3":5,"FeO":6,"MgO":7,"CaO":8,
          "Na2O":9,"K2O":10,"P2O5":11,"MnO":12,"C":13,"SO3":14,"F":15,
          "Cl":16,"S":17,"CO2":18,"SO":19}
EXTRA = ["F20","F21","F22","F24","F25","F26","F12","F13","F14","F15","F16","G2","I2"]


def _rc(coord):
    letters = "".join(ch for ch in coord if ch.isalpha())
    row = int(coord[len(letters):])
    col = 0
    for ch in letters.upper():
        col = col * 26 + (ord(ch) - 64)
    return row, col


def run_sample(comp):
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.EnableEvents = False
    try:
        wb = excel.Workbooks.Open(XLSM, UpdateLinks=0)
        ws = wb.Worksheets("ИСХ ДАННЫЕ")
        for oxide, wt in comp.items():
            ws.Cells(ROW_OF[oxide], 2).Value = wt
        excel.Application.Run("aut_1")
        excel.Application.Run("aut_1a")
        excel.CalculateFullRebuild()

        result = {"input": comp, "names": {}, "cells": {}}
        for i in range(1, wb.Names.Count + 1):
            nm = wb.Names(i)
            try:
                result["names"][nm.Name] = nm.RefersToRange.Value
            except Exception:
                result["names"][nm.Name] = None
        ws3 = wb.Worksheets("Нач+Type 3")
        for coord in EXTRA:
            row, col = _rc(coord)
            result["cells"][coord] = ws3.Cells(row, col).Value
        ws12 = wb.Worksheets("Нач+Type 12")
        result["row287"] = [ws12.Cells(287, c).Value for c in range(2, 36)]
        result["defect"] = [ws12.Cells(r, 4).Value for r in range(164, 172)]
        return result
    finally:
        try:
            wb.Close(SaveChanges=False)
        except Exception:
            pass
        excel.Quit()


def main():
    ref = {}
    for name, comp in SAMPLES.items():
        print(f"Запуск макросов: {name}...")
        ref[name] = run_sample(comp)
        print(f"  flags={[ref[name]['cells'].get(f'F{x}') for x in [20,21,22,24,25,26]]}")
    OUT.write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("Сохранено:", OUT)


if __name__ == "__main__":
    main()
