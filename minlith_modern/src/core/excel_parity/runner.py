"""Runner: полный прогон чистого движка для одного образца."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.excel_parity.branches import (
    COEFFICIENT_BAND_INFO,
    ROCK_TYPE_INFO,
    STAGE_VI_INFO,
    TYPE_BRANCH_INFO,
    BranchPath,
)
from src.core.excel_parity.output import Output, output
from src.core.excel_parity.stage0 import DEFAULT_OXIDES, Stage0, compute_stage0
from src.core.excel_parity.stage_vi import StageVI, solve_stage_vi
from src.core.excel_parity.types import TypeSolution, solve_type


@dataclass
class ExcelRun:
    """Результат полного прогона чистого движка."""

    st0: Stage0 = field(default_factory=Stage0)
    tsol: TypeSolution = field(default_factory=TypeSolution)
    vi: StageVI = field(default_factory=StageVI)
    out: Output = field(default_factory=Output)

    @property
    def trace(self) -> list[str]:
        return self.tsol.trace + self.vi.trace

    @property
    def names(self) -> dict[str, float]:
        """Имена переменных, совпадающие с набором excel_port (для сверки)."""
        fe = self.st0.fe
        n: dict[str, float] = {
            # ф.е. базовых оксидов и производные (имена оригинала)
            "na": fe["Na2O"], "k": fe["K2O"], "mg": fe["MgO"],
            "cl": fe["Cl"], "so": fe["SO"], "c0": fe["C"], "s": self.st0.s,
            "ca": self.st0.ca,
            "pr0": self.st0.pr0, "fe3_1": self.st0.fe3_1,
            "achl": self.st0.achl, "k_1": self.st0.k1, "k_2": self.st0.k2,
            "k_3": self.st0.k3, "k_4": self.st0.k4,
            # минералы типов
            **self.tsol.mineral_vars(),
            # остатки после типов
            "ca_n": self.tsol.ca_n, "mg_n": self.tsol.mg_n,
            "fe_n": self.tsol.fe_n, "si_n": self.tsol.si_n,
            # минералы VI этапа
            "dl": self.vi.dl, "ank": self.vi.ank, "cc": self.vi.cc,
            "rch": self.vi.rch, "q": self.vi.q, "sd": self.vi.sd,
            "prl": self.vi.prl, "srp": self.vi.srp, "mst": self.vi.mst,
            "ht": self.vi.ht,
        }
        return n

    @property
    def path(self) -> BranchPath:
        """Структурированный маршрут веток (для графа/диагностики).

        Собирается из уже принятых решений: полоса коэффициентов и тип
        породы (стадия 0), подписи веток типа и VI этапа. Расчёт не меняет.
        """
        p = BranchPath()
        band = self.st0.coefficient_band
        cond, src = COEFFICIENT_BAND_INFO.get(band, ("", ""))
        p.add("stage0", f"band_{band or '?'}", condition=cond, source=src,
              value=self.st0.F)
        rt = int(self.st0.rock_type)
        cond, src = ROCK_TYPE_INFO.get(rt, ("", ""))
        p.add("stage0", f"rock_type_{rt}", condition=cond, source=src)
        for label in self.tsol.trace:
            cond, src = TYPE_BRANCH_INFO.get(label, ("", ""))
            p.add("type", label, condition=cond, source=src)
        for label in self.vi.trace:
            cond, src = STAGE_VI_INFO.get(label, ("", ""))
            p.add("stage_vi", label, condition=cond, source=src)
        return p


def run_from_stage0(st0: Stage0) -> ExcelRun:
    """Прогнать уже посчитанную стадию 0 через типы/VI-этап/вывод."""
    tsol = solve_type(st0)
    vi = solve_stage_vi(st0, tsol)
    out = output(st0, tsol, vi)
    return ExcelRun(st0=st0, tsol=tsol, vi=vi, out=out)


def run_sample(oxide_values: dict[str, float],
               data_dir: object | None = None,
               entry: str = "aDefin",
               rounding: bool | None = None) -> ExcelRun:
    """Прогнать образец через чистый движок (без округлений).

    Аргументы data_dir/entry/rounding приняты для совместимости сигнатуры
    c excel_port.run_sample; чистый движок всегда считает в float64.
    """
    merged = {**DEFAULT_OXIDES, **{k: (0.0 if v is None else v)
                                   for k, v in oxide_values.items()}}
    return run_from_stage0(compute_stage0(merged))
