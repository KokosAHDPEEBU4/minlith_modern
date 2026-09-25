"""Стадии типов 1-5: переход «ф.е. оксидов -> набор минералов и остатков».

Каждая функция повторяет логику VBA-процедур aType_1..aType_5 и их
ветвлений (t_49..t_83, C214-блок, C90..C264, тип 4/5 mm-путь и т.д.)
листа «Нач+Type 3»/«Нач+Type 12» — но в явном float64 без округлений.

Результат: не только «полезные» минералы (ab, an, or, ill, chl, gb, kn, mm),
но и остаточные количества ca_n, mg_n, fe_n, si_n, передаваемые на VI этап.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.excel_parity.stage0 import Stage0


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
    ov = getattr(st0, "overrides", None)
    if t == 1:
        return type1(st0, overrides=ov)
    if t == 2:
        return type2(st0, overrides=ov)
    if t == 3:
        return type3(st0, overrides=ov)
    return type45(st0, overrides=ov)


# --------------------------------------------------------------------------
# Тип 1: Al <= Na + K   (t_49..t_83)
# --------------------------------------------------------------------------
def type1(st0: Stage0, overrides=None) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    fe3_1 = st0.fe3_1
    sol = TypeSolution(ab=na, or_=k)

    si_1 = si - 6.0 * na            # E45
    e46 = si_1 - 6.0 * k            # E46 = si после Ab и Or
    al1 = al - 2.0 * k              # E47 = Al после Or (D4 - k - k)

    forced_t49 = overrides.get("type1.t_49") if overrides else None
    d49 = al1 - ca <= 0
    if forced_t49 in ("t_52~53", "t_58"):
        d49 = True
    elif forced_t49 in ("t_67", "t_83"):
        d49 = False
    if d49:
        c51 = e46 - 2.0 * al1       # Si для анортита
        c51_ok = c51 >= 0
        if forced_t49 == "t_58":
            c51_ok = False
        elif forced_t49 == "t_52~53":
            c51_ok = True
        if c51_ok:
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
        e46_ok = e46 - 2.0 * ca >= 0
        if forced_t49 == "t_83":
            e46_ok = False
        elif forced_t49 == "t_67":
            e46_ok = True
        if e46_ok:                  # t_67/68: Si для анортита по Ca
            sol.an = ca
            al_r = al1 - ca
            si_r = e46 - 2.0 * ca
            sol.ca_n = st0.ca_n_in - ca      # C71 = D8 - ca
            if al_r - si_r >= 0:             # t_73/74
                # t_74t ставит только kn/gb; si_n остаётся = C70 = si_r
                # (записан ранее в t_68t), НЕ обнуляется.
                sol.kn = si_r / 2.0
                sol.gb = al_r - sol.kn
                sol.si_n = si_r
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
def type2(st0: Stage0, overrides=None) -> TypeSolution:
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    ca_fe = st0.ca_n_in                  # D8 — сырой CaO ф.е. (может быть <0)
    fe3_1 = st0.fe3_1
    sol = TypeSolution(ab=na)

    si_1 = si - 6.0 * na                # C175

    # ---- s_177/s_179 → s_180: илито-кварцевый коридор (or=k, an из кремнезёма) ----
    if si_1 - 6.0 * k - 0.4 * na < 0:            # d177 → s_179
        if ca - (si_1 - 6.0 * k) / 2.0 >= 0:     # d179 → s_180
            or_k = k                             # C180
            si_2k = si_1 - 6.0 * k               # C181
            an_k = si_2k / 2.0                   # C182
            al_1k = al - k - na                  # C183
            sol.or_ = or_k
            sol.si_n = 0.0                       # C185
            sol.an = an_k
            sol.ca_n = ca - an_k                 # C186
            sol.gb = al_1k - an_k                # C184
            sol.fe_n = fe3_1                     # = fe_1 (I21)
            sol.mg_n = mg                        # mg_n ← D7
            sol.trace.append("ill-kz (D177-D179)")
            return sol
    # иначе s_188(d188)/s_190 → s_192: анортит

    # ---- анортит: s_192 / s_197 (s_198 / s_198an) ----
    if ca >= 0.2 * na:                  # D192: Ca хватает на анортит
        sol.an = 0.2 * na
        si_2 = si_1 - 2.0 * sol.an      # C194
        al_1 = al - na - sol.an         # C195
        sol.ca_n = ca - sol.an          # C196
        sol.trace.append("an=0.2na")
    elif ca > 0:                        # D199: анортит по Ca (s_198)
        sol.an = ca
        si_2 = si_1 - 2.0 * sol.an      # C200
        al_1 = al - na - sol.an         # C201
        sol.ca_n = 0.0                  # C202
        sol.trace.append("an=ca")
    else:                               # ca <= 0: анортит по Na (s_198an)
        sol.an = 0.2 * na
        si_2 = si_1 - 2.0 * sol.an      # I200
        al_1 = al - na - sol.an         # I201
        sol.ca_n = 0.0                  # I202
        sol.trace.append("an=0.2na(I)")

    if si_2 - (11.5 * k + 2.0 * al_1) / 2.25 >= 0:   # s_204 -> s_208
        if 0.2 * na - ca - 3.25 * k < 0:             # d208 -> s_213
            ill_a = (al_1 - k) / 4.5                 # C214
            if fe3_1 - ill_a > 0 and mg - ill_a > 0:  # d213 -> s_213t
                sol.ill = ill_a
                sol.or_ = k - 2.0 * sol.ill
                sol.fe_n = fe3_1 - sol.ill
                sol.mg_n = mg - sol.ill
                sol.si_n = si_2 - 16.0 * sol.ill - 6.0 * sol.or_   # C218
                sol.trace.append("ill+or")
            else:                        # d213 FALSE -> s_221 (Fe-иллит)
                _type2_fe_illite(sol, si_2, al_1, mg, k, fe3_1, overrides)
        else:                            # d208 FALSE -> s_251 (бедный Ca)
            _type2_ca_poor(sol, si_2, al_1, mg, k, fe3_1, ca_fe, overrides)
    else:                                # s_204 else -> s_271 -> s_274
        ill_c = (si_2 - 6.0 * k) / 4.0   # C275
        if fe3_1 - ill_c > 0 and ca_fe - ill_c > 0:   # d274 -> s_274t
            sol.ill = ill_c
            sol.or_ = k - 2.0 * sol.ill
            sol.gb = al_1 - 6.5 * sol.ill - sol.or_    # C277
            sol.fe_n = fe3_1 - sol.ill
            sol.mg_n = mg - sol.ill
            sol.si_n = 0.0                              # C280
            sol.trace.append("ill-gb (D274)")
        else:                            # s_274 else -> s_221 (Fe-иллит)
            _type2_fe_illite(sol, si_2, al_1, mg, k, fe3_1, overrides)
    return sol


def _type2_fe_illite(sol: TypeSolution, si_2: float, al_1: float,
                     mg: float, k: float, fe3_1: float,
                     overrides=None) -> None:
    """s_221: иллит лимитирован Fe (s_221t) или Mg (s_230); дальше kn/gb."""
    forced_fe = overrides.get("type2.fe_ill") if overrides else None
    if forced_fe == "fe-ill":
        fe_ok = True
    elif forced_fe == "fe-ill-mg":
        fe_ok = False
    else:
        fe_ok = mg - fe3_1 >= 0
    if fe_ok:                        # s_221t: Ill по Fe
        ill = fe3_1                  # C222
        sol.fe_n = fe3_1 - ill       # C224 = 0
        sol.mg_n = mg - ill          # C225
    else:                            # s_230: Ill по Mg
        ill = mg                     # C230
        sol.fe_n = fe3_1 - ill       # C232
        sol.mg_n = mg - ill          # C233 = 0
    sol.ill = ill
    sol.or_ = k - 2.0 * ill          # C223/C231
    si3_2 = si_2 - 16.0 * ill - 6.0 * sol.or_   # C226/C234
    al_2 = al_1 - 6.5 * ill - sol.or_           # C227/C235
    sol.trace.append("fe-ill" if fe_ok else "fe-ill-mg")
    if si3_2 - 2.0 * al_2 >= 0:      # s_238 -> s_238t
        sol.kn = al_2                # C239
        sol.si_n = si3_2 - 2.0 * sol.kn         # C240
        sol.gb = 0.0
        sol.trace.append("fe-ill kn")
    else:                            # s_243
        sol.kn = si3_2 / 2.0         # C244
        sol.gb = al_2 - sol.kn       # C245
        sol.si_n = 0.0               # C246
        sol.trace.append("fe-ill gb")


def _type2_ca_poor(sol: TypeSolution, si_2: float, al_1: float,
                   mg: float, k: float, fe3_1: float, ca_fe: float,
                   overrides=None) -> None:
    """s_251: бедный Ca (Na доминирует) — либо ill=k/2, либо s_274."""
    d251 = (mg - 0.5 * k > 0) and (fe3_1 - 0.5 * k >= 0)
    if d251:                           # s_251t
        ill = k / 2.0                  # C252
        sol.ill = ill
        si3_2 = si_2 - 16.0 * ill      # C253
        sol.fe_n = fe3_1 - ill         # C254
        al_2 = al_1 - 6.5 * ill        # C255
        sol.mg_n = mg - ill            # C256
        sol.or_ = 0.0                  # E255 (константа листа)
        if si3_2 - 2.0 * al_2 >= 0:    # s_258 -> s_258t
            sol.kn = al_2              # C259
            sol.si_n = si3_2 - 2.0 * sol.kn    # C260
            sol.gb = 0.0
            sol.trace.append("ill=k/2 kn")
        else:                          # s_263
            sol.kn = si3_2 / 2.0       # C264
            sol.gb = al_2 - sol.kn     # C265
            sol.si_n = 0.0             # C266
            sol.trace.append("ill=k/2 gb")
    else:                              # s_274 (тот же путь, что D204<0)
        ill_c = (si_2 - 6.0 * k) / 4.0  # C275
        if fe3_1 - ill_c > 0 and ca_fe - ill_c > 0:   # d274 -> s_274t
            sol.ill = ill_c
            sol.or_ = k - 2.0 * sol.ill
            sol.gb = al_1 - 6.5 * sol.ill - sol.or_
            sol.fe_n = fe3_1 - sol.ill
            sol.mg_n = mg - sol.ill
            sol.si_n = 0.0
            sol.trace.append("ill-gb (D274b)")
        else:
            _type2_fe_illite(sol, si_2, al_1, mg, k, fe3_1, overrides)


# --------------------------------------------------------------------------
# Тип 3: среднее Al (basalt_t3, T-O2)
# --------------------------------------------------------------------------
# Общие хвосты типов 3/4/5
# --------------------------------------------------------------------------
def _t3_balance(sol: TypeSolution, si_rest: float, al_rest: float) -> None:
    """Баланс остатков Al/Si (p_81 rows 81-88 и p_257 rows 257-264)."""
    if 2.0 * al_rest - si_rest >= 0:
        sol.kn = si_rest / 2.0
        sol.gb = al_rest - sol.kn
        sol.si_n = 0.0
    else:
        sol.kn = al_rest
        sol.si_n = si_rest - 2.0 * al_rest
        sol.gb = 0.0


def _t5(sol: TypeSolution, ca_in: float, mg_1: float, fe3_2: float,
        al3_3: float, si3_3: float, k1: float, k2: float, k3: float,
        k4: float, or_p: float) -> None:
    """p_227/p_236/p_236t/p_246t/p_257: хлорит из остатков Si/Mg/Fe/Al."""
    c224 = si3_3 / k4 - mg_1 / k1
    c225 = si3_3 / k4 - fe3_2 / k2
    c226 = si3_3 / k4 - al3_3 / k3
    if c224 < 0 and c225 <= 0 and c226 <= 0:     # D226 → p_227t (chl по Si)
        chl = si3_3 / k4                         # C227
        sol.chl = chl
        sol.mg_n = mg_1 - k1 * chl               # C228
        sol.fe_n = fe3_2 - k2 * chl              # C229
        sol.gb = al3_3 - k3 * chl                # C230
        sol.si_n = 0.0                            # C231 (статичный 0)
        sol.ca_n = ca_in                          # D8
        sol.or_ = or_p
        return
    c233 = al3_3 / k3 - si3_3 / k4
    c234 = al3_3 / k3 - fe3_2 / k2
    c235 = al3_3 / k3 - mg_1 / k1
    if c233 < 0 and c234 <= 0 and c235 <= 0:     # D235 → p_236t (chl по Mg)
        chl = mg_1 / k1                          # C236
        sol.chl = chl
        sol.fe_n = fe3_2 - k2 * chl              # C237
        si3_4 = si3_3 - k4 * chl                 # C238
        al3_4 = al3_3 - k3 * chl                 # C239
        # C240=0 → mg_n: в оригинале вставка не достигает B94
        # (Select B94 разрешается на активном листе Type 3) → mg_n не трогаем
    elif (c233 < 0 and c234 >= 0 and c235 >= 0   # D236 → p_236t
          or c233 < 0 and c234 <= 0 and c235 >= 0):   # D237 → p_236t
        chl = mg_1 / k1
        sol.chl = chl
        sol.fe_n = fe3_2 - k2 * chl
        si3_4 = si3_3 - k4 * chl
        al3_4 = al3_3 - k3 * chl
    else:                                        # p_246t (chl по Fe)
        chl = fe3_2 / k2                         # C246
        sol.chl = chl
        sol.mg_n = mg_1 - k1 * chl               # C247
        si3_4 = si3_3 - k1 * chl                 # C248 (k1! квирк оригинала)
        al3_4 = al3_3 - k4 * chl                 # C249 (k4! квирк оригинала)
        sol.fe_n = 0.0                           # C250
    sol.ca_n = ca_in                              # D8
    sol.or_ = or_p
    _t3_balance(sol, si3_4, al3_4)                # p_257
    sol.trace.append("t5")


def _t3_after_p253(sol: TypeSolution, si3_2: float, al3_2: float, k: float,
                   ca_in: float, mg_1: float, fe3_2: float,
                   k1: float, k2: float, k3: float, k4: float) -> None:
    """p_253: or=k, al3_3=al3_2-k, si3_3=si3_2-6k, затем p_227."""
    or_ = k                                     # C252
    al3_3 = al3_2 - k                           # C253
    si3_3 = si3_2 - 6.0 * k                     # C254
    sol.or_ = or_
    sol.si_n = si3_3
    _t5(sol, ca_in, mg_1, fe3_2, al3_3, si3_3, k1, k2, k3, k4, or_)
    sol.trace.append("p253->t5")


def _t3_after_ill(sol: TypeSolution, ca_in: float, si3_2: float, al3_2: float,
                  k: float, mg_1: float, fe3_2: float, al3_3: float,
                  si3_3: float,
                  k1: float, k2: float, k3: float, k4: float) -> None:
    """p_196/p_199 после 3332: si3_3<0 → p_253 (p_222-путь), иначе p_81."""
    if si3_3 < 0:
        _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, fe3_2,
                       k1, k2, k3, k4)
        return
    _t3_balance(sol, si3_3, al3_3)


def _t3_fe_path(sol: TypeSolution, si3_2: float, al3_2: float,
                mg: float, k: float, k1: float, k2: float, k3: float,
                k4: float, fe3_1: float, ill3: float, or_in: float,
                ca_in: float, si3_3_in: float | None = None,
                al3_3_in: float | None = None,
                skip_fe_lookup: bool = False, overrides=None) -> None:
    """Fe-путь типа 3: p_159 → (3331 | 3332a/b | 3333a/b) + tail.

    ``skip_fe_lookup=True`` — вызывающий (type45 m_418t) в Excel вызывает
    ``p_201`` напрямую, минуя p_159/p_163/p_176/p_181/p_189 (ветка d159-false).
    """
    c158 = 4.5 * fe3_1 - al3_2 + k             # C158
    c159 = 4.5 * k1 - k2                       # C159
    if not skip_fe_lookup and c158 >= 0 and c159 > 0:    # d159 → p_163
        c162 = (k / 2.0
                - (fe3_1 - k2 * (k + 4.5 * fe3_1 - al3_2) / (4.5 * k2 - k3)))
        if c162 > 0:                           # d162 → p_163t (3331)
            chl = (k + 4.5 * fe3_1 - al3_2) / (4.5 * k2 - k3)   # C163
            ill = fe3_1 - k2 * chl                             # C164
            or_ = k - 2.0 * ill                                # C165
            mg_1 = mg - ill - k1 * chl                        # C167
            si3_3 = si3_2 - 16.0 * ill - k4 * chl - 6.0 * or_  # C168
            sol.ill, sol.chl, sol.or_ = ill, chl, or_
            sol.mg_n = mg_1
            sol.si_n = si3_3
            sol.trace.append("3331")
            if si3_3 >= 0:                     # p_171 (d170) → rVI
                sol.fe_n = 0.0                 # C166
                return
            sol.fe_n = 0.0                     # C166
            _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, 0.0,
                           k1, k2, k3, k4)
            return
        if c162 < 0:                           # p_176t: ill = k/2
            ill3 = k / 2.0
            sol.ill = ill3
        # p_181/p_189
        c180 = fe3_1 - k / 2.0 - (k1 / k2) * (al3_2 - 3.25 * k)   # C180
        if c180 > 0:                           # p_181t (3332a: chl по Al)
            chl = (al3_2 - 6.5 * ill3) / k3                     # C181
            fe3_2 = fe3_1 - ill3 - k2 * chl                     # C182
            mg_1 = mg - ill3 - k1 * chl                         # C183
            si3_3 = si3_2 - 16.0 * ill3 - k4 * chl              # C184
            al3_3 = 0.0                        # E183 (Al→хлорит целиком)
            sol.chl = chl
            sol.fe_n = fe3_2
            sol.mg_n = mg_1
            sol.si_n = si3_3
            sol.or_ = 0.0                      # E182 = 0
            sol.trace.append("3332a")
            _t3_after_ill(sol, ca_in, si3_2, al3_2, k, mg_1, fe3_2, al3_3,
                          si3_3, k1, k2, k3, k4)
            return
        c188 = fe3_1 - k / 2.0 - (k1 / k3) * (al3_2 - 3.25 * k)   # C188
        if c188 < 0:                           # p_189t (3332b: chl по Fe)
            chl = (fe3_1 - ill3) / k2                              # C189
            fe3_2 = 0.0                        # C190
            mg_1 = mg - ill3 - k1 * chl                           # C191
            si3_3 = si3_2 - 16.0 * ill3 - k4 * chl                # C192
            al3_3 = al3_2 - 6.5 * ill3 - k2 * chl                 # C193
            sol.chl = chl
            sol.fe_n = 0.0
            sol.mg_n = mg_1
            sol.si_n = si3_3
            sol.trace.append("3332b")
            _t3_after_ill(sol, ca_in, si3_2, al3_2, k, mg_1, fe3_2, al3_3,
                          si3_3, k1, k2, k3, k4)
            return
        # p_196 (else p_181/p_189): используются ВХОДЯЩИЕ si3_3/al3_3
        # (на листе это ячейки C195/C198 и ранее записанные имена).
        if si3_3_in is None or al3_3_in is None:
            # Из type45 m_418t Excel вызывает p_201 напрямую (не p_196) —
            # этот композитный путь кода ещё не портирован.
            raise NotImplementedError(
                "Тип 3: p_196 из type45 (m_418t) — не портирован.")
        if si3_3_in < 0.0:                     # d195 → p_253
            _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, fe3_2,
                           k1, k2, k3, k4)
            return
        _t3_balance(sol, si3_3_in, al3_3_in)   # d198 → p_81
        sol.trace.append("p196->p81")
        return
    # p_201
    c200 = 4.5 * fe3_1 - al3_2 + k             # C200
    forced_d200 = overrides.get("type3.d200") if overrides else None
    if forced_d200 == "3333a":
        c200_neg = True
    elif forced_d200 == "3333b":
        c200_neg = False
    else:
        c200_neg = c200 < 0
    if c200_neg:                               # p_201t (3333a: ill = fe3_1)
        ill = fe3_1                            # C201
        or_ = k - 2.0 * ill                     # C202
        mg_1 = mg - ill                         # C204
        si3_3 = si3_2 - 16.0 * ill - 6.0 * or_  # C205
        al3_3 = al3_2 - or_ - 6.5 * ill        # C206
        sol.ill, sol.or_ = ill, or_
        sol.fe_n = 0.0                          # C203
        sol.mg_n = mg_1
        sol.si_n = si3_3
        sol.trace.append("3333a")
        if si3_3 < 0:                          # p_209 (d208) → p_253
            _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, 0.0,
                           k1, k2, k3, k4)
            return
        _t3_balance(sol, si3_3, al3_3)
        return
    # p_215 → p_215t (3333b: ill = k/2)
    ill = k / 2.0                               # C215
    fe3_2 = fe3_1 - ill                         # C216
    mg_1 = mg - ill                             # C217
    al3_3 = al3_2 - 6.5 * ill                   # C218
    si3_3 = si3_2 - 16.0 * ill                  # C219
    sol.ill = ill
    sol.fe_n = fe3_2
    sol.mg_n = mg_1
    sol.si_n = si3_3
    sol.trace.append("3333b")
    if si3_3 < 0:                              # p_222 (d221) → s_271
        if k2 == 0:                            # s_274 → s_274t (k2=0, редко)
            raise NotImplementedError(
                "Тип 3: p_222 → s_271 → s_274t (k2=0).")
        # s_274 → s_221 → s_221t (d221=si3_3<0)
        sol.ill = 0.0                          # C222 (пусто)
        sol.or_ = 0.0                          # C223 (пусто)
        sol.fe_n = si3_3 / k4 - mg_1 / k1      # C224
        sol.mg_n = si3_3 / k4 - fe3_2 / k2     # C225
        # s_238: d238 не определён → s_243
        sol.kn = fe3_2 / k2 - mg_1 / k1        # C244
        sol.gb = fe3_2 / k2 - al3_3 / k3       # C245
        sol.si_n = fe3_2 / k2                  # C246
        sol.trace.append("s_271")
        return sol
    # Excel: p_222 (d221-false) → p_227; or сохраняется (не пишется в p_215)
    _t5(sol, ca_in, mg_1, fe3_2, al3_3, si3_3, k1, k2, k3, k4, sol.or_)
    sol.trace.append("p222->t5")


# --------------------------------------------------------------------------
def type3(st0: Stage0, al3_3_in: float | None = None,
          overrides=None) -> TypeSolution:
    """Полный порт «Нач+Type 3»: плагиоклаз + p_90/p_93/p_97/p_114 + p_142 +
    Fe-путь (p_159/p_163/p_163t/3331/3332/3333) + хвосты p_227/p_236/p_246/p_257."""
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    ca_in = st0.ca_n_in
    k1, k2, k3, k4 = st0.k1, st0.k2, st0.k3, st0.k4
    fe3_1 = st0.fe3_1
    sol = TypeSolution(ab=na)

    # ---- плагиоклазовая зона (rows 46-72) ----
    si3_1 = si - 6.0 * na                      # C47
    al3_1 = al - na                            # C48
    c50 = ca - 0.2 * na
    c51 = si3_1 - 6.0 * k - 0.4 * na           # C51
    c52 = ca - 0.2 * na                        # C52 (повтор C50)
    c53 = si3_1 - 6.0 * k - 2.0 * ca           # C53
    c60 = ca - 0.2 * na                        # C60
    c61 = si3_1 - 6.0 * k - 0.4 * na           # C61
    if c50 >= 0 and c51 < 0 and c52 < 0 and c53 < 0:
        # p_53 → p_53t → rVI (редкая плагиоклазовая ветка D51&D53)
        an_p = (si3_1 - 6.0 * k) / 2.0         # C55
        sol.or_ = k                            # C54
        sol.an = an_p
        sol.si_n = 0.0                         # C56 (статичный 0)
        sol.ca_n = ca - an_p                   # C57
        sol.gb = al3_1 - k - an_p              # C58
        sol.fe_n = fe3_1                       # fe_n ← fe3_1
        sol.mg_n = mg                          # mg_n ← mg (ф.к)
        sol.trace.append("p_53t")
        return sol
    forced_d61 = overrides.get("type3.d61") if overrides else None
    d61 = c60 >= 0 and c61 >= 0
    if forced_d61 == "D61":
        d61 = True
    elif forced_d61 == "D68":
        d61 = False
    if d61:                                    # p_61t (D61)
        sol.an = 0.2 * na                      # C62
        si3_2 = si3_1 - 2.0 * sol.an           # C63
        al3_2 = al3_1 - sol.an                 # C64
        sol.fe_n = fe3_1
        sol.mg_n = mg
        sol.trace.append("D61")
    else:                                      # p_68 → p_68t (безусловно)
        sol.an = ca                            # C69
        si3_2 = si3_1 - 2.0 * sol.an           # C70
        al3_2 = al3_1 - sol.an                 # C71
        sol.fe_n = fe3_1
        sol.mg_n = mg
        sol.trace.append("D68")
    sol.ca_n = ca - sol.an                     # C65 (D61) / C72=0 (D68)

    # ---- иллит/хлорит ----
    c90 = 4.5 * mg - al3_2 + k                 # C90
    c95 = (k + 4.5 * mg - al3_2) / (4.5 * k1 - k3)   # C95
    c97 = mg - k1 * c95                        # C97
    f93 = (k / 2.0 - c97) >= 0                 # F93

    forced_p142 = overrides.get("type3.p_142") if overrides else None
    if forced_p142 == "p_142":
        p142 = True
    elif forced_p142 == "no_p_142":
        p142 = False
    else:
        p142 = c90 < 0
    if p142:                                   # p_142: ill = mg
        ill = mg                               # C142
        or_ = k - 2.0 * ill                    # C143
        mg_1 = 0.0                             # C144
        fe3_2 = fe3_1 - ill                    # C145
        si3_3 = si3_2 - 16.0 * ill - 6.0 * or_  # C146
        al3_3 = al3_2 - or_ - 6.5 * ill        # C147
        sol.ill, sol.or_ = ill, or_
        sol.mg_n = 0.0
        sol.fe_n = fe3_2
        sol.trace.append("p_142")
        if fe3_2 < 0:                          # d149 → p_159
            _t3_fe_path(sol, si3_2, al3_2, mg, k, k1, k2, k3, k4,
                        fe3_1, ill, or_in=0.0, ca_in=ca_in,
                        si3_3_in=si3_3, al3_3_in=al3_3)
            return sol
        if si3_3 < 0:                          # p_152 → p_253
            _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, fe3_2,
                           k1, k2, k3, k4)
            return sol
        _t3_balance(sol, si3_3, al3_3)         # p_156 → p_81
        return sol

    if forced_p142 == "no_p_142":
        sol.trace.append("no_p_142")
    if f93 and c97 > 0:                        # p_97 → p_93t (Mg-путь)
        sol.ill = c97                        # C97 (ill_3+ill) — пишется сразу
        sol.chl = c95                        # C95 — пишется всегда
        sol.or_ = k - 2.0 * c97              # C98
        sol.mg_n = 0.0                       # C99 — статичный ноль
        c100 = fe3_1 - c97 - k2 * c95        # C100
        c101 = si3_2 - 16.0 * c97 - k4 * c95 - 6.0 * sol.or_   # C101
        if c100 >= 0 and c101 >= 0:            # D106 → rVI
            sol.fe_n = c100
            sol.si_n = c101
            sol.trace.append("D106")
            return sol
        if c100 < 0:                           # D109 → p_159 (Fe-путь)
            sol.trace.append("D109-fe")
            _t3_fe_path(sol, si3_2, al3_2, mg, k, k1, k2, k3, k4,
                    fe3_1, c97, or_in=0.0, ca_in=ca_in,
                    si3_3_in=c101, al3_3_in=0.0, overrides=overrides)
            return sol
        _t3_after_p253(sol, si3_2, al3_2, k, ca_in, 0.0, c100,   # D112 → p_253
                       k1, k2, k3, k4)
        return sol

    # p_114 → p_119: ill = k/2
    ill = k / 2.0                              # C116
    sol.ill = ill
    e119 = mg - 0.5 * k - (k1 / k3) * (al3_2 - 3.25 * k)   # E119
    forced_p114 = overrides.get("type3.p_114") if overrides else None
    if forced_p114 == "F119+":
        e119_ok = True
    elif forced_p114 == "F126-":
        e119_ok = False
    else:
        e119_ok = e119 >= 0
    if e119_ok:                                # f119 → p_119t: хлорит по Al
        chl = (al3_2 - 6.5 * ill) / k3         # C120
        mg_1 = mg - ill - k1 * chl             # C121
        fe3_2 = fe3_1 - ill - k2 * chl         # C122
        si3_3 = si3_2 - 16.0 * ill - k4 * chl  # C123
        sol.trace.append("F119+")
    else:                                      # p_126: хлорит по Mg
        chl = (mg - ill) / k1                  # C127
        mg_1 = 0.0                             # C128 (статик)
        fe3_2 = fe3_1 - ill - k2 * chl         # C129
        si3_3 = si3_2 - 16.0 * ill - k4 * chl  # C130
        sol.trace.append("F126-")
    sol.chl = chl
    sol.mg_n = mg_1
    sol.fe_n = fe3_2
    # p_119t/p_126 al3_3 не пастят: сохраняется входящее значение ячейки I51
    # (напр. из коридора aType_5→m_531, где al3_3=C534); иначе 0.
    al3_3 = al3_3_in if al3_3_in is not None else 0.0
    if fe3_2 < 0:                              # p_132 → p_159 (Fe-путь)
        _t3_fe_path(sol, si3_2, al3_2, mg, k, k1, k2, k3, k4,
                    fe3_1, ill, or_in=0.0, ca_in=ca_in,
                    si3_3_in=si3_3, al3_3_in=al3_3, overrides=overrides)
        return sol
    if si3_3 < 0:                              # p_136 → p_253
        _t3_after_p253(sol, si3_2, al3_2, k, ca_in, mg_1, fe3_2,
                       k1, k2, k3, k4)
        return sol
    _t3_balance(sol, si3_3, al3_3)             # p_139 → p_81
    return sol


# --------------------------------------------------------------------------
# Типы 4-5 (алюминиевые): обычный путь (кварцит) и mm-путь (highal)
# --------------------------------------------------------------------------
def _t45_after_m37x(sol: TypeSolution, si: float, al: float, k: float,
                    mg: float, na: float, ca: float,
                    m366_rewrite: bool = False) -> None:
    """m_366→m_371→(m_376→m_379): возврат из Ca-дефицита (C366..C383).

    m366_rewrite — True при входе из m_334 (d343): Excel затирает
    an=ca, ca_n=0. False при входе из m_281t (d294-false): an/ca_n=0
    уже выставлены в m_287t и не перезаписываются.
    """
    an = ca                                # C366
    ca_n = 0.0                             # C367
    if m366_rewrite:
        sol.an = an
        sol.ca_n = ca_n
    si_n0 = (si - 6.0 * k) - 2.0 * ca      # C368 (C276)
    al4_2 = (al - k) - ca                  # C369 (C277)
    sol.si_n = si_n0
    mm = (al4_2 - na) / 4.0                # C371
    ab = na - mm                           # C372
    sol.mm, sol.ab = mm, ab
    sol.mg_n = mg - 2.0 * mm               # C373
    si_n = si_n0 - 24.0 * mm - 6.0 * ab    # C374
    if si_n < 0:                           # d376 → m_379
        mm3 = (si_n0 - 6.0 * na) / 18.0    # C379
        ab3 = na - mm3                     # C380
        sol.mm, sol.ab = mm3, ab3
        sol.mg_n = mg - 2.0 * mm3          # C381
        sol.si_n = 0.0                     # C382
        sol.gb = al4_2 - 5.0 * mm3 - ab3   # C383
        sol.trace.append("m_366-m_379")
        return
    sol.si_n = si_n
    sol.trace.append("m_366")


def _t45_m334(sol: TypeSolution, si4_1: float, al4_1: float, mg0v: float,
              na: float, k1: float, k2: float, k3: float, k4: float,
              ca: float, ca_in: float, fe3_1: float, si: float, al: float,
              k: float, mg: float, mm4: float) -> TypeSolution:
    """m_334: mm-путь по Na (C333..C341) + коридоры m_343/m_346/m_360."""
    c333 = si4_1 - 6.4 * na
    c334 = si4_1 - 24.0 * na
    if c333 > 0 and c334 <= 0:                 # d334 → m_334t
        mm = (si4_1 - 6.4 * na) / 17.6         # C335
        ab = na - mm                           # C336 (mm_4 = C335)
        an = 0.2 * ab                          # C337
        ca_n = ca - an                         # C338
        mg_n = mg0v - 2.0 * mm                 # C340
        gb = (si - 6.0 * k) - 1.2 * ab - 5.0 * mm   # C341 (C276)
        sol.mm, sol.ab, sol.an = mm, ab, an
        sol.ca_n = ca_n
        sol.mg_n = mg_n
        sol.gb = gb
        sol.fe_n = fe3_1                        # fe_n ← fe3_1
        sol.si_n = 0.0                          # C339
        if ca_n < 0:                           # d343 → m_366
            _t45_after_m37x(sol, si, al, k, mg, na, ca, m366_rewrite=True)
            sol.trace.append("m_334t->m_343")
            return sol
        sol.trace.append("mm-path (D334)")
        return sol
    if si4_1 - 6.4 * na <= 0:                  # d346 → m_346t
        sol.ab = na                             # C347
        sol.fe_n = fe3_1                        # C348 (копия fe3_1)
        c336 = na - mm4                         # C336 (входящий mm_4)
        a350 = (si4_1 - 6.0 * c336) / 2.0      # C350
        if ca - a350 >= 0:                     # d349 → m_349t
            sol.an = a350
            sol.gb = al4_1 - 1.2 * c336        # C351
            sol.ca_n = ca - 0.2 * c336         # C352
            sol.trace.append("m_346-349t")
            return sol
        sol.an = ca                             # m_354 (C355)
        sol.ca_n = 0.0                          # C356
        al3 = al4_1 - na - a350                 # C357
        si_n = si4_1 - 6.0 * na - 2.0 * a350   # C358
        sol.si_n = si_n
        _t3_balance(sol, si_n, al3)             # p_81
        sol.trace.append("m_354->p81")
        return sol
    sol.mm = na                                 # m_360
    sol.mg_n = mg0v - 2.0 * na                  # C362
    si_n = si4_1 - 24.0 * na                    # C363
    al3 = al4_1 - 5.0 * na                      # C364
    sol.si_n = si_n
    _t3_balance(sol, si_n, al3)                 # p_81
    sol.trace.append("m_360->p81")
    return sol


def _t45_m281(sol: TypeSolution, si4_1: float, al4_1: float, mg0v: float,
              na: float, k1: float, k2: float, k3: float, k4: float,
              ca: float, ca_in: float, fe3_1: float, al: float, si: float,
              k: float, mg: float) -> TypeSolution:
    """m_281: распределение Mg после иллита (d279-true ветвь m_279)."""
    if mg0v - (al4_1 - 1.2 * na) / 1.9 >= 0:   # d281 → m_281t
        mm = (al4_1 - 1.2 * na) / 3.8      # C282
        mg_n = mg0v - 2.0 * mm             # C283
        si4_2 = si4_1 - 24.0 * mm          # C285
        sol.mm = mm
        sol.mg_n = mg_n
        sol.si_n = si4_2
        if si4_2 - 6.4 * (na - mm) > 0:    # d287 → m_287t
            ab = na - mm                   # C288
            an = 0.2 * ab                  # C290
            ca_n = ca - an                 # C292
            si_n = si4_2 - 6.0 * ab - 2.0 * an   # C291
            sol.ab, sol.an = ab, an
            sol.ca_n = ca_n
            sol.si_n = si_n
            if ca_n > 0:                   # d294 → rVI
                sol.trace.append("m_281t-m_287t")
                return sol
            _t45_after_m37x(sol, si, al, k, mg, na, ca)   # m_371
            return sol
        # d287 false → m_334
        return _t45_m334(sol, si4_1, al4_1, mg0v, na, k1, k2, k3, k4,
                         ca, ca_in, fe3_1, si, al, k, mg, mm)
    # d281 false → m_296 → m_296t
    mm = mg0v / 2.0                        # C297
    sol.mm = mm
    sol.mg_n = 0.0                         # C298
    si4_2 = si4_1 - 24.0 * mm              # C299
    ab = na - mm                           # C300
    sol.ab = ab
    sol.si_n = si4_2
    if ca - 0.2 * ab >= 0:                 # d302 → m_302t
        an = 0.2 * ab                      # C303
        ca_n = ca - an                     # C304
        sol.an = an
        sol.ca_n = ca_n
        si_n = si4_2 - 6.4 * (na - mm)     # C305
        al3 = al4_1 - 5.0 * mm - 1.2 * ab  # C306
        sol.si_n = si_n
        if si_n < 0:                       # d308 → m_334
            return _t45_m334(sol, si4_1, al4_1, mg0v, na, k1, k2, k3,
                             k4, ca, ca_in, fe3_1, si, al, k, mg, mm)
        _t3_balance(sol, si_n, al3)        # p_81 (si3_3=C305, al3_3=C306)
        sol.trace.append("m_296t->p81")
        return sol
    # m_311 (дефицит Ca)
    an = ca                                # C312
    sol.an = an
    sol.ca_n = 0.0                         # C313
    si_n = si4_2 - (6.0 * na - mm) - 2.0 * ca   # C314
    al3 = (al - k) - 5.0 * mm - ab - ca    # C315 (C277)
    sol.si_n = si_n
    if si_n < 0:                           # d317 → m_334
        return _t45_m334(sol, si4_1, al4_1, mg0v, na, k1, k2, k3,
                         k4, ca, ca_in, fe3_1, si, al, k, mg, mm)
    _t3_balance(sol, si_n, al3)            # p_81 (si3_3=C314)
    sol.trace.append("m_311->p81")
    return sol


def _t45_m279(sol: TypeSolution, si4_1: float, al4_1: float, mg0v: float,
              na: float, k1: float, k2: float, k3: float, k4: float,
              ca: float, ca_in: float, fe3_1: float, al: float, si: float,
              k: float, mg: float) -> TypeSolution:
    """m_279: распределение Mg после иллита → m_281/m_296/m_320 + mm-коридоры."""
    if al4_1 - 5.0 * na <= 0:                  # d279 → m_281
        return _t45_m281(sol, si4_1, al4_1, mg0v, na, k1, k2, k3, k4,
                         ca, ca_in, fe3_1, al, si, k, mg)
    # d279 false (избыток Al) → m_320/m_322
    if mg0v - 2.0 * na > 0:                    # d322 → m_322t
        sol.mm = na                            # C323
        sol.mg_n = mg0v - 2.0 * na             # C324
        al4 = al4_1 - 5.0 * na                 # C325 (1-я оценка → al4_1)
        si4 = si4_1 - 24.0 * na                # C326 (1-я оценка → si4_1)
        # C326 реевалируется после записи si4_1 (=первый eval): si4_2/si3_3/si_n
        # и ворота d328 (C328=C326) получают цепочку si4_1-48na.
        sol.si_n = si4 - 24.0 * na
        if si4 - 24.0 * na < 0:                # d328 → m_334
            return _t45_m334(sol, si4, al4, mg0v, na, k1, k2, k3,
                             k4, ca, ca_in, fe3_1, si, al, k, mg, na)
        # p_81: si3_3=si4_1e-48na, al3_3=al4_1e-10na (цепочка копий C326/C325)
        _t3_balance(sol, si4 - 24.0 * na, al4 - 5.0 * na)
        sol.trace.append("m_322t->p81")
        return sol
    # m_296 (mg0v-2na<=0) → m_296t
    mm = mg0v / 2.0                            # C297
    sol.mm = mm
    sol.mg_n = 0.0
    si4_2 = si4_1 - 24.0 * mm                  # C299
    ab = na - mm                               # C300
    sol.ab = ab
    sol.si_n = si4_2
    if ca - 0.2 * ab >= 0:                     # m_302t
        an = 0.2 * ab
        sol.an = an
        sol.ca_n = ca - an
        si_n = si4_2 - 6.4 * (na - mm)         # C305
        al3 = al4_1 - 5.0 * mm - 1.2 * ab      # C306
        sol.si_n = si_n
        if si_n < 0:
            return _t45_m334(sol, si4_1, al4_1, mg0v, na, k1, k2, k3,
                             k4, ca, ca_in, fe3_1, si, al, k, mg, mm)
        _t3_balance(sol, si_n, al3)
        sol.trace.append("m_296t(322)->p81")
        return sol
    an = ca
    sol.an = an
    sol.ca_n = 0.0
    si_n = si4_2 - (6.0 * na - mm) - 2.0 * ca  # C314
    al3 = (al - k) - 5.0 * mm - ab - ca        # C315 (C277)
    sol.si_n = si_n
    if si_n < 0:
        return _t45_m334(sol, si4_1, al4_1, mg0v, na, k1, k2, k3,
                         k4, ca, ca_in, fe3_1, si, al, k, mg, mm)
    _t3_balance(sol, si_n, al3)
    sol.trace.append("m_311(322)->p81")
    return sol


def _t45_504(sol: TypeSolution, si4_1: float, al4_1: float, mg4_1: float,
             fe4_2: float, na: float, an: float,
             k1: float, k2: float, k3: float, k4: float) -> None:
    """m_504: хлорит из остатка Si после ab/an (limit by k4)."""
    chl = (si4_1 - 6.0 * na - 2.0 * an) / k4   # C504
    sol.chl = chl
    sol.si_n = 0.0                              # C505
    sol.gb = al4_1 - k3 * chl - na - an         # C506
    sol.fe_n = fe4_2 - k2 * chl                 # C507
    sol.mg_n = mg4_1 - k1 * chl                 # C508
    sol.trace.append("t45-m504")


def _t45_513(sol: TypeSolution, si4_1: float, al4_1: float, mg4_1: float,
             fe4_2: float, na: float, k1: float, k2: float, k3: float,
             k4: float, ca: float, ca_in: float, al: float, si: float,
             k: float, mg0v: float, fe3_1: float) -> TypeSolution:
    """m_513: mm=na, затем m_520 → p_227 или m_279.

    ``fe4_2`` идёт в ``_t5`` (C515/C... используют fe3_2), а в ``m_279``
    передаётся исходный ``fe3_1`` (m_513 пишет только fe3_2, fe3_1 не трогает).
    """
    sol.mm = na                                 # C513
    si3 = si4_1 - 24.0 * na                     # C514
    mg1 = mg4_1 - 2.0 * na                      # C515
    al3 = al4_1 - 5.0 * na                      # C516
    # D520 = AND(C518>=0,C519>=0,C520>=0); C518=al4_1-10*na, т.к. m_513
    # уже перезаписал имя al4_1 (=C516) и формула C516 реевалируется.
    al3_gate = al4_1 - 10.0 * na
    sol.mg_n = mg1
    sol.si_n = si3
    if si3 >= 0 and mg1 >= 0 and al3_gate >= 0:      # m_520 (d520) → p_227
        _t5(sol, ca_in, mg1, fe4_2, al3, si3, k1, k2, k3, k4, 0.0)
        sol.trace.append("t45-m513->t5")
        return sol
    # → m_279 (al4_1 уже = al3 после m_513); C283/C297/C324 читают mg0 (J272).
    # fe_n в m_346t/m_334t берётся из fe3_1 (исходного), не из fe4_2.
    return _t45_m279(sol, si4_1, al3, mg0v, na, k1, k2, k3, k4,
                     ca, ca_in, fe3_1, al, si, k, mg0v)


def _t45_m531w(sol: TypeSolution, si: float, al: float, mg: float, na: float,
               k: float, ca: float, ca_in: float, k1: float, k2: float,
               k3: float, k4: float, fe3_1: float,
               st0: Stage0) -> TypeSolution:
    """m_531w: копии C532-C536 → m_281."""
    ill = k / 2.0                             # C532
    si4_1 = si - 16.0 * ill                   # C533
    al4_1 = al - 6.5 * ill                    # C534
    fe4_2 = fe3_1 - ill                       # C535
    mg4_1 = mg - ill                          # C536
    sol.ill = ill
    sol.fe_n = fe4_2                          # fe_n = C535
    sol.mg_n = mg4_1
    return _t45_m281(sol, si4_1, al4_1, mg4_1, na, k1, k2, k3, k4,
                     ca, ca_in, fe3_1, al, si, k, mg)


def _t45_m528_corridor(sol: TypeSolution, si: float, al: float, mg: float,
                       na: float, k: float, ca: float, ca_in: float,
                       k1: float, k2: float, k3: float, k4: float,
                       fe3_1: float, st0: Stage0) -> TypeSolution:
    """aType_5 → m_528(fe3_1>k/2) → m_531 → m_538/540/542/544/549/551/552."""
    ill = k / 2.0                             # C532
    si4_1 = si - 16.0 * ill                   # C533
    al4_1 = al - 6.5 * ill                    # C534
    fe4_2 = fe3_1 - ill                       # C535
    mg4_1 = mg - ill                          # C536
    sol.ill = ill
    sol.fe_n = fe4_2
    sol.mg_n = mg4_1
    if mg4_1 <= 0:                            # d538 → cleane_4 → aType_3
        return type3(st0, al3_3_in=al4_1,
                     overrides=getattr(st0, "overrides", None))
    c539 = ca - 0.2 * na                      # C539
    c540 = si4_1 - 6.0 * na - ca              # C540
    if c539 < 0 and c540 <= 0:                # d540 → cleane_4
        return type3(st0, al3_3_in=al4_1,
                     overrides=getattr(st0, "overrides", None))
    c542 = si4_1 - 6.0 * na - 0.4 * na        # C542
    if c539 >= 0 and c542 <= 0:               # d542 → cleane_4
        return type3(st0, al3_3_in=al4_1,
                     overrides=getattr(st0, "overrides", None))
    mm = na                                   # C544
    si2 = si4_1 - 24.0 * mm                   # C545
    mg2 = mg4_1 - 2.0 * mm                    # C546
    al2 = al4_1 - 5.0 * mm                    # C547
    sol.mm = mm
    if mg2 < 0 and si2 >= 0:                  # d550 → m_531w
        return _t45_m531w(sol, si, al, mg, na, k, ca, ca_in, k1, k2, k3, k4,
                          fe3_1, st0)
    if mg2 < 0 and si2 < 0:                   # d551 → m_531w
        return _t45_m531w(sol, si, al, mg, na, k, ca, ca_in, k1, k2, k3, k4,
                          fe3_1, st0)
    if mg2 >= 0 and si2 >= 0:                 # d552 → m_552t
        mg_1 = mg2                            # C546
        fe3_2 = fe4_2                         # C535
        si3_3 = si2                           # C545
        al3_3 = al2                           # C547
        sol.mg_n = mg_1
        sol.fe_n = fe3_2
        sol.si_n = si3_3
        _t5(sol, ca_in, mg_1, fe3_2, al3_3, si3_3, k1, k2, k3, k4, 0.0)
        sol.trace.append("t45-m552t->t5")
        return sol
    # C549>=0, C550<0 → m_531w
    return _t45_m531w(sol, si, al, mg, na, k, ca, ca_in, k1, k2, k3, k4,
                      fe3_1, st0)


def type45(st0: Stage0, overrides=None) -> TypeSolution:
    """Полный порт «Нач+Type 3» типов 4-5: aType_4 + m_274t/m_385t/m_401 +
    m_414t/m_418t/m_424, m_433..m_513 (нормальный путь) и m_279/m_334 (mm-путь)."""
    d = st0.fe
    si, al, mg, na, k = _base(d)
    ca = st0.ca
    ca_in = st0.ca_n_in
    k1, k2, k3, k4 = st0.k1, st0.k2, st0.k3, st0.k4
    fe3_1 = st0.fe3_1
    # mg0 — отдельная именованная ячейка (J272), НЕ базовый MgO. Её пишет
    # только aType_4 (mg0=mg); для типа 5 aType_5 её не трогает → остаётся 0
    # (коридор m_528 задаёт mg0 через m_531, и там значение проброшено явно).
    mg0 = mg if st0.rock_type != 5 else 0.0
    sol = TypeSolution()

    if st0.rock_type == 5:                     # aType_5: d525 → m_274 | m_528
        if k2 == 0:                            # m_274t (421): or=K, si1, al1
            or_ = k                            # C275
            si4_1 = si - 6.0 * k               # C276
            al4_1 = al - k                     # C277
            sol.or_ = or_
            sol.fe_n = fe3_1                   # fe_n ← fe3_1
            sol.si_n = si4_1
            return _t45_m279(sol, si4_1, al4_1, 0.0, na, k1, k2, k3, k4,
                             ca, ca_in, fe3_1, al, si, k, mg)
        if fe3_1 - k / 2.0 > 0:                # m_528 → m_531-коридор
            sol.trace.append("t45-aType5")
            return _t45_m528_corridor(sol, si, al, mg, na, k, ca, ca_in,
                                      k1, k2, k3, k4, fe3_1, st0)
        # иначе fe3_1-k/2<=0 → d528 → m_385 (fallthrough)

    if k1 == 0 and k3 == 0:                    # aType_4: d271 → m_272 → aType_3
        return type3(st0, overrides=overrides)

    if k2 == 0:                                # d274 → m_274t (or, si4_1, al4_1)
        or_ = k                                # C275
        si4_1 = si - 6.0 * k                   # C276
        al4_1 = al - k                         # C277
        sol.or_ = or_
        sol.fe_n = fe3_1                        # fe_n ← fe3_1
        sol.si_n = si4_1
        return _t45_m279(sol, si4_1, al4_1, mg0, na, k1, k2, k3, k4,
                         ca, ca_in, fe3_1, al, si, k, mg)

    if fe3_1 - k / 2.0 <= 0:                   # d385 → m_385t (ill = fe3_1)
        ill = fe3_1                            # C386
        fe4_2 = 0.0                            # C387
        si4_1 = si - 16.0 * fe3_1              # C388
        al4_1 = al - 6.5 * fe3_1               # C389
        mg4_1 = mg - fe3_1                     # C390
        sol.ill = ill
        sol.fe_n = 0.0
        sol.mg_n = mg4_1
        if (mg4_1 >= 0
                and si4_1 - 6.0 * na - 6.0 * (k - 2.0 * fe3_1) >= 0):   # d393
            or_ = k - 2.0 * fe3_1              # C394
            si_n = si4_1 - 16.0 * fe3_1        # C395 (двойной вычет ill)
            al4_1 = al4_1 - or_                # C396
            sol.or_ = or_
            sol.si_n = si_n
            return _t45_m279(sol, si_n, al4_1, mg0, na, k1, k2, k3, k4,
                             ca, ca_in, fe3_1, al, si, k, mg)
        return type3(st0, overrides=overrides)  # m_398 → aType_3

    # m_401: ill = k/2
    ill = k / 2.0                              # C402
    sol.ill = ill
    si4_1 = si - 16.0 * ill                    # C403
    al4_1 = al - 6.5 * ill                     # C404
    fe4_2 = fe3_1 - ill                        # C405
    mg4_1 = mg0 - ill                          # C406
    sol.fe_n = fe4_2
    sol.mg_n = mg4_1
    if mg4_1 <= 0:                             # m_408 → aType_3
        return type3(st0, overrides=overrides)
    c409 = ca - 0.2 * na
    c410 = si4_1 - 6.0 * na - 2.0 * ca
    if c409 < 0 and c410 <= 0:                 # m_410 → aType_3
        return type3(st0, overrides=overrides)
    c412 = si4_1 - 6.0 * na - 0.4 * na
    if c409 >= 0 and c412 <= 0:                # m_412 → aType_3
        return type3(st0, overrides=overrides)

    if 1.9 * k1 - k3 <= 0:                     # d414 → m_414t
        sol.ab = na                             # C415
        si4_2 = si4_1 - 6.0 * na               # C416
        sol.si_n = si4_2
        forced_d418 = overrides.get("type45.d418") if overrides else None
        if forced_d418 == "t45-m418t":
            d418 = True
        elif forced_d418 == "t45-m424->t5":
            d418 = False
        else:
            d418 = 0.2 * na - ca_in >= 0
        if d418:                               # d418 → m_418t (Fe-путь)
            sol.an = ca                         # C419
            sol.ca_n = 0.0                      # C420
            si3_2_ = si4_2 - 2.0 * ca           # C421
            # Квирк оригинала: C422 копируется ДВАЖДЫ — сначала в al4_1,
            # потом в al3_2. После записи в al4_1 формула C422 пересчитывается
            # (=al4_1-C415-C419), поэтому вычитание na/ca двойное.
            al4_1 = al4_1 - na - ca             # C422 → al4_1
            al3_2_ = al4_1 - na - ca            # C422 (пересчёт) → al3_2
            _t3_fe_path(sol, si3_2_, al3_2_, mg, k, k1, k2, k3, k4,
                        fe3_1, ill, or_in=0.0, ca_in=ca_in,
                        skip_fe_lookup=True, overrides=overrides)
            sol.trace.append("t45-m418t")
            return sol
        an = 0.2 * na                           # C425 (m_424)
        sol.an = an
        sol.ca_n = ca - an                      # C427
        si3_3 = si4_2 - 2.0 * an                # C426
        al3_3 = al4_1 - na - an                 # C428
        _t5(sol, ca_in, mg4_1, fe4_2, al3_3, si3_3, k1, k2, k3, k4, 0.0)
        sol.trace.append("t45-m424->t5")
        return sol

    # m_433 (обычный путь)
    c432 = mg4_1 - k1 * (1.9 * mg4_1 + 1.2 * na - al4_1) / (1.9 * k1 - k3)
    if c432 >= 0 and 2.0 * na - c432 >= 0:     # d433 → m_435t
        chl = (1.9 * mg4_1 + 1.2 * na - al4_1) / (1.9 * k1 - k3)   # C435
        sol.chl = chl
        if chl - al4_1 / k3 < 0:               # d437 → m_437t
            mm = (mg4_1 - k1 * chl) / 2.0      # C438
            ab = na - mm                       # C439
            an = 0.2 * ab                      # C440
            fe_n = fe4_2 - k2 * chl            # C441
            si_n = (si4_1 - k4 * chl - 24.0 * mm
                    - 6.0 * ab - 2.0 * an)     # C442
            ca_n = ca - an                     # C443
            sol.mm, sol.ab, sol.an = mm, ab, an
            sol.fe_n = fe_n
            sol.si_n = si_n
            sol.ca_n = ca_n
            sol.mg_n = 0.0                     # C444
            sol.trace.append("type45-normal")
            if fe_n >= 0 and si_n >= 0 and ca_n >= 0:    # d448 → rVI
                return sol
            # m_450 → m_454
            an2 = ca                           # C450
            al4_2 = al4_1 - an2                # C451
            si4_2n = si4_1 - 2.0 * an2         # C452
            sol.an = an2
            sol.si_n = si4_2n
            if 2.0 * mg4_1 + na - al4_2 < 0:   # d454 → m_455t
                mm2 = (al4_2 - na) / 4.0       # C455
                sol.mm = mm2
                sol.chl = 0.0                  # E455 ('CHL=' → 0)
                if mm2 - na < 0:               # d457 → m_458t
                    ab_n = na - mm2            # C458
                    mg_n = mg - 2.0 * mm2      # C459
                    si_n2 = si4_2n - 24.0 * mm2 - 6.0 * ab_n   # C460
                    sol.ab = ab_n
                    sol.mg_n = mg_n
                    sol.si_n = si_n2
                    if si_n2 > 0:              # d462 → rVI
                        sol.trace.append("t45-m_458t")
                        return sol
                    mm3 = (si4_2n - 6.0 * na) / 18.0   # C465 (m_465)
                    if mm3 - na < 0:           # d467 → m_468t
                        ab3 = na - mm3         # C468
                        sol.mm, sol.ab = mm3, ab3
                        sol.mg_n = mg - 2.0 * mm3  # C469
                        sol.si_n = 0.0             # C470
                        sol.gb = al4_2 - 5.0 * mm3 - ab3   # C471
                        sol.trace.append("t45-m_465")
                        return sol
                    return _t45_513(sol, si4_1, al4_1, mg4_1, fe4_2, na,
                                    k1, k2, k3, k4, ca, ca_in, al, si, k, mg0, fe3_1)
                return _t45_513(sol, si4_1, al4_1, mg4_1, fe4_2, na,
                                k1, k2, k3, k4, ca, ca_in, al, si, k, mg0, fe3_1)
            # m_473
            chl2 = (2.0 * mg4_1 + na - 2.0 * al4_2) / (2.0 * k1 - k3)  # C474
            sol.chl = chl2
            if chl2 - al4_2 / k3 < 0:          # d476 → m_477t
                mm2 = (mg4_1 - k1 * chl2) / 2.0      # C477
                ab_n = na - mm2                      # C478
                fe_n2 = fe4_2 - k2 * chl2            # C481
                si_n2 = (si4_2n - k4 * chl2
                         - 24.0 * mm2 - 6.0 * ab_n)  # C479
                sol.mm, sol.ab = mm2, ab_n
                sol.mg_n = 0.0                        # C480
                sol.fe_n = fe_n2
                sol.si_n = si_n2
                if fe_n2 >= 0 and si_n2 >= 0:        # d484 → rVI
                    sol.trace.append("t45-m_477t")
                    return sol
                chl3 = fe4_2 / k2                     # C486 (m_486)
                sol.chl = chl3
                sol.fe_n = 0.0                        # C487
                al4_1b = al4_1 - k3 * chl3            # C488
                si4_1b = si4_1 - k4 * chl3            # C489
                mg0b = mg4_1 - k1 * chl3              # C490
                sol.si_n = si4_1b
                if si4_1b - 6.0 * na >= 0:            # d492 → m_279 (mg0=J272)
                    sol.trace.append("t45-m486->m279")
                    return _t45_m279(sol, si4_1b, al4_1b, mg0b, na,
                                     k1, k2, k3, k4, ca, ca_in, fe3_1,
                                     al, si, k, mg)
                sol.ab = na                           # m_494
                if ca - 0.2 * na >= 0:                # m_496 → m_497t
                    an_n = 0.2 * na
                    sol.an = an_n
                    sol.ca_n = ca - an_n
                else:                                 # m_500
                    sol.an = ca
                    sol.ca_n = 0.0
                _t45_504(sol, si4_1b, al4_1b, mg4_1, fe4_2, na, sol.an,
                         k1, k2, k3, k4)
                sol.trace.append("t45-m486->m504")
                return sol
            return _t45_513(sol, si4_1, al4_1, mg4_1, fe4_2, na,
                            k1, k2, k3, k4, ca, ca_in, al, si, k, mg0, fe3_1)
        return _t45_513(sol, si4_1, al4_1, mg4_1, fe4_2, na,
                        k1, k2, k3, k4, ca, ca_in, al, si, k, mg0, fe3_1)
    return _t45_513(sol, si4_1, al4_1, mg4_1, fe4_2, na,
                    k1, k2, k3, k4, ca, ca_in, al, si, k, mg0, fe3_1)
