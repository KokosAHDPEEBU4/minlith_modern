"""Runner: полный прогон excel_port (формулы + VBA VM) для образца.

Устанавливает вход, исполняет граф VBA (начиная с aDefin) и возвращает
значения именованных переменных.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.core.excel_port.interpreter import identity_round
from src.core.excel_port.vm import VbaVM
from src.core.excel_port.workbook import Workbook

DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=4)
def _load_raw(data_dir: Path) -> dict:
    """Разобранный workbook_raw.json (кэш на уровне каталога данных).

    Экземпляры Workbook копируют словарь ячеек (Workbook.__init__), поэтому
    общий raw между прогонами безопасен: мутации идут только в копию.
    """
    raw: dict = json.loads((data_dir / "workbook_raw.json").read_text(encoding="utf-8"))
    return raw


def load_workbook(data_dir: Path | None = None, rounding: bool = True) -> Workbook:
    d = Path(data_dir or DATA)
    round_fn = None if rounding else identity_round
    return Workbook(_load_raw(d), round_fn=round_fn)


@lru_cache(maxsize=4)
def load_structure(data_dir: Path | None = None) -> dict:
    """VBA-структура процедур (кэшируется: читается только на чтение)."""
    d = data_dir or DATA
    return json.loads((d / "vba_structure.json").read_text(encoding="utf-8"))


def run_sample(oxide_values: dict[str, float], data_dir: Path | None = None,
               entry: str = "aDefin", rounding: bool = True) -> dict:
    """Прогнать образец и вернуть значения именованных переменных (ф.е.).

    См. :func:`run_sample_full` — здесь отбрасывается строка 287.
    """
    names, _row287 = run_sample_full(oxide_values, data_dir=data_dir,
                                     entry=entry, rounding=rounding)
    return names


# Колонки строки 287 листа «Нач+Type 12» (B..AI, 34 значения).
_ROW287_COLS = (
    "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI",
)


def _read_row287(wb: Workbook) -> list[float]:
    """Итоговая строка 287 (вес.% минералов) листа «Нач+Type 12»."""
    sheet = "Нач+Type 12"
    out: list[float] = []
    for col in _ROW287_COLS:
        try:
            value = wb.eval_cell(sheet, f"{col}287")
            out.append(float(value) if isinstance(value, (int, float)) else 0.0)
        except Exception:  # noqa: BLE001 — незаполненная ячейка -> 0
            out.append(0.0)
    return out


def run_sample_full(oxide_values: dict[str, float], data_dir: Path | None = None,
                    entry: str = "aDefin", rounding: bool = True,
                    ) -> tuple[dict, list[float]]:
    """Прогнать образец через формульный движок + VBA VM.

    Args:
        rounding: True — как в Excel (ROUND на каждом шаге);
                  False — «чистый» режим без округлений (полная точность).

    Returns:
        (names, row287): значения именованных переменных (имена -> значения)
        и итоговая строка 287 листа «Нач+Type 12» (34 значения, B..AI).
    """
    wb = load_workbook(data_dir, rounding=rounding)
    structure = load_structure(data_dir)

    # Вход записываем на лист Нач+Type 3 (VBA затем копирует в Type 12)
    wb.set_input("Нач+Type 3", oxide_values)

    vm = VbaVM(wb, structure)
    vm.active_sheet = "Нач+Type 3"
    vm.run(entry)

    # собрать значения всех именованных переменных
    result = {}
    for name, (sheet, coord) in wb.names.items():
        try:
            result[name] = wb.eval_cell(sheet, coord)
        except Exception as e:  # noqa: BLE001
            result[name] = f"ERR:{e}"
    result["_calls"] = list(vm.call_log)
    result["_assignments"] = list(vm.assignments)
    return result, _read_row287(wb)
