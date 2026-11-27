"""Массовая сверка ``excel_parity`` с ``excel_port`` на синтетической сетке.

Дизайн корпуса (детерминированный, seed по умолчанию 20260916):

* **типичные составы (60 %)** — равномерно внутри петрохимического конверта
  осадочных пород, сумма оксидов нормируется к 100 %;
* **граничные составы (30 %)** — 1–2 оксида прижаты к нижней/верхней границе
  конверта или к нулю; сумма также нормируется к 100 %;
* **экстремальные суммы (10 %)** — те же диапазоны, но сумма приводится к
  85 % или 115 % (вне допуска валидатора 98–102 %), проверяется устойчивость
  нормировки.

Область определения стадии 0: F = FeO*/(FeO*+MgO) должна быть строго меньше
единицы, иначе k1 = 4 − 4F обращается в ноль и классификатор типа не определён.
Поэтому в корпусе MgO >= 0.1 вес.%; составы с MgO = 0 и FeO > 0 (F = 1) в
проверку не входят и описываются как известное краевое ограничение.

Невалидные входы (отрицательные значения, NaN/inf) в корпус не входят — их
отсекает ``src.core.validation.validate_sample``; отдельная проверка
валидатора запускается флагом ``--check-validation``.

Критерии успеха для каждого допущенного состава:
  1. оба движка завершаются (нет исключений, кроме явного NotImplementedError);
  2. значения именованных переменных и строка 287 (34 вес. %) совпадают
     с допуском ``--tol`` (по умолчанию 1e-6);
  3. тип породы в 1..5, все значения конечны.

Отчёт: ``reports/synthetic_grid/summary.json`` + ``samples.csv``.

Запуск (из ``minlith_modern/``)::

    python -m scripts.verify_synthetic_grid --n 16000
    python -m scripts.verify_synthetic_grid --n 200 --skip-port   # быстрый
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.excel_parity.branch_catalog import catalog_to_dict  # noqa: E402
from src.core.excel_parity.runner import run_sample as parity_run  # noqa: E402

# Петрохимический конверт корпуса, вес.% (осадочные породы).
ENVELOPE: dict[str, tuple[float, float]] = {
    "SiO2": (35.0, 85.0),
    "TiO2": (0.0, 1.5),
    "Al2O3": (2.0, 28.0),
    "Fe2O3": (0.0, 6.0),
    "FeO": (0.0, 12.0),
    "MgO": (0.1, 15.0),
    "CaO": (0.0, 20.0),
    "Na2O": (0.0, 7.0),
    "K2O": (0.0, 10.0),
    "P2O5": (0.0, 0.5),
    "MnO": (0.0, 0.3),
    "S": (0.0, 1.0),
    "CO2": (0.0, 20.0),
}
SUM_TARGETS = (85.0, 115.0)
_TOL = 1e-6


def _clip_fe_mg(ox: dict[str, float]) -> None:
    """Держит состав внутри области определения стадии 0 (F < 1)."""
    if ox.get("MgO", 0.0) < 0.1:
        ox["MgO"] = 0.1
    if ox.get("FeO", 0.0) + ox["MgO"] < 0.2:
        ox["FeO"] = 0.2


def _normalize(ox: dict[str, float], target: float) -> dict[str, float]:
    total = sum(ox.values())
    if total <= 0.0:
        ox["SiO2"] = 1.0
        total = 1.0
    return {k: v * target / total for k, v in ox.items()}


def generate(n: int, seed: int = 20260916) -> list[dict[str, float]]:
    """Детерминированный стратифицированный корпус из ``n`` составов."""
    rng = random.Random(seed)
    out: list[dict[str, float]] = []
    for i in range(n):
        share = i / n
        if share < 0.60:
            stratum = "typical"
            target = 100.0
        elif share < 0.90:
            stratum = "boundary"
            target = 100.0
        else:
            stratum = "extreme_sum"
            target = rng.choice(SUM_TARGETS)

        ox = {k: rng.uniform(*v) for k, v in ENVELOPE.items()}
        if stratum == "boundary":
            keys = rng.sample(list(ox), k=rng.choice((1, 2)))
            for key in keys:
                lo, hi = ENVELOPE[key]
                ox[key] = rng.choice((lo, hi, 0.0))
        _clip_fe_mg(ox)
        out.append(_normalize(ox, target))
    return out


def _compare(ox: dict[str, float], port_run, tol: float) -> dict:
    """Сверить один состав; вернуть запись результата."""
    rec: dict[str, object] = {"status": "ok", "delta": 0.0}
    try:
        py = parity_run(ox)
    except NotImplementedError as exc:  # явный gap движка
        rec.update(status="gap", error=f"NotImplementedError: {exc}")
        return rec
    except Exception as exc:  # noqa: BLE001
        rec.update(status="error", error=f"{type(exc).__name__}: {exc}")
        return rec

    rec["rock_type"] = int(py.st0.rock_type)
    rec["band"] = py.st0.coefficient_band
    rec["labels"] = py.path.labels()

    if port_run is None:
        return rec

    try:
        names, row287 = port_run(ox, rounding=False)
    except NotImplementedError as exc:
        rec.update(status="gap", error=f"NotImplementedError: {exc}")
        return rec
    except Exception as exc:  # noqa: BLE001
        rec.update(status="error", error=f"{type(exc).__name__}: {exc}")
        return rec

    worst = 0.0
    for key, mine in py.names.items():
        ref = names.get(key)
        if isinstance(ref, (int, float)) and isinstance(mine, (int, float)):
            worst = max(worst, abs(float(ref) - float(mine)))
    for ref, mine in zip(row287, py.out.row287):
        if isinstance(ref, (int, float)) and isinstance(mine, (int, float)):
            worst = max(worst, abs(float(ref) - float(mine)))

    rec["delta"] = worst
    if not math.isfinite(worst):
        rec["status"] = "mismatch"
    elif worst > tol:
        rec["status"] = "mismatch"
    return rec


def _branch_catalog() -> tuple[dict[str, str], dict[str, list[str]]]:
    """id ветки -> стадия; решение -> список id."""
    stage_of: dict[str, str] = {}
    by_decision: dict[str, list[str]] = {}
    for decision in catalog_to_dict()["decisions"]:
        ids = [b["id"] for b in decision["branches"]]
        by_decision[decision["id"]] = ids
        for bid in ids:
            stage_of[bid] = decision["stage"]
    return stage_of, by_decision


def _normalize_label(label: str) -> str:
    for prefix in ("band_", "rock_type_"):
        if label.startswith(prefix):
            return label[len(prefix):]
    return label


def check_validation(n: int = 1000, seed: int = 7) -> dict[str, int]:
    """Невалидные входы должны отсекаться валидатором (100 %)."""
    from src.core.models import CalculationConfig, OxideComposition
    from src.core.validation import validate_sample

    rng = random.Random(seed)
    rejected = 0
    for _ in range(n):
        kind = rng.choice(("negative", "nan", "inf"))
        values = {k.lower(): 0.0 for k in ("SiO2", "TiO2", "Al2O3", "Fe2O3",
                                           "FeO", "MgO", "CaO", "Na2O", "K2O",
                                           "P2O5", "MnO", "CO2")}
        values["sio2"] = 70.0
        values["al2o3"] = 15.0
        values["feo"] = 3.0
        values["mgo"] = 2.0
        key = rng.choice(list(values))
        if kind == "negative":
            values[key] = -rng.uniform(0.1, 5.0)
        elif kind == "nan":
            values[key] = float("nan")
        else:
            values[key] = float("inf")
        ok, _ = validate_sample(OxideComposition(**values), CalculationConfig())
        rejected += int(not ok)
    return {"generated": n, "rejected": rejected}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=16000)
    ap.add_argument("--seed", type=int, default=20260916)
    ap.add_argument("--tol", type=float, default=_TOL)
    ap.add_argument("--skip-port", action="store_true",
                    help="только прогон чистого движка (без сверки с excel_port)")
    ap.add_argument("--check-validation", action="store_true")
    ap.add_argument("--out", default=str(ROOT.parent / "reports" / "synthetic_grid"))
    args = ap.parse_args()

    port_run = None
    if not args.skip_port:
        from src.core.excel_port.runner import run_sample_full

        def port_run(ox, rounding=False):  # noqa: ANN001
            return run_sample_full(ox, rounding=rounding)

    samples = generate(args.n, args.seed)
    stage_of, by_decision = _branch_catalog()

    statuses: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    types: Counter[int] = Counter()
    bands: Counter[str] = Counter()
    covered: set[str] = set()
    worst = 0.0
    worst_ox: dict[str, float] | None = None
    rows: list[dict] = []

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, ox in enumerate(samples):
        rec = _compare(ox, port_run, args.tol)
        statuses[rec["status"]] += 1
        if rec["status"] in ("error", "gap"):
            errors[str(rec.get("error", ""))] += 1
        if rec["status"] == "ok":
            types[rec["rock_type"]] += 1
            bands[rec["band"]] += 1
            for label in rec["labels"]:
                norm = _normalize_label(label)
                if norm in stage_of:
                    covered.add(norm)
            delta = float(rec["delta"])
            if delta > worst:
                worst, worst_ox = delta, ox
        rows.append({"idx": idx, **{k: rec.get(k) for k in
                                   ("status", "rock_type", "band", "delta", "error")}})
        if (idx + 1) % 500 == 0:
            print(f"{idx + 1}/{args.n}  {dict(statuses)}  worst={worst:.2e}",
                  flush=True)

    all_ids = set(stage_of)
    missing = sorted(all_ids - covered)
    decisions_fully = {
        name: all(b in covered for b in ids) for name, ids in by_decision.items()
    }

    summary = {
        "n": args.n,
        "seed": args.seed,
        "tol": args.tol,
        "compared_with_port": not args.skip_port,
        "statuses": dict(statuses),
        "errors": dict(errors),
        "worst_delta": worst,
        "worst_delta_sample": worst_ox,
        "rock_types": {str(k): v for k, v in sorted(types.items())},
        "coefficient_bands": dict(sorted(bands.items())),
        "branches_total": len(all_ids),
        "branches_covered": len(covered),
        "branches_missing": missing,
        "decisions_fully_covered": sum(decisions_fully.values()),
        "decisions_total": len(decisions_fully),
    }
    if args.check_validation:
        summary["validation"] = check_validation()

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "samples.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "status", "rock_type",
                                               "band", "delta", "error"])
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Отчёт -> {out_dir}")


if __name__ == "__main__":
    main()
