"""Выходной этап: ф.е. минералов -> весовые (%), нормировка D151/D152/D154,
итоговая строка 287 и невязки (дефект) строк 164-171 «Нач+Type 12».
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.clean_engine.stage0 import Stage0
from src.core.clean_engine.stage_vi import StageVI
from src.core.clean_engine.types import TypeSolution

# Молярные массы минералов (ячейки B31..B41, D31..D41 — «Нач+Type 12»).
_MW = {
    "ap": 336.21, "ab": 524.482, "an": 278.22, "ill": 2014.75,
    "or": 556.7, "ank": 215.952, "cc": 100.091, "q": 60.09,
    "pr": 119.982, "dl": 184.42, "rch": 114.952, "sd": 115.861,
    "prl": 86.94, "srp": 227.172, "ht": 177.716, "mst": 84.331,
    "gb": 156.008, "kn": 258.172, "mm": 2202.6, "hl": 116.896,
    "gy": 172.178, "fl": 78.08,
}

# Порядок весовых колонок E..AC (ф.е. -> (переменная, молярная, множитель)).
# множитель: 1 — ф.е.*Mw/10000; 'wt' — сырой вес.% (TiO2, C); 'div2' — /2.
_COLUMNS149 = [
    ("ap", "ap", 1.0),            # E  = D11*336.21/10000
    ("ab", "ab", 1.0),            # F
    ("an", "an", 1.0),            # G
    ("chl", "chl", 1.0),          # H  — с achl
    ("ill", "ill", 1.0),          # I
    ("or", "or", 1.0),            # J
    ("ank", "ank", 1.0),          # K
    ("cc", "cc", 1.0),            # L
    ("q", "q", 1.0),              # M
    ("rt", "tio2", "wt"),         # N  = B3*1  (TiO2 вес.%)
    ("pr", "pr0", 1.0),           # O
    ("dl", "dl", 1.0),            # P
    ("rch", "rch", 1.0),          # Q
    ("sd", "sd", 1.0),            # R
    ("prl", "prl", 1.0),          # S
    ("srp", "srp", 1.0),          # T
    ("ht", "ht", 1.0),            # U
    ("mst", "mst", 1.0),          # V
    ("gb", "gb", 1.0),            # W
    ("kn", "kn", 1.0),            # X
    ("mm", "mm", 1.0),            # Y
    ("c0", "c0", "wt"),           # Z  = C ф.е.
    ("hl", "cl", "div2"),         # AA = cl/2*116.896/10000
    ("fl", "fl", 1.0),            # AB = пустая (0)
    ("gy", "so", 1.0),            # AC = so*172.178/10000
]


@dataclass
class Output:
    """Полный выход расчёта (ф.е. + веса + итоговая строка + невязки)."""

    minerals_fe: dict[str, float] = field(default_factory=dict)  # row147
    weights149: list[float] = field(default_factory=list)        # E..AC
    row287: list[float] = field(default_factory=list)            # B..AI (34)
    defect: dict[str, float] = field(default_factory=dict)       # D164..D171


def _minerals_fe(st0: Stage0, tsol: TypeSolution, vi: StageVI) -> dict[str, float]:
    """Ф.е. минералов и прочих компонентов (строка 147 концептуально)."""
    fe = st0.fe
    m = {
        **tsol.mineral_vars(),
        "ap": fe["P2O5"],
        "q": vi.q,
        "dl": vi.dl,
        "ank": vi.ank,
        "cc": vi.cc,
        "rch": vi.rch,
        "sd": vi.sd,
        "prl": vi.prl,
        "srp": vi.srp,
        "mst": vi.mst,
        "ht": vi.ht,
        "pr0": st0.pr0,
        "tio2": None,        # вес.% напрямую (не ф.е.)
        "c0": fe.get("C", 0.0),
        "cl": fe.get("Cl", 0.0),
        "so": fe.get("SO", 0.0),
        "fl": 0.0,
    }
    return m


def _row149(m: dict[str, float], st0: Stage0) -> list[float]:
    """Весовые колонки E..AC (row149) — ф.е.*Mw/10000 без округлений."""
    out = []
    for label, var, mult in _COLUMNS149:
        if mult == "wt":
            out.append(m[var] if m[var] is not None else 0.0)
        elif mult == "div2":
            out.append(m[var] / 2.0 * _MW[label] / 10000.0)
        else:
            mol = st0.achl if label == "chl" else _MW[label]
            out.append(m[var] * mol / 10000.0)
    return out


def _sum_col(vals: list[float]) -> float:
    return sum(vals)


def output(st0: Stage0, tsol: TypeSolution, vi: StageVI) -> Output:
    """Собирает выходной пакет (эквивалент Excel-вычисления row149..287)."""
    fe = st0.fe
    m = _minerals_fe(st0, tsol, vi)
    m["tio2"] = st0.fe.get("TiO2", 0.0)   # ф.е. молярки нет, вес.% напрямую

    w149 = _row149(m, st0)                 # E..AC  (25 колонок)
    sum149 = _sum_col(w149)                # D151

    cpu149 = st0.ca_raw                    # E6 — CaO ф.е. для невязки

    # нормировка: row150 = w*100/D151; D152 = sum(row150)
    row150 = [x * 100.0 / sum149 for x in w149]
    sum150 = _sum_col(row150)              # D152
    # row153 = row150*100/D152; D154 = sum(row153)
    row153 = [x * 100.0 / sum150 for x in row150]
    sum153 = _sum_col(row153)              # D154

    # индексы row153: 0=ap(E),1=ab(F),2=an(G),3=chl(H),4=ill(I),5=or(J),
    #                6=ank(K),7=cc(L),8=q(M),9=rt(N),10=pr(O),11=dl(P),
    #               12=rch(Q),13=sd(R),14=prl(S),15=srp(T),16=ht(U),
    #               17=mst(V),18=gb(W),19=kn(X),20=mm(Y),21=c0(Z),
    #               22=hl(AA),23=fl(AB),24=gy(AC)
    def i(label: str) -> float:
        for idx, (lbl, *_rest) in enumerate(_COLUMNS149):
            if lbl == label:
                return row153[idx]
        raise KeyError(label)

    d287 = i("ab")
    e287 = i("an")
    f287 = d287 + e287                     # Pln = D287+E287
    g287 = i("or")
    h287 = i("q")
    i287 = i("mm")
    j287 = i("ill")
    k287 = i("chl")
    l287 = i("gb")
    m287 = i("kn")
    n287 = i("ap")
    o287 = i("c0")
    p287 = i("cc")
    q287 = i("dl")
    r287 = i("ank")
    s287 = i("rch")
    t287 = i("sd")
    u287 = i("srp")
    v287 = i("mst")
    w287 = i("ht")
    x287 = i("prl")
    y287 = i("pr")
    z287 = i("rt")
    aa287 = i("hl")
    ab287 = i("gy")
    ac287 = i("fl")
    ad287 = f287 + g287
    ae287 = i287 + j287 + k287 + u287
    af287 = ad287 + ae287
    ag287 = p287 + q287 + r287 + t287
    ah287 = j287 + m287
    ai287 = i287 + k287 + u287

    row287 = [sum149, sum153,
              d287, e287, f287, g287, h287, i287, j287, k287, l287, m287,
              n287, o287, p287, q287, r287, s287, t287, u287, v287, w287,
              x287, y287, z287, aa287, ab287, ac287,
              ad287, ae287, af287, ag287, ah287, ai287]

    # невязки (D164..D171) — в ф.е.
    defect = {}
    defect["SiO2"] = (fe["SiO2"]
                      - (6 * tsol.ab + 2 * tsol.an + st0.k4 * tsol.chl
                         + 16 * tsol.ill + 6 * tsol.or_ + vi.q
                         + 2 * vi.srp + 2 * tsol.kn + 24 * tsol.mm))
    defect["Al2O3"] = (fe["Al2O3"]
                       - (tsol.ab + tsol.an + st0.k3 * tsol.chl
                          + 6.5 * tsol.ill + tsol.or_ + tsol.gb
                          + tsol.kn + 5 * tsol.mm))
    defect["Na2O"] = fe["Na2O"] - (tsol.ab + tsol.mm + m["cl"] / 2.0)
    defect["K2O"] = fe["K2O"] - (2 * tsol.ill + tsol.or_)
    defect["MgO"] = (fe["MgO"]
                     - (st0.k1 * tsol.chl + tsol.ill + vi.dl
                        + 3 * vi.srp + vi.mst + 2 * tsol.mm))
    defect["FeO"] = (fe["FeO"]
                     - (st0.k2 * tsol.chl + tsol.ill + vi.ank
                        + st0.pr0 + vi.sd + 2 * vi.ht))
    defect["CaO"] = cpu149 - (3.36 * m["ap"] + tsol.an + vi.ank
                              + vi.cc + vi.dl)
    defect["MnO"] = fe["MnO"] - (vi.rch + vi.prl)

    return Output(minerals_fe=m, weights149=w149, row287=row287,
                  defect=defect)
