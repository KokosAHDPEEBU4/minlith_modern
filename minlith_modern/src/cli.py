"""MINLITH Modern — Command Line Interface.

Usage:
    python -m src calculate input.xlsx -o results.xlsx
    python -m src calculate input.xlsx --format pdf --template full
    python -m src info input.xlsx
    python -m src validate input.xlsx
    python -m src chart input.xlsx --type tas -o chart.png
    python -m src report input.xlsx --template standard -o report.pdf
    python -m src gui
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", nargs="+", help="Input file(s): .xlsx, .xls, .csv, .zip")
    parser.add_argument("--format", "-f", choices=["xlsx", "csv", "json", "pdf", "docx", "html"],
                        default=None, help="Output format (auto-detect from -o extension)")


def cmd_calculate(args: argparse.Namespace) -> int:
    """Calculate mineral composition from input file(s)."""
    from src.io.excel import load_samples, save_results, save_results_json, save_results_csv
    from src.io.csv_handler import read_csv
    from src.io.zip_handler import load_samples_from_zip
    from src.core.calculator import Calculator
    from src.database.engine import init_db
    from src.database.repository import SampleRepository

    init_db()
    calc = Calculator()
    all_results = []

    for input_path in args.input:
        p = Path(input_path)
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            continue

        if p.suffix.lower() == ".zip":
            samples = load_samples_from_zip(p)
        elif p.suffix.lower() == ".csv":
            samples = read_csv(p)
        else:
            samples = load_samples(p)

        if not samples:
            print(f"WARNING: No samples found in {p.name}", file=sys.stderr)
            continue

        print(f"Loaded {len(samples)} sample(s) from {p.name}")

        for sample in samples:
            try:
                result = calc.calculate_single(sample)
                all_results.append(result)
                print(f"  {sample.name:30s} -> {result.rock_type.name:8s} "
                      f"(F={result.coefficients.F:.3f}, Ab={result.minerals_weight.ab:.1f}%)")

                # Save to DB
                try:
                    repo = SampleRepository()
                    repo.save_result(result)
                except Exception:
                    pass
            except Exception as e:
                print(f"  ERROR: {sample.name}: {e}", file=sys.stderr)

    if not all_results:
        print("No results to export.", file=sys.stderr)
        return 1

    # Determine output path and format
    output_path = Path(args.output) if args.output else None
    fmt = args.format

    if output_path:
        fmt = fmt or output_path.suffix.lstrip(".")
    elif fmt is None:
        fmt = "xlsx"
        output_path = Path("minlith_results.xlsx")
    else:
        output_path = Path(f"minlith_results.{fmt}")

    # Export
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        save_results_csv(output_path, all_results)
    elif fmt == "json":
        save_results_json(output_path, all_results)
    elif fmt in ("pdf", "docx", "html"):
        _export_report(output_path, fmt, all_results, args.template)
    else:
        save_results(output_path, all_results)

    print(f"\nExported {len(all_results)} result(s) to {output_path}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show information about samples in file(s)."""
    from src.io.excel import load_samples
    from src.io.csv_handler import read_csv
    from src.io.zip_handler import load_samples_from_zip

    for input_path in args.input:
        p = Path(input_path)
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            continue

        if p.suffix.lower() == ".zip":
            samples = load_samples_from_zip(p)
        elif p.suffix.lower() == ".csv":
            samples = read_csv(p)
        else:
            samples = load_samples(p)

        print(f"\n{'='*60}")
        print(f"File: {p.name}")
        print(f"Samples: {len(samples)}")
        print(f"{'='*60}")

        for s in samples:
            comp = s.composition
            total = comp.sum()
            print(f"\n  {s.name}  (sum={total:.2f}%)")
            print(f"  {'-'*40}")
            for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o"]:
                val = getattr(comp, field, 0.0)
                if val > 0:
                    print(f"    {field:8s} = {val:.2f}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate input data without calculating."""
    from src.io.excel import load_samples
    from src.io.csv_handler import read_csv
    from src.io.zip_handler import load_samples_from_zip
    from src.core.validation import validate_sample
    from src.core.models import CalculationConfig

    config = CalculationConfig()
    errors = 0

    for input_path in args.input:
        p = Path(input_path)
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            errors += 1
            continue

        if p.suffix.lower() == ".zip":
            samples = load_samples_from_zip(p)
        elif p.suffix.lower() == ".csv":
            samples = read_csv(p)
        else:
            samples = load_samples(p)

        print(f"\nValidating: {p.name} ({len(samples)} samples)")

        for s in samples:
            is_valid, warnings = validate_sample(s.composition, config)
            status = "OK" if is_valid else "INVALID"
            total = s.composition.sum()

            if warnings or not is_valid:
                print(f"  {s.name:30s} [{status}] sum={total:.2f}%")
                for w in warnings:
                    print(f"    ⚠ {w}")
            else:
                print(f"  {s.name:30s} [OK] sum={total:.2f}%")

            if not is_valid:
                errors += 1

    print(f"\n{'Validation passed' if errors == 0 else f'{errors} error(s) found'}")
    return 0 if errors == 0 else 1


def cmd_chart(args: argparse.Namespace) -> int:
    """Generate a chart from input data."""
    from src.io.excel import load_samples
    from src.io.csv_handler import read_csv
    from src.io.zip_handler import load_samples_from_zip
    from src.core.calculator import Calculator
    from src.charts import BUILTIN_CHARTS, ChartData
    import numpy as np

    calc = Calculator()
    all_results = []

    for input_path in args.input:
        p = Path(input_path)
        if p.suffix.lower() == ".zip":
            samples = load_samples_from_zip(p)
        elif p.suffix.lower() == ".csv":
            samples = read_csv(p)
        else:
            samples = load_samples(p)
        for s in samples:
            all_results.append(calc.calculate_single(s))

    if not all_results:
        print("No data to chart.", file=sys.stderr)
        return 1

    # Build chart data
    data = ChartData(sample_names=[r.sample_name for r in all_results])
    for field in ["ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
                   "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl"]:
        data.minerals_wt[field] = np.array([getattr(r.minerals_weight, field, 0.0) for r in all_results])
    for field in ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno", "tio2"]:
        data.oxides[field] = np.array([getattr(r.input_composition, field, 0.0) for r in all_results])
    data.rock_types = [int(r.rock_type) for r in all_results]
    if all_results and all_results[0].defect:
        for oxide in all_results[0].defect:
            data.defect[oxide] = np.array([r.defect.get(oxide, 0.0) for r in all_results])

    # Find chart
    chart = None
    for c in BUILTIN_CHARTS:
        if args.type.lower() in c.get_name().lower():
            chart = c
            break
    if not chart:
        print(f"Unknown chart type: {args.type}", file=sys.stderr)
        print("Available: " + ", ".join(c.get_name().lower() for c in BUILTIN_CHARTS))
        return 1

    output = Path(args.output) if args.output else Path(f"{chart.get_name().lower().replace(' ', '_')}.png")
    chart.export(data, output, dpi=args.dpi)
    print(f"Chart exported: {output}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate a report from input data."""
    from src.io.excel import load_samples
    from src.io.csv_handler import read_csv
    from src.io.zip_handler import load_samples_from_zip
    from src.core.calculator import Calculator
    from src.reports.template_builder import PREDEFINED_TEMPLATES

    calc = Calculator()
    all_results = []

    for input_path in args.input:
        p = Path(input_path)
        if p.suffix.lower() == ".zip":
            samples = load_samples_from_zip(p)
        elif p.suffix.lower() == ".csv":
            samples = read_csv(p)
        else:
            samples = load_samples(p)
        for s in samples:
            all_results.append(calc.calculate_single(s))

    if not all_results:
        print("No data for report.", file=sys.stderr)
        return 1

    fmt = args.format or Path(args.output).suffix.lstrip(".") if args.output else "pdf"
    output = Path(args.output) if args.output else Path(f"minlith_report.{fmt}")

    template = PREDEFINED_TEMPLATES.get(args.template, PREDEFINED_TEMPLATES["standard"])()

    _export_report(output, fmt, all_results, args.template)
    print(f"Report exported: {output}")
    return 0


def _export_report(path: Path, fmt: str, results: list, template_name: str = "standard") -> None:
    from src.reports.template_builder import PREDEFINED_TEMPLATES
    template = PREDEFINED_TEMPLATES.get(template_name, PREDEFINED_TEMPLATES["standard"])()

    if fmt == "pdf":
        from src.reports.pdf_generator import PDFGenerator
        PDFGenerator(results).generate(path, template)
    elif fmt == "docx":
        from src.reports.word_generator import WordGenerator
        WordGenerator(results).generate(path, template)
    elif fmt == "html":
        from src.reports.html_generator import HTMLGenerator
        HTMLGenerator(results).generate(path, template)


def cmd_gui(args: argparse.Namespace) -> int:
    """Launch the GUI application."""
    from src.main import main
    main()
    return 0


def main_cli() -> int:
    # Fix Windows console encoding
    import io
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="minlith",
        description="MINLITH Modern — Normative Mineralogical Calculation",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # calculate
    p_calc = subparsers.add_parser("calculate", aliases=["calc", "c"],
                                    help="Calculate mineral composition")
    _add_common_args(p_calc)
    p_calc.add_argument("-o", "--output", help="Output file path")
    p_calc.add_argument("--template", "-t", choices=["brief", "standard", "full"],
                        default="standard", help="Report template (for pdf/docx/html)")
    p_calc.set_defaults(func=cmd_calculate)

    # info
    p_info = subparsers.add_parser("info", aliases=["i"],
                                    help="Show file information")
    p_info.add_argument("input", nargs="+", help="Input file(s)")
    p_info.set_defaults(func=cmd_info)

    # validate
    p_val = subparsers.add_parser("validate", aliases=["v"],
                                   help="Validate input data")
    p_val.add_argument("input", nargs="+", help="Input file(s)")
    p_val.set_defaults(func=cmd_validate)

    # chart
    p_chart = subparsers.add_parser("chart", aliases=["ch"],
                                     help="Generate a chart")
    _add_common_args(p_chart)
    p_chart.add_argument("-o", "--output", help="Output file path")
    p_chart.add_argument("--type", "-T", default="bar",
                         help="Chart type: bar, pie, qapf, tas, acnk, defect, heatmap, feldspar, "
                              "harker, afm, sio2_k2o, bland_altman, correlation")
    p_chart.add_argument("--dpi", type=int, default=150, help="Image DPI")
    p_chart.set_defaults(func=cmd_chart)

    # report
    p_report = subparsers.add_parser("report", aliases=["r"],
                                      help="Generate a report")
    _add_common_args(p_report)
    p_report.add_argument("-o", "--output", help="Output file path")
    p_report.add_argument("--template", "-t", choices=["brief", "standard", "full"],
                          default="standard")
    p_report.set_defaults(func=cmd_report)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch GUI application")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main_cli())
