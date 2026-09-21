"""Адаптер excel_exact к интерфейсу MineralAlgorithm.

Движок — полная копия оригинальной книги MINLITH: формулы и VBA исполняются
с пошаговым ROUND ровно как в Excel (включая накопление ошибки округления).

В отличие от :class:`~src.core.excel_parity.algorithm.ExcelParityAlgorithm`,
который считает тот же алгоритм в float64 без округлений, здесь входом
служат исходные весовые проценты оксидов (``AlgorithmInput.oxide_wt``):
книга сама пересчитывает вес.% -> ф.е. (D = ROUND(B*10000/C, …)), и этот
шаг тоже должен быть частью копии.
"""

from __future__ import annotations

from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.excel_port.runner import run_sample


def _num(value: object) -> float:
    """Привести значение именованной переменной к float (ERR/None -> 0.0)."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


class ExcelExactAlgorithm:
    """Адаптер :class:`~src.core.algorithm.MineralAlgorithm` → excel_exact.

    Использует ``excel_port.run_sample(rounding=True)``: полный прогон
    формульного графа + VBA с округлениями Excel.
    """

    def __init__(self) -> None:
        self.last: dict | None = None

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        if not inp.oxide_wt:
            raise ValueError(
                "excel_exact требует исходные весовые проценты "
                "(AlgorithmInput.oxide_wt): движок, как и книга MINLITH, "
                "сам пересчитывает вес.% -> ф.е. с пошаговым ROUND."
            )
        run = run_sample(dict(inp.oxide_wt), rounding=True)
        self.last = run
        return AlgorithmOutput(
            Ab=_num(run.get("ab")), An=_num(run.get("an")), Or=_num(run.get("or")),
            Ill=_num(run.get("ill")), Chl=_num(run.get("chl")),
            Kn=_num(run.get("kn")), Mm=_num(run.get("mm")), Gb=_num(run.get("gb")),
            Q=_num(run.get("q")), Dl=_num(run.get("dl")), Ank=_num(run.get("ank")),
            Cc=_num(run.get("cc")), Rch=_num(run.get("rch")), Sd=_num(run.get("sd")),
            Srp=_num(run.get("srp")), Mst=_num(run.get("mst")), Ht=_num(run.get("ht")),
            Prl=_num(run.get("prl")),
            residuals={
                "ca_n": _num(run.get("ca_n")), "mg_n": _num(run.get("mg_n")),
                "fe_n": _num(run.get("fe_n")), "si_n": _num(run.get("si_n")),
            },
        )
