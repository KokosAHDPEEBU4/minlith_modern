"""Стадия 0: подготовка расчёта (формульные единицы, F/A, коэффициенты, тип).

Точная формульная база оригинала MINLITH (лист «Нач+Type 3», колонки B-E),
но без пошаговых округлений:

  ф.е. оксида = (вес.% * 10000) / молярная_масса        (колонка D)
  F = D6 / (D6 + D7)                                     (FeO*/(FeO*+MgO))
  A = 2·D4 / (2·D4 + D6 + D7)                            (Al/(Al+Fe))

Коэффициенты хлорита k1..k4 и achl выбираются каскадом диапазонов по F
(и по A для полосы 0.69-0.87), повторяя VBA-каскад u_0..u_10 и флаги
J17/I17/J17/G18/I18 листа «Нач+Type 3».
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Массы молекул оксидов (г/моль) — колонка C листа «Нач+Type 3».
# TiO2 и C не переводятся в ф.е. (D3=B3, D13=B13).
_MOLAR_MASS = {
    "SiO2": 60.09, "Al2O3": 101.96, "FeO": 71.85, "MgO": 40.32,
    "CaO": 56.08, "Na2O": 61.982, "K2O": 94.2, "P2O5": 141.95,
    "MnO": 70.94, "SO3": 80.066, "F": 19.0, "Cl": 35.457,
    "S": 32.066, "CO2": 44.011, "SO": 80.066,
}

# Состав-«по умолчанию», сохранённый в ячейках B2:B19 листа «Нач+Type 3»
# дистрибутива. Отсутствующие во входе оксиды НЕ обнуляются, а берутся
# отсюда — так ведёт себя original (старые значения образца в файле).
DEFAULT_OXIDES: dict[str, float] = {
    "SiO2": 92.10165641968236, "TiO2": 0.1112402885146459,
    "Al2O3": 0.19177993841720542, "Fe2O3": 2.419104815264398,
    "FeO": 0.0, "MgO": 2.6277638778880794, "CaO": 1.8080043542825976,
    "Na2O": 0.10234212078200429, "K2O": 0.37766696442642117,
    "P2O5": 0.0027113323404357567, "MnO": 0.017365804330351443,
    "C": 0.0, "SO3": 0.0, "F": 0.0, "Cl": 0.0,
    "S": 0.2403640840715119, "CO2": 0.0, "SO": 0.0,
}


@dataclass
class Stage0:
    """Входные параметры расчёта, посчитанные без округлений."""

    fe: dict[str, float] = field(default_factory=dict)   # ф.е. оксидов (D2..D19)
    F: float = 0.0
    A: float = 0.0
    k1: float = 0.0
    k2: float = 0.0
    k3: float = 0.0
    k4: float = 0.0
    achl: float = 0.0
    rock_type: int = 5
    # важные производные величины (не входят в ф.е., но нужны далее):
    ca_raw: float = 0.0      # E6 — CaO ф.е. без вычета апатита (для дефекта)
    pr0: float = 0.0         # H20 — пирит = s/2
    fe3_1: float = 0.0       # I21 — лимонит/Fe после пирита = D6 − s/2
    ca: float = 0.0          # E10 — CaO для стадий типов (D8 при D8>0 иначе 0)
    ca_n_in: float = 0.0     # D8 — CaO остаток при отрицательном Ca (T-O2)
    s: float = 0.0           # D17 — S_ф.е. + SO3_ф.е.


def formula_units(ox: dict[str, float]) -> dict[str, float]:
    """Пересчёт вес.% -> формульные единицы (ф.е.), как в колонке D.

    Особенности оригинала сохраняются:
      * D3 = B3 (TiO2), D13 = B13 (C) — без пересчёта;
      * D5 (Fe2O3) на листе отсутствует -> ф.е. Fe2O3 = 0;
      * D6 = (0.9·Fe2O3 + FeO) — весь Fe пересчитан в FeO*;
      * D8 = CaO ф.е. − апатитовый Ca (3.33·P2O5);
      * D9 = Na2O ф.е. − (Cl/2);
      * D17 = S ф.е. + SO3 ф.е.
    """
    def fe_u(name: str) -> float:
        return ox.get(name, 0.0) * 10000.0 / _MOLAR_MASS[name]

    fe = {
        "SiO2": fe_u("SiO2"),
        "TiO2": ox.get("TiO2", 0.0),            # D3 = B3
        "Al2O3": fe_u("Al2O3"),
        "Fe2O3": 0.0,                           # на листе нет ячейки D5
        "FeO": (0.9 * ox.get("Fe2O3", 0.0) + ox.get("FeO", 0.0)) * 10000.0 / _MOLAR_MASS["FeO"],
        "MgO": fe_u("MgO"),
        "CaO": fe_u("CaO")
               - (3.33 * fe_u("P2O5")
                  + ox.get("F", 0.0) * 10000.0 / _MOLAR_MASS["F"] / 2.0),
        "Na2O": fe_u("Na2O") - ox.get("Cl", 0.0) * 10000.0 / _MOLAR_MASS["Cl"] / 2.0,
        "K2O": fe_u("K2O"),
        "P2O5": fe_u("P2O5"),
        "MnO": fe_u("MnO"),
        "C": ox.get("C", 0.0),                  # D13 = B13
        "SO3": ox.get("SO3", 0.0) * 10000.0 / _MOLAR_MASS["SO3"],
        "F": 0.0,                               # D15 — текстовая заглушка
        "Cl": ox.get("Cl", 0.0) * 10000.0 / _MOLAR_MASS["Cl"],
        "S": (ox.get("S", 0.0) * 10000.0 / _MOLAR_MASS["S"]) +
             (ox.get("SO3", 0.0) * 10000.0 / _MOLAR_MASS["SO3"]),
        "CO2": ox.get("CO2", 0.0) * 10000.0 / _MOLAR_MASS["CO2"],
        "SO": ox.get("SO", 0.0) * 10000.0 / _MOLAR_MASS["SO"],
    }
    return fe


def f_and_a(fe: dict[str, float]) -> tuple[float, float]:
    """F = FeO*/(FeO*+MgO); A = 2·Al/(2·Al + FeO* + MgO)."""
    d6 = fe["FeO"]
    d7 = fe["MgO"]
    d4 = fe["Al2O3"]
    f = d6 / (d6 + d7) if (d6 + d7) else 0.0
    a = (2.0 * d4) / (2.0 * d4 + d6 + d7) if (2.0 * d4 + d6 + d7) else 0.0
    return f, a


def coefficients(f: float, a: float) -> tuple[float, float, float, float, float]:
    """Коэффициенты хлорита k1..k4 и achl по диапазону F (и A).

    Полосы (каскад VBA u_0..u_10) и формулы ячеек-кандидатов:
      F 0.00-0.21   -> H5:H9: k1=4.42-5.18F;  k2=4.09F;  k3=(3.16-0.41F)/2;
      F 0.21-0.51   -> J5:J9: k1=3.93-2.96F;  k2=5.66F-0.34; k3=(3.66-2.69F)/2;
      F 0.51-0.69   -> L5:L9: k1=5.13-5.32F;  k2=2.54F+1.24; k3=(3.46F+0.53)/2;
      F 0.69-0.87 A>0.47  -> H12:H16: k1=0.56; k2=2.54F+1.24; k3=(3.46F+0.53)/2;
      F 0.69-0.87 0.40<A<0.47 -> J12:J16: k1=6.2-12A; k2, k3 как выше;
      F 0.87-1.00   -> L12:L16: k1=4-4F; k2=18.36F-12.36; k3=(25-25F)/2.

    Всегда k4 = 10 − k1 − k2 − 2·k3.  Константа achl:
      126.89·F + 551.81 (полоса H5), 126.89·F + 555.81 (J5/L5),
      126.89 + F + 555.81 (H12/J12), 561.42·F + 182.12 (L12).
    """
    if 0.0 < f < 0.21:
        k1, k2, k3, _ = (4.42 - 5.18 * f, 4.09 * f, (3.16 - 0.41 * f) / 2.0, None)
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 126.89 * f + 551.81
    elif 0.21 <= f < 0.51:
        k1, k2, k3, _ = (3.93 - 2.96 * f, 5.66 * f - 0.34, (3.66 - 2.69 * f) / 2.0, None)
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 126.89 * f + 555.81
    elif 0.51 <= f < 0.69:
        k1, k2, k3, _ = (5.13 - 5.32 * f, 2.54 * f + 1.24, (3.46 * f + 0.53) / 2.0, None)
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 126.89 * f + 555.81
    elif 0.69 <= f < 0.87 and a > 0.47:
        k1, k2, k3, _ = (0.56, 2.54 * f + 1.24, (3.46 * f + 0.53) / 2.0, None)
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 126.89 + f + 555.81
    elif 0.69 <= f < 0.87 and 0.40 < a < 0.47:
        k1 = 6.2 - 12.0 * a
        k2 = 2.54 * f + 1.24
        k3 = (3.46 * f + 0.53) / 2.0
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 126.89 + f + 555.81
    else:  # 0.87 <= f < 1.0
        k1, k2, k3, _ = (4 - 4 * f, 18.36 * f - 12.36, (25 - 25 * f) / 2.0, None)
        k4 = 10.0 - k1 - k2 - 2.0 * k3
        achl2 = 561.42 * f + 182.12
    return k1, k2, k3, k4, achl2


def classify(fe: dict[str, float], k1: float, k3: float) -> int:
    """Определить тип породы по условиям E20..E25 (чистые, без округлений).

    Тип 1: Al ≤ Na + K            (F20: Al−Na−K < 0)
    Тип 2: Al ≤ 1.2·Na + 3.25·K   (F22: Al−1.2Na−3.25K ≤ 0)
    Тип 3: Al ≤ 1.2Na+3.25K+(Mg−0.5K)·k3/k1
    Тип 4: Al ≤ 5Na+3.25K+(Mg−0.5K−2Na)·k3/k1
    Тип 5: прочее (больше всего Al).
    """
    al = fe["Al2O3"]
    na = fe["Na2O"]
    k = fe["K2O"]
    mg = fe["MgO"]
    e20 = al - na - k
    e21 = al - (1.2 * na + k)
    e22 = al - (1.2 * na + 3.25 * k)
    e24 = al - (1.2 * na + 3.25 * k + (mg - 0.5 * k) * k3 / k1)
    e25 = al - (5 * na + 3.25 * k + (mg - 0.5 * k - 2 * na) * k3 / k1)
    if e20 < 0 or e21 <= 0:
        return 1
    if e22 <= 0:
        return 2
    if e24 <= 0:
        return 3
    if e25 <= 0:
        return 4
    return 5


def compute_stage0(ox: dict[str, float]) -> Stage0:
    """Полная стадия 0 для входных весовых процентов оксидов."""
    fe = formula_units(ox)
    f, a = f_and_a(fe)
    k1, k2, k3, k4, achl = coefficients(f, a)
    rock_type = classify(fe, k1, k3)

    # s = D17 = S_ф.е. + SO3_ф.е. (сведено в fe["S"] внутри formula_units)
    s_total = fe["S"]
    pr0 = s_total / 2.0
    fe3_1 = fe["FeO"] - pr0
    d8 = fe["CaO"]
    d8_raw = ox.get("CaO", 0.0) * 10000.0 / _MOLAR_MASS["CaO"]
    ca = d8 if d8 > 0 else 0.0
    return Stage0(
        fe=fe, F=f, A=a,
        k1=k1, k2=k2, k3=k3, k4=k4, achl=achl,
        rock_type=rock_type,
        ca_raw=d8_raw,
        pr0=pr0,
        fe3_1=fe3_1,
        ca=ca,
        ca_n_in=d8,
        s=s_total,
    )
