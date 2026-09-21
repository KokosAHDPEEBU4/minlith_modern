"""Сравнение «как в Excel» (с округлениями) и «чистого» режима (без).

Phase 4: как сильно накапливается ошибка округления по цепочке вычислений
VBA MINLITH. Для каждого образца прогоняем оба режима и по порядку
присваивания именованных переменных строим |error|.

Продукты:
  * CSV-таблица расхождений по переменным
  * (опционально) график роста ошибки matplotlib -> PNG
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from src.core.excel_port.runner import run_sample

SKIP_NAMES = {"n_1", "n_2", "n_3"}


@dataclass
class SampleResult:
    name: str
    errors: list[tuple[float, str, object, object]]  # (|d|, name, round, full)
    assignments: list[str]                          # порядок присваивания


def compare_sample(name: str, composition: dict[str, float]) -> SampleResult:
    a = run_sample(composition, rounding=True)
    b = run_sample(composition, rounding=False)
    order = a.get("_assignments") or b.get("_assignments") or []
    errors: list[tuple[float, str, object, object]] = []
    for v in order:
        if v in SKIP_NAMES or v not in a or v not in b:
            continue
        try:
            delta = abs(float(a[v]) - float(b[v]))
        except (TypeError, ValueError):
            continue
        if delta > 1e-9:
            errors.append((delta, v, a[v], b[v]))
    errors.sort(reverse=True)
    return SampleResult(name, errors, order)


def compare_all(samples: dict[str, dict[str, float]]) -> list[SampleResult]:
    return [compare_sample(name, comp) for name, comp in samples.items()]


def write_csv(results: list[SampleResult], out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample", "variable", "err_abs", "value_excel_round", "value_full_precision"])
        for r in results:
            for d, v, av, bv in r.errors:
                w.writerow([r.name, v, f"{d:.6g}", f"{av:.12g}", f"{bv:.12g}"])


def plot_growth(results: list[SampleResult], out: Path | None = None) -> None:
    """График накопления ошибки по порядку присваивания переменных."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.ravel()
    for ax, r in zip(axes, results):
        by_var = {v: d for d, v, _, _ in r.errors}
        xs = [i for i, v in enumerate(r.assignments) if v in by_var
              or v not in SKIP_NAMES]
        ys = [by_var.get(r.assignments[i], 0.0) for i in xs]
        ax.plot(xs, ys, "o-", ms=3, lw=1)
        ax.set_yscale("log")
        ax.set_title(r.name)
        ax.set_xlabel("порядок присваивания")
        ax.set_ylabel("|err| (ф.е.)")
        ax.grid(True, which="both", alpha=0.3)
    for ax in axes[len(results):]:
        ax.axis("off")
    fig.suptitle("Рост ошибки округления: Excel (ROUND) vs полная точность")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=140)
        plt.close(fig)  # backend Agg — окно не показываем
    else:
        plt.show()


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    samples = json.loads((data_dir / "samples.json").read_text(encoding="utf-8"))
    multi = json.loads((data_dir / "reference_multi.json").read_text(encoding="utf-8"))
    comps: dict[str, dict[str, float]] = {
        "BK-1": samples["BK-1"],
        "T-O2": samples["T-O2"],
    }
    for k, v in multi.items():
        comps[k] = v["input"]

    results = compare_all(comps)
    out = data_dir / "compare_round_vs_full.csv"
    write_csv(results, out)
    print(f"CSV -> {out}")
    for r in results:
        print(f"{r.name:14s} отличий={len(r.errors):3d}  "
              f"max=|d|={r.errors[0][0]:.4g} ({r.errors[0][1]})")
    plot_growth(results, out.with_suffix(".png"))


if __name__ == "__main__":
    main()
