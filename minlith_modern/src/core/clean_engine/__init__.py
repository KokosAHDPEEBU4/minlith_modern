"""clean_engine — чистый (без округлений) Python-порт алгоритма MINLITH.

Фаза 3. В отличие от ``excel_port`` движок не воспроизводит пошаговые
округления книги Excel (ROUND …), а считает те же формулы непрерывной
арифметикой float64. Каждая стадия — явная читаемая функция.

Сравнение с ``excel_port(run_sample(rounding=False))`` показывает, где
исходная книга накапливает ошибку округления (см. Phase 4 / compare.py).

Состав:
  * stage0    — формульные единицы, F/A, коэффициенты k1..k4, классификация;
  * types     — стадии типов 1-5 (плагиоклаз, иллит, хлорит, mm, kn, остатки);
  * stage_vi  — распределение Ca/Mg/Fe/Mn по карбонатам и оксидам;
  * output    — вес.%, нормировка, дефект, строка 287;
  * runner    — оркестратор: оксиды -> результат.
"""

from .runner import CleanRun, run_sample
from .stage0 import DEFAULT_OXIDES, Stage0

__all__ = ["run_sample", "CleanRun", "Stage0", "DEFAULT_OXIDES"]
