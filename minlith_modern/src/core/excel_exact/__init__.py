"""excel_exact — полная 1:1 копия оригинальной книги MINLITH (лист+VBA+ROUND).

Движок исполняет тот же граф формул и VBA, что и ``excel_port`` в режиме
``rounding=True``: на каждом шаге применяется округление ровно так, как это
делает Excel (включая накопление ошибки округления).

Отличие от ``excel_parity``: тот считает тот же алгоритм непрерывной
арифметикой float64 без пошаговых ROUND (см. ``core/excel_parity``).

Состав:
  * algorithm — адаптер к интерфейсу MineralAlgorithm (Calculator).

Реализация опирается на ``core/excel_port`` (формульный интерпретатор + VBA VM).
"""

from .algorithm import ExcelExactAlgorithm

__all__ = ["ExcelExactAlgorithm"]
