"""Сравнение двух Excel-движков «бок о бок»: excel_parity vs excel_exact.

``excel_parity`` считает те же формулы без пошаговых ROUND (float64),
``excel_exact`` — полная копия Excel с ROUND. Функция возвращает
по-минеральные (ф.е.) значения обоих движков и их разность.

Модуль прикладной (не Qt); используется GUI-диалогом сравнения движков.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.excel_parity.runner import run_sample as parity_run
from src.core.excel_port.runner import run_sample as exact_run

# (русское имя, ключ ф.е. в наборе имён обоих движков)
MINERAL_ORDER: list[tuple[str, str]] = [
    ("Альбит", "ab"), ("Анортит", "an"), ("Ортоклаз", "or"),
    ("Иллит", "ill"), ("Хлорит", "chl"), ("Каолинит", "kn"),
    ("Монтмориллонит", "mm"), ("Гиббсит", "gb"), ("Кварц", "q"),
    ("Доломит", "dl"), ("Анкерит", "ank"), ("Кальцит", "cc"),
    ("Родохрозит", "rch"), ("Сидерит", "sd"), ("Серпентин", "srp"),
    ("Магнезит", "mst"), ("Гематит", "ht"), ("Пиролюзит", "prl"),
]


@dataclass(frozen=True)
class MineralDiff:
    """Разность одного минерала (ф.е.) между движками."""

    name: str
    parity: float
    exact: float
    delta: float


def _num(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def compare_engines(
    oxide_wt: dict[str, float],
    data_dir: Path | None = None,
) -> list[MineralDiff]:
    """По-минеральное сравнение ``excel_parity`` и ``excel_exact`` (ф.е.).

    ``oxide_wt`` — весовые проценты с Excel-ключами ("SiO2", …).
    """
    parity = parity_run(oxide_wt, data_dir=data_dir).names
    exact = exact_run(oxide_wt, data_dir=data_dir, rounding=True)
    rows: list[MineralDiff] = []
    for name, key in MINERAL_ORDER:
        p = _num(parity.get(key))
        e = _num(exact.get(key))
        rows.append(MineralDiff(name=name, parity=p, exact=e, delta=p - e))
    return rows


def max_abs_delta(rows: list[MineralDiff]) -> tuple[float, str]:
    """Максимальное |delta| и имя минерала (для сводки)."""
    if not rows:
        return 0.0, ""
    worst = max(rows, key=lambda r: abs(r.delta))
    return abs(worst.delta), worst.name


def compare_all(
    compositions: dict[str, dict[str, float]],
    data_dir: Path | None = None,
) -> list[tuple[str, list[MineralDiff]]]:
    """Сравнить движки по нескольким образцам: ``[(имя, строки), …]``."""
    return [(name, compare_engines(ox, data_dir=data_dir))
            for name, ox in compositions.items()]


def summary_rows(
    compositions: dict[str, dict[str, float]],
    data_dir: Path | None = None,
) -> list[tuple[str, float, str]]:
    """Сводка: ``(имя, max|Δ|, минерал с максимальным |Δ|)`` по образцам."""
    out: list[tuple[str, float, str]] = []
    for name, rows in compare_all(compositions, data_dir=data_dir):
        worst, worst_name = max_abs_delta(rows)
        out.append((name, worst, worst_name))
    return out


def to_csv(
    compositions: dict[str, dict[str, float]],
    data_dir: Path | None = None,
) -> str:
    """CSV-отчёт по всем образцам: sample,mineral,parity,exact,delta."""
    lines = ["sample,mineral,excel_parity,excel_exact,delta"]
    for name, rows in compare_all(compositions, data_dir=data_dir):
        for row in rows:
            lines.append(f"{name},{row.name},{row.parity:.6g},"
                         f"{row.exact:.6g},{row.delta:.6g}")
    return "\n".join(lines)
