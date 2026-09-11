"""Runner: полный прогон excel_port (формулы + VBA VM) для образца.

Устанавливает вход, исполняет граф VBA (начиная с aDefin) и возвращает
значения именованных переменных.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.core.excel_port.vm import VbaVM
from src.core.excel_port.workbook import Workbook

DATA = Path(__file__).resolve().parent / "data"


def load_workbook(data_dir: Optional[Path] = None) -> Workbook:
    d = data_dir or DATA
    raw = json.loads((d / "workbook_raw.json").read_text(encoding="utf-8"))
    return Workbook(raw)


def load_structure(data_dir: Optional[Path] = None) -> dict:
    d = data_dir or DATA
    return json.loads((d / "vba_structure.json").read_text(encoding="utf-8"))


def run_sample(oxide_values: dict[str, float], data_dir: Optional[Path] = None,
               entry: str = "aDefin") -> dict:
    """Прогнать образец через формульный движок + VBA VM.

    Returns:
        dict с значениями именованных переменных (имена -> значения).
    """
    wb = load_workbook(data_dir)
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
    return result
