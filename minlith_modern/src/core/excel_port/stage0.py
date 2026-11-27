"""Стадия 0 (подготовка) оригинального MINLITH — точная реплика.

Что делает:
  1. Пересчёт вес.% -> формульные единицы (ф.е.) в колонке D.
  2. Расчёт F (Fe3+/ΣFe) и A (Al/(Al+Fe)) — G2, I2.
  3. ВЫБОР коэффициентов k1-k4 и achl из таблицы-кандидата по диапазону F
     (и A для диапазона 0.69-0.87) — в оригинале это делают VBA-макросы
     u_0..u_10, копируя колонку H/J/L в F12:F16.
  4. Классификация типа породы по флагам F20-F26 (лист Нач+Type 3).

Таблица коэффициентов (лист Нач+Type 3, точность 3 знака):
  Колонка H (строки 5-9):  F 0.00-0.21
  Колонка J (строки 5-9):  F 0.21-0.51
  Колонка L (строки 5-9):  F 0.51-0.69
  Колонка H (строки 12-16): F 0.69-0.87, A > 0.47
  Колонка J (строки 12-16): F 0.69-0.87, 0.40 < A < 0.47
  Колонка L (строки 12-16): F 0.87-1.00

Порядок выбора (каскад VBA u_0..u_10):
  G17 -> H5:H9 ; H17 -> J5:J9 ; I17 -> L5:L9 ;
  J17 -> H12:H16 ; G18 -> J12:J16 ; I18 -> L12:L16
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.excel_port.workbook import Workbook

# Диапазоны-кандидаты: (флаг, колонка, первая строка)
_CANDIDATES = [
    ("G17", "H", 5),
    ("H17", "J", 5),
    ("I17", "L", 5),
    ("J17", "H", 12),
    ("G18", "J", 12),
    ("I18", "L", 12),
]

COEF_SHEET = "Нач+Type 3"


@dataclass
class Stage0Result:
    """Результат стадии 0."""

    fe: dict[str, float]          # формульные единицы оксидов (D2..D19)
    F: float                      # Fe3+/ΣFe
    A: float                      # Al/(Al+Fe)
    k1: float
    k2: float
    k3: float
    k4: float
    achl: float                   # формульный вес хлорита
    rock_type: int                # 1-5
    flags: dict[str, bool]        # F20..F26


def _fe_from_sheet(wb: Workbook, sheet: str) -> dict[str, float]:
    """Собрать ф.е. оксидов D2..D19 с листа.

    Ячейка D15 (F ф.е.) в оригинале содержит текстовую заглушку
    'ROUND(B15/C15*10000;2)-0,67*D11' (не формулу) и нигде не используется —
    трактуем как 0.
    """
    rows = {
        "SiO2": 2, "TiO2": 3, "Al2O3": 4, "Fe2O3": 5, "FeO": 6,
        "MgO": 7, "CaO": 8, "Na2O": 9, "K2O": 10, "P2O5": 11,
        "MnO": 12, "C": 13, "SO3": 14, "F": 15, "Cl": 16,
        "S": 17, "CO2": 18, "SO": 19,
    }
    out = {}
    for ox, r in rows.items():
        v = wb.eval_cell(sheet, f"D{r}")
        try:
            out[ox] = float(v)
        except (TypeError, ValueError):
            out[ox] = 0.0
    return out


def select_coefficients(wb: Workbook) -> tuple[float, float, float, float, float, str]:
    """Выбрать k1-k4 и achl по диапазону F (каскад VBA u_0..u_10).

    Возвращает (k1, k2, k3, k4, achl, использованный_флаг).
    Значения берутся из ячеек-кандидатов (H/J/L) на листе Type 3.
    """
    chosen_flag = None
    chosen = None
    for flag, col, r0 in _CANDIDATES:
        if bool(wb.eval_cell(COEF_SHEET, flag)):
            chosen_flag = flag
            chosen = (col, r0)
            break
    if chosen is None:
        raise ValueError("Не сработал ни один диапазон коэффициентов (F вне [0,1])")

    col, r0 = chosen
    # Ячейки: k1..k4 (r0..r0+3), achl (r0+4)
    k1 = float(wb.eval_cell(COEF_SHEET, f"{col}{r0}"))
    k2 = float(wb.eval_cell(COEF_SHEET, f"{col}{r0 + 1}"))
    k3 = float(wb.eval_cell(COEF_SHEET, f"{col}{r0 + 2}"))
    k4 = float(wb.eval_cell(COEF_SHEET, f"{col}{r0 + 3}"))
    achl = float(wb.eval_cell(COEF_SHEET, f"{col}{r0 + 4}"))
    return k1, k2, k3, k4, achl, chosen_flag


def write_coefficients(wb: Workbook, k1, k2, k3, k4, achl) -> None:
    """Записать выбранные коэффициенты в F12:F16 (как VBA PasteSpecial).

    Пишем на оба листа (VBA копирует A1:F19 из Type 3 в Type 12).
    """
    for sheet in ["Нач+Type 3", "Нач+Type 12"]:
        wb.set_value(sheet, "F12", k1)
        wb.set_value(sheet, "F13", k2)
        wb.set_value(sheet, "F14", k3)
        wb.set_value(sheet, "F15", k4)
        wb.set_value(sheet, "F16", achl)


def classify(wb: Workbook) -> tuple[int, dict[str, bool]]:
    """Классифицировать тип породы по флагам F20-F26 листа Type 3."""
    flags = {f"F{r}": bool(wb.eval_cell(COEF_SHEET, f"F{r}")) for r in range(20, 27)}
    if flags["F20"] or flags["F21"]:
        rt = 1
    elif flags["F22"]:
        rt = 2
    elif flags["F24"]:
        rt = 3
    elif flags["F25"]:
        rt = 4
    else:
        rt = 5
    return rt, flags


def compute_stage0(wb: Workbook, oxide_values: dict[str, float]) -> Stage0Result:
    """Полная стадия 0: записать вход, посчитать ф.е./F/A/коэффициенты/тип."""
    # вход в оба листа (как aut_1/aut_1a)
    for sheet in ["Нач+Type 3", "Нач+Type 12"]:
        wb.set_input(sheet, oxide_values)

    # коэффициенты вычисляются от F на листе Type 3
    k1, k2, k3, k4, achl, _flag = select_coefficients(wb)
    write_coefficients(wb, k1, k2, k3, k4, achl)

    f = float(wb.eval_cell(COEF_SHEET, "G2"))
    a = float(wb.eval_cell(COEF_SHEET, "I2"))
    fe = _fe_from_sheet(wb, COEF_SHEET)
    rock_type, flags = classify(wb)

    return Stage0Result(
        fe=fe, F=f, A=a,
        k1=k1, k2=k2, k3=k3, k4=k4, achl=achl,
        rock_type=rock_type, flags=flags,
    )
