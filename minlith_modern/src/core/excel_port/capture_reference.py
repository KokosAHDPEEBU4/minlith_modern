"""Захват эталона: запуск макросов MINLITH через COM и чтение ВСЕХ переменных.

Для каждого образца:
  - пишем вход в ИСХ ДАННЫЕ
  - запускаем aut_1 + aut_1a (полный цикл)
  - читаем значения всех именованных диапазонов + ключевые ячейки
  - сохраняем в data/reference.json

Это эталон, с которым сверяем Python-порт на КАЖДОМ шаге.
"""
import json
import sys
from pathlib import Path

import win32com.client

XLSM = r"C:\Users\kokos\Desktop\Lene\Ispravlenny_MINLITH1_2010.xlsm"
OUT = Path(r"C:\Users\kokos\Desktop\Lene\minlith_modern\src\core\excel_port\data\reference.json")
samples = json.load(open(r"C:\Users\kokos\Desktop\Lene\minlith_modern\src\core\excel_port\data\samples.json", encoding="utf-8"))

ROW_OF = {"SiO2":2,"TiO2":3,"Al2O3":4,"Fe2O3":5,"FeO":6,"MgO":7,"CaO":8,
          "Na2O":9,"K2O":10,"P2O5":11,"MnO":12,"C":13,"SO3":14,"F":15,
          "Cl":16,"S":17,"CO2":18,"SO":19}

# ключевые ячейки помимо имён
EXTRA = ["D2","D4","D6","D7","D8","D9","D10","D11","D12","D13","D14","D16","D17",
         "G2","I2","E20","E21","E22","E24","E25","E26",
         "F20","F21","F22","F24","F25","F26",
         "F12","F13","F14","F15","F16"]


def run_sample(name):
    sample = samples[name]
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.EnableEvents = False
    try:
        wb = excel.Workbooks.Open(XLSM, UpdateLinks=0)
        ws = wb.Worksheets("ИСХ ДАННЫЕ")
        ws.Cells(1, 2).Value = name
        for oxide, wt in sample.items():
            ws.Cells(ROW_OF[oxide], 2).Value = wt
        excel.Application.Run("aut_1")
        excel.Application.Run("aut_1a")
        excel.CalculateFullRebuild()

        result = {"input": sample, "names": {}, "cells": {}}

        # все именованные диапазоны
        for i in range(1, wb.Names.Count + 1):
            nm = wb.Names(i)
            try:
                rng = nm.RefersToRange
                result["names"][nm.Name] = rng.Value
            except Exception:
                result["names"][nm.Name] = None

        # ключевые ячейки (лист Нач+Type 3 и Type 12)
        for coord in EXTRA:
            letters = "".join(ch for ch in coord if ch.isalpha())
            row = int(coord[len(letters):])
            col = 0
            for ch in letters.upper():
                col = col * 26 + (ord(ch) - 64)
            result["cells"][coord] = wb.Worksheets("Нач+Type 3").Cells(row, col).Value

        # строка 287 итог + defect
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
    for name in ["BK-1", "T-O2"]:
        print(f"Запуск макросов для {name}...")
        ref[name] = run_sample(name)
        n_names = len(ref[name]["names"])
        print(f"  имён: {n_names}, ключевых ячеек: {len(ref[name]['cells'])}")
    OUT.write_text(json.dumps(ref, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("Эталон сохранён:", OUT)


if __name__ == "__main__":
    main()
