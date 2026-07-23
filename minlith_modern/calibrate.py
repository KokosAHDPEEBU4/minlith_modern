#!/usr/bin/env python3
"""Calibrate algorithm parameters from MINLITH Excel output.

Usage:
    python calibrate.py MINLITH1.xlsx
    python calibrate.py MINLITH1.xlsx -o calibration_config.json
    python calibrate.py MINLITH1.xlsx --maxiter 2000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="calibrate",
        description="Auto-calibrate algorithm from MINLITH Excel output",
    )
    parser.add_argument("input", help="Path to MINLITH1.xlsx (or similar)")
    parser.add_argument(
        "-o", "--output",
        default="calibration_config.json",
        help="Output path for calibrated config (default: calibration_config.json)",
    )
    parser.add_argument(
        "--maxiter", type=int, default=1000,
        help="Max optimization iterations (default: 1000)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--sheet", default="Нач+Type 12",
        help="Excel sheet name with expected output (default: Нач+Type 12)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ОШИБКА: Файл не найден: {input_path}", file=sys.stderr)
        return 1

    # Fix Windows console encoding
    import io
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    print(f"Загрузка данных из {input_path.name}...")
    print(f"  Лист: {args.sheet}")

    from src.core.calibrator import (
        Calibrator,
        read_expected_from_excel,
        save_calibration_config,
    )

    try:
        sample, expected = read_expected_from_excel(input_path, args.sheet)
    except Exception as e:
        print(f"ОШИБКА при чтении Excel: {e}", file=sys.stderr)
        return 1

    print(f"  Образец: {sample.name}")
    print(f"  Ожидаемые минералы: {len(expected)}")
    for mineral, val in sorted(expected.items()):
        print(f"    {mineral:8s} = {val:.2f}%")

    print(f"\nЗапуск калибровки (maxiter={args.maxiter})...")
    calibrator = Calibrator(sample, expected)
    result = calibrator.calibrate(maxiter=args.maxiter, seed=args.seed)

    print(result.report)

    # Save config
    output_path = Path(args.output)
    save_calibration_config(result.params, output_path)
    print(f"Конфигурация сохранена: {output_path}")

    # Validation
    print("\nВалидация:")
    for mineral in ["ab", "an", "or_", "q", "ill", "chl", "kn"]:
        exp = result.expected.get(mineral, 0)
        cal = result.calibrated_output.get(mineral, 0)
        err = abs(cal - exp)
        status = "OK" if err < 0.1 else "ОШИБКА"
        print(f"  {mineral:8s}: expected={exp:7.2f}  calibrated={cal:7.2f}  Δ={err:.4f}  [{status}]")

    if result.rmse_after < 0.1:
        print(f"\n✓ Калибровка успешна! RMSE: {result.rmse_before:.4f} → {result.rmse_after:.4f}")
    else:
        print(f"\n⚠ Калибровка не сошлась. RMSE: {result.rmse_before:.4f} → {result.rmse_after:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
