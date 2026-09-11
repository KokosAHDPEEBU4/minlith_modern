"""Стадии типов 1-5: переход «ф.е. оксидов -> набор минералов и остатков».

Каждая функция повторяет логику VBA-процедур aType_1..aType_5 и их
ветвлений (t_49..t_83, C214-блок, C90..C264, тип 4/5 mm-путь и т.д.)
листа «Нач+Type 3»/«Нач+Type 12» — но в явном float64 без округлений.

Результат: не только «полезные» минералы (ab, an, or, ill, chl, gb, kn, mm),
но и остаточные количества ca_n, mg_n, fe_n, si_n, передаваемые на VI этап.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.clean_engine.stage0 import Stage0


@dataclass
class TypeSolution:
    """Результат стадии типа: минералы (ф.е.) и остатки для VI этапа."""

    ab: float = 0.0    # альбит
    an: float = 0.0    # анортит
    or_: float = 0.0    # ортоклаз
    ill: float = 0.0   # иллит
    chl: float = 0.0   # хлорит
    gb: float = 0.0    # гиббсит
    kn: float = 0.0    # каолинит
    mm: float = 0.0    # монтмориллонит

    ca_n: float = 0.0  # остаток CaO
    mg_n: float = 0.0  # остаток MgO
    fe_n: float = 0.0  # остаток FeO*
    si_n: float = 0.0  # остаток SiO2 (quartz)

    # подпись ветки для отладки
    trace: list[str] = field(default_factory=list)

    def mineral_vars(self) -> dict[str, float]:
        return {
            "ab": self.ab, "an": self.an, "or": self.or_,
            "ill": self.ill, "chl": self.chl, "gb": self.gb,
            "kn": self.kn, "mm": self.mm,
        }


def _base(d: dict[str, float]) -> tuple[float, float, float, float, float, float]:
    """Общие «имена» из ф.е.: si, al, mg, na, k, ca (E10)."""
    si = d["SiO2"]
    al = d["Al2O3"]
    mg = d["MgO"]
    na = d["Na2O"]
    k = d["K2O"]
    return si, al, mg, na, k


def solve_type(st0: Stage0) -> TypeSolution:
    """Диспетчер по rock_type из стадии 0."""
    t = st0.rock_type
    if t == 1:
        return type1(st0)
    if t == 2:
        return type2(st0)
    if t == 3:
        return type3(st0)
    return type45(st0)


# --------------------------------------------------------------------------
# Тип 1: Al <= Na + K   (t_49..t_83)
# --------------------------------------------------------------------------
def type1(st0: Stage0) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    fe3_1 = st0.fe3_1
    sol = TypeSolution(ab=na, or_=k)

    si_1 = si - 6.0 * na            # E45
    e46 = si_1 - 6.0 * k            # E46 = si после Ab и Or
    al1 = al - 2.0 * k              # E47 = Al после Or (D4 - k - k)

    d49 = al1 - ca <= 0
    if d49:
        c51 = e46 - 2.0 * al1       # Si для анортита
        if c51 >= 0:
            if al1 > 0:             # t_52t
                sol.an = al1
            else:                   # t_53an (anorthite по лимиту Na)
                sol.an = 0.2 * na
            sol.ca_n = ca - sol.an
            sol.si_n = e46 - 2.0 * sol.an
            sol.trace.append("t_52~53")
        else:                       # t_58: не хватает SiO2 на анортит
            sol.an = e46 / 2.0
            sol.gb = al1 - sol.an
            sol.ca_n = ca - sol.an
            sol.si_n = 0.0
            sol.trace.append("t_58")
    else:                           # al1 > ca
        if e46 - 2.0 * ca >= 0:     # t_67/68: Si для анортита по Ca
            sol.an = ca
            al_r = al1 - ca
            si_r = e46 - 2.0 * ca
            sol.ca_n = st0.ca_n_in - ca      # C71 = D8 - ca
            if al_r - si_r >= 0:             # t_73/74
                sol.kn = si_r / 2.0
                sol.gb = al_r - sol.kn
                sol.si_n = 0.0
            else:                            # t_78/79
                sol.kn = al_r
                sol.si_n = si_r - 2.0 * sol.kn
                sol.gb = 0.0
            sol.trace.append("t_67")
        else:                                # t_83 (БК-1)
            sol.an = e46 / 2.0
            sol.gb = al1 - sol.an
            sol.ca_n = ca - sol.an
            sol.si_n = 0.0
            sol.trace.append("t_83")

    sol.mg_n = mg
    sol.fe_n = fe3_1
    return sol


# --------------------------------------------------------------------------
# Тип 2: 1.2Na + 3.25K < Al  (granite_t2)
# --------------------------------------------------------------------------
def type2(st0: Stage0) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    fe3_1 = st0.fe3_1
    sol = TypeSolution(ab=na)

    si_1 = si - 6.0 * na            # C175

    if ca - 0.2 * na >= 0:          # D192: Ca хватает на анортит
        sol.an = 0.2 * na
        si_2 = si_1 - 2.0 * sol.an          # C194
        al_1 = al - na - sol.an             # C195
        sol.ca_n = ca - sol.an              # C196
        sol.trace.append("C192+")
    else:                           # D198: ca < 0.2na — анортит по Ca
        sol.an = ca
        si_2 = si_1 - 2.0 * sol.an          # C200
        al_1 = al - na - sol.an             # C201
        sol.ca_n = 0.0                      # C202
        sol.trace.append("C192-")

    # иллит + ортоклаз (D204: Si достаточно)
    if si_2 - (11.5 * k + 2.0 * al_1) / 2.25 >= 0:
        sol.ill = (al_1 - k) / 4.5
        sol.or_ = k - 2.0 * sol.ill
        sol.fe_n = fe3_1 - sol.ill
        sol.mg_n = mg - sol.ill
        sol.si_n = si_2 - 16.0 * sol.ill - 6.0 * sol.or_
        sol.trace.append("ill+or")
    else:
        raise NotImplementedError(
            "Тип 2: ветка недостатка SiO2 (D204<0) не реализована в clean_engine."
        )

    sol.ca_n = ca - sol.an
    return sol


# --------------------------------------------------------------------------
# Тип 3: среднее Al (basalt_t3, T-O2)
# --------------------------------------------------------------------------
def type3(st0: Stage0) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    k1, k2, k3, k4 = st0.k1, st0.k2, st0.k3, st0.k4
    fe3_1 = st0.fe3_1
    d8 = st0.ca_n_in
    sol = TypeSolution(ab=na)

    si3_1 = si - 6.0 * na               # C47
    al3_1 = al - na                     # C48

    c60 = ca - 0.2 * na
    c61 = si3_1 - 6.0 * k - 0.4 * na
    c68 = si3_1 - 6.0 * k - 2.0 * ca
    if c60 >= 0 and c61 >= 0:           # D61: анортит по Na, Si хватает
        sol.an = 0.2 * na
        si3_2 = si3_1 - 2.0 * sol.an    # C63
        al3_2 = al3_1 - sol.an          # C64
        sol.trace.append("D61")
    elif c60 < 0 and c68 >= 0:          # D68: анортит по Ca (T-O2: ca=0)
        sol.an = ca
        si3_2 = si3_1 - 2.0 * sol.an    # C70
        al3_2 = al3_1 - sol.an          # C71
        sol.trace.append("D68")
    else:
        raise NotImplementedError(
            "Тип 3: редкие ветки плагиоклаза (D51/D53) не реализованы."
        )

    # остаток Ca: при отрицательном D8 берём сам D8 (кислый случай T-O2)
    sol.ca_n = d8 if d8 <= 0 else ca - sol.an

    # ---- иллит/хлорит ----
    c90 = 4.5 * mg - al3_2 + k          # C90
    c95 = (k + 4.5 * mg - al3_2) / (4.5 * k1 - k3)   # C95 (chl по Mg)
    c97 = mg - k1 * c95                 # C97 -> Ill по Mg
    f93 = (k / 2.0 - c97) >= 0

    if c90 >= 0 and c97 > 0:            # D97: Mg-хлоритовый путь (T-O2)
        sol.or_ = k - 2.0 * c97          # C98 — фиксируется сразу
        c100 = fe3_1 - c97 - k2 * c95   # C100
        c101 = si3_2 - 16.0 * c97 - k4 * c95 - 6.0 * sol.or_   # C101
        if c100 >= 0 and c101 >= 0:     # D106: всё сошлось
            sol.ill = c97
            sol.chl = c95
            si3_3 = c101
            al3_3 = al3_2 - 6.5 * sol.ill - k3 * sol.chl
            sol.trace.append("D106")
        elif c100 < 0:                  # D109: Fe-доминантный путь (T-O2)
            sol.trace.append("D109-fe")
            _type3_fe_path(sol, si3_2, al3_2, mg, k, k1, k2, k3, k4,
                           fe3_1, or_kept=sol.or_)
            return sol
        else:                           # D112: дефицит SiO2
            raise NotImplementedError("Тип 3: ветка D112 не реализована.")
        _type3_balance(sol, si3_3, al3_3)
        return sol

    if c90 >= 0 and f93:                # F93>=0, но C97<=0 (basalt)
        ill_3 = k / 2.0                 # C116
        sol.ill = ill_3
        e119 = mg - 0.5 * k - (k1 / k3) * (al3_2 - 3.25 * k)
        if e119 >= 0:                   # F119: хлорит по Al (basalt)
            sol.chl = (al3_2 - 6.5 * ill_3) / k3          # C120
            sol.mg_n = mg - ill_3 - k1 * sol.chl          # C121
            sol.fe_n = fe3_1 - ill_3 - k2 * sol.chl       # C122
            si3_3 = si3_2 - 16.0 * ill_3 - k4 * sol.chl   # C123
            al3_3 = 0.0
            sol.trace.append("F119+")
        else:                           # F126: хлорит по Mg
            sol.chl = (mg - ill_3) / k1
            sol.mg_n = 0.0
            sol.fe_n = fe3_1 - ill_3 - k2 * sol.chl
            si3_3 = si3_2 - 16.0 * ill_3 - k4 * sol.chl
            al3_3 = al3_2 - 6.5 * ill_3 - k3 * sol.chl
            sol.trace.append("F126-")
        _type3_balance(sol, si3_3, al3_3)
        return sol

    raise NotImplementedError("Тип 3: ветка F93<0 не реализована.")


def _type3_fe_path(sol: TypeSolution, si3_2: float, al3_2: float,
                   mg: float, k: float, k1: float, k2: float, k3: float,
                   k4: float, fe3_1: float, or_kept: float) -> None:
    """Fe-путь типа 3 (T-O2): ill = k/2, хлорит из Fe, Д244/D245/..."""
    c215 = k / 2.0                        # C215 = ill
    ill = c215
    fe3_2 = fe3_1 - ill                   # C216
    mg_1 = mg - ill                       # C217
    al3_3 = al3_2 - 6.5 * ill             # C218
    si3_3 = si3_2 - 16.0 * ill            # C219
    k4x = k4

    # составы хлорита по избытку катионов (C233..C249)
    c233 = al3_3 / k3 - si3_3 / k4x
    c234 = al3_3 / k3 - fe3_2 / k2
    c235 = al3_3 / k3 - mg_1 / k1
    d235 = c233 < 0 and c234 <= 0 and c235 <= 0
    d236 = c233 < 0 and c234 >= 0 and c235 >= 0
    d237 = c233 < 0 and c234 <= 0 and c235 >= 0
    if d235 or d236 or d237:
        # хлорит по Mg: chl = mg_1/k1
        chl = mg_1 / k1
        sol.ill = ill
        sol.chl = chl
        sol.mg_n = 0.0
        sol.fe_n = fe3_2 - k2 * chl
        si3_3b = si3_3 - k4x * chl
        al3_3b = al3_3 - k3 * chl
        sol.or_ = or_kept
        _type3_balance(sol, si3_3b, al3_3b)
        return

    c243 = fe3_2 / k2 - si3_3 / k4x
    c244 = fe3_2 / k2 - mg_1 / k1
    c245 = fe3_2 / k2 - al3_3 / k3
    if c243 < 0 and c244 < 0 and c245 < 0:        # D245: хлорит по Fe (T-O2)
        chl = fe3_2 / k2                          # C246
        sol.ill = ill
        sol.chl = chl
        sol.mg_n = mg_1 - k1 * chl                # C247
        si3_4 = si3_3 - k1 * chl                  # C248 (k1! квирк оригинала)
        al3_4 = al3_3 - k4x * chl                 # C249 (k4! квирк оригинала)
        sol.fe_n = 0.0
        sol.or_ = or_kept
        _type3_balance(sol, si3_4, al3_4)
        return
    raise NotImplementedError("Тип 3: хлорит по D245 не сошёлся (D235..245).")


def _type3_balance(sol: TypeSolution, si_rest: float, al_rest: float) -> None:
    """Баланс остатков Al/Si типа 3: каолинит или си_3 (rows 81-88, 257-264)."""
    if 2.0 * al_rest - si_rest >= 0:
        sol.kn = si_rest / 2.0
        sol.gb = al_rest - sol.kn
        sol.si_n = 0.0
    else:
        sol.kn = al_rest
        sol.si_n = si_rest - 2.0 * al_rest
        sol.gb = 0.0


# --------------------------------------------------------------------------
# Типы 4-5 (алюминиевые): обычный путь (кварцит) и mm-путь (highal)
# --------------------------------------------------------------------------
def type45(st0: Stage0) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    k1, k2, k3, k4 = st0.k1, st0.k2, st0.k3, st0.k4
    fe3_1 = st0.fe3_1

    ill_4 = k / 2.0
    si4_1 = si - 16.0 * ill_4          # Si после иллита
    al4_1 = al - 6.5 * ill_4           # Al после иллита
    fe4_2 = fe3_1 - ill_4
    mg4_1 = mg - ill_4

    sol = TypeSolution(ill=ill_4)

    # --- обычный путь: хлорит+монтмориллонит (D433/D437, кварцит) ---
    c432 = mg4_1 - k1 * (1.9 * mg4_1 + 1.2 * na - al4_1) / (1.9 * k1 - k3)
    if c432 >= 0 and 2.0 * na - c432 >= 0:      # D433
        chl_4 = (1.9 * mg4_1 + 1.2 * na - al4_1) / (1.9 * k1 - k3)   # C435
        if chl_4 - al4_1 / k3 < 0:              # D437
            mm_4 = (mg4_1 - k1 * chl_4) / 2.0
            ab_4 = na - mm_4
            an_4 = 0.2 * ab_4
            sol.chl = chl_4
            sol.mm = mm_4
            sol.ab = ab_4
            sol.an = an_4
            sol.fe_n = fe4_2 - k2 * chl_4
            sol.si_n = (si4_1 - k4 * chl_4 - 24.0 * mm_4
                        - 6.0 * ab_4 - 2.0 * an_4)
            sol.mg_n = 0.0
            sol.ca_n = ca - an_4
            sol.trace.append("type45-normal")
            return sol
        raise NotImplementedError("Тип 4/5: ветка D437>=0 не реализована.")

    # --- mm-путь высокоглинозёмистой (D331+D334, highal) ---
    # mg0 здесь = D7 − ill_4 (то есть Mg после K-слюды), как на листе.
    mg0_after_ill = mg - ill_4
    if mg0_after_ill - 2.0 * na < 0 and si4_1 - 6.4 * na > 0 and si4_1 - 24.0 * na <= 0:
        mm_4 = (si4_1 - 6.4 * na) / 17.6                 # C335
        ab_4 = na - mm_4                                 # C336
        an_4 = 0.2 * ab_4                                # C337
        sol.ab = ab_4
        sol.an = an_4
        sol.mm = mm_4
        sol.ca_n = ca - an_4                             # C338
        sol.mg_n = mg0_after_ill - 2.0 * mm_4            # C340
        # C276 = si - 6k на листе; C341 = C276 - 1.2*ab - 5*mm
        sol.gb = (si - 6.0 * k) - 1.2 * ab_4 - 5.0 * mm_4   # C341
        sol.fe_n = fe3_1                     # Fe остаётся целиком (см. trace)
        sol.si_n = 0.0
        sol.trace.append("mm-path (D334)")
        return sol

    raise NotImplementedError(
        "Тип 4/5: ни обычный путь (D433), ни mm-путь (D334) не сошлись; "
        "другие ветки типов 4/5 не реализованы."
    )
