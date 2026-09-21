"""Auto-calibrator — reverse-engineers the VBA algorithm via optimization.

Uses scipy.optimize.differential_evolution to find algorithm parameters
that make the stub output match the expected Excel output.

Usage:
    from src.core.calibrator import Calibrator, read_expected_from_excel
    sample, expected = read_expected_from_excel(Path("MINLITH1.xlsx"))
    calibrator = Calibrator(sample, expected)
    result = calibrator.calibrate()
    print(result.report)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

from src.core.algorithm import AlgorithmInput, AlgorithmOutput
from src.core.calculator import Calculator
from src.core.models import (
    CalculationConfig,
    OxideComposition,
    Sample,
)

logger = logging.getLogger(__name__)

# Expected mineral fields in the output
EXPECTED_MINERALS = [
    "ab", "an", "or_", "q", "ill", "chl", "kn", "mm", "gb",
    "ap", "cc", "dl", "ank", "rch", "sd", "srp", "mst", "ht", "prl",
]

# Weights for cost function (major minerals weighted higher)
MINERAL_WEIGHTS = {
    "ab": 2.0, "an": 1.0, "or_": 2.0, "q": 3.0,
    "ill": 3.0, "chl": 3.0, "kn": 1.5, "mm": 0.5, "gb": 0.5,
    "ap": 1.0, "cc": 0.5, "dl": 1.0, "ank": 0.5, "rch": 0.5,
    "sd": 0.5, "srp": 1.0, "mst": 0.5, "ht": 0.5, "prl": 0.5,
}

# Parameter bounds for optimization
PARAM_BOUNDS = {
    "ab_scale": (0.5, 2.0),
    "an_ca_ratio": (0.0, 2.0),
    "chl_mg_k1": (0.1, 5.0),
    "ill_k_consumption": (0.5, 4.0),
    "ill_al_ratio": (2.0, 12.0),
    "ill_si_ratio": (3.0, 25.0),
    "kn_al_ratio": (0.3, 3.0),
    "dl_ca_ratio": (0.0, 2.0),
    "ht_feo_ratio": (0.0, 1.0),
    "srp_mg_ratio": (0.0, 1.0),
    "chl_fe_ratio": (0.0, 3.0),
    "ill_fe_ratio": (0.0, 3.0),
}

# Default parameters (matches stub algorithm)
DEFAULT_PARAMS = {
    "ab_scale": 1.0,
    "an_ca_ratio": 1.0,
    "chl_mg_k1": 1.0,
    "ill_k_consumption": 2.0,
    "ill_al_ratio": 6.5,
    "ill_si_ratio": 16.0,
    "kn_al_ratio": 1.0,
    "dl_ca_ratio": 1.0,
    "ht_feo_ratio": 0.5,
    "srp_mg_ratio": 0.0,
    "chl_fe_ratio": 1.0,
    "ill_fe_ratio": 1.0,
}


@dataclass
class CalibrationResult:
    """Result of the calibration process."""

    sample_name: str
    expected: dict[str, float]
    stub_output: dict[str, float]
    calibrated_output: dict[str, float]
    params: dict[str, float]
    rmse_before: float
    rmse_after: float
    report: str = ""
    convergence: bool = True


def read_expected_from_excel(
    path: Path, sheet_name: str = "Нач+Type 12"
) -> tuple[Sample, dict[str, float]]:
    """Read input data and expected mineral output from Excel sheet.

    The sheet layout:
      - Row 1: headers (sample name in B1)
      - Rows 2-19: oxide labels (col A) + values (col B)
      - Rows 146-154: mineral output headers + values (normalized wt%)
      - Row 287: summary table with final values

    Returns:
        (Sample, expected_dict) where expected_dict maps mineral codes to wt%
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)

    if sheet_name not in wb.sheetnames:
        # Try fallback sheets
        for fallback in ["Нач+Type 3", "Нач+Type 12"]:
            if fallback in wb.sheetnames:
                sheet_name = fallback
                break
        else:
            raise ValueError(f"Sheet '{sheet_name}' not found in {path}")

    ws = wb[sheet_name]

    # Read sample name from B1
    sample_name = str(ws["B1"].value or "Unknown")

    # Read oxide input from rows 2-19, column B
    oxide_map = {
        2: "sio2", 3: "tio2", 4: "al2o3", 5: "fe2o3", 6: "feo",
        7: "mgo", 8: "cao", 9: "na2o", 10: "k2o", 11: "p2o5",
        12: "mno", 13: "c", 14: "so3", 15: "f", 16: "cl",
        17: "s", 18: "co2", 19: "so",
    }
    oxide_values = {}
    for row, field in oxide_map.items():
        val = ws.cell(row=row, column=2).value
        oxide_values[field] = float(val) if val is not None else 0.0

    sample = Sample(
        name=sample_name,
        composition=OxideComposition(**oxide_values),
    )

    # Read expected mineral output from row 287 (summary table)
    # Layout: B287=summa, C287=summa, D287=Ab, E287=An, F287=Pl, G287=Or,
    #         H287=Q, I287=Mm, J287=Ill, K287=Chl, L287=Gb, M287=Kn,
    #         N287=Ap, O287=C, P287=Cc, Q287=Dl, R287=Ank, S287=Rch,
    #         T287=Sd, U287=Srp, V287=Mst, W287=Ht, X287=Prl,
    #         Y287=Pr, Z287=Rt, AA287=Hl, AB287=Gy, AC287=Fl
    mineral_col_map = {
        "D": "ab", "E": "an", "G": "or_", "H": "q",
        "I": "mm", "J": "ill", "K": "chl", "L": "gb", "M": "kn",
        "N": "ap", "P": "cc", "Q": "dl", "R": "ank", "S": "rch",
        "T": "sd", "U": "srp", "V": "mst", "W": "ht", "X": "prl",
    }

    expected = {}
    for col_letter, mineral in mineral_col_map.items():
        cell_val = ws[f"{col_letter}287"].value
        if cell_val is not None:
            try:
                expected[mineral] = float(cell_val)
            except (ValueError, TypeError):
                expected[mineral] = 0.0

    # Also try row 153 (normalized values) as fallback
    if not expected:
        for col_letter, mineral in mineral_col_map.items():
            cell_val = ws[f"{col_letter}153"].value
            if cell_val is not None:
                try:
                    expected[mineral] = float(cell_val)
                except (ValueError, TypeError):
                    expected[mineral] = 0.0

    wb.close()
    logger.info("Read expected output for '%s': %d minerals", sample_name, len(expected))
    return sample, expected


class ParameterizedAlgorithm:
    """Algorithm with adjustable parameters for calibration."""

    def __init__(self, params: dict[str, float]) -> None:
        self.p = params

    def compute(self, inp: AlgorithmInput) -> AlgorithmOutput:
        """Run parameterized calculation."""
        out = AlgorithmOutput()

        # Stage I: Feldspars
        out.Ab = self.p["ab_scale"] * inp.na2o
        out.An = self.p["an_ca_ratio"] * max(inp.cao, 0.0)

        # Stage II: Remaining Al, Si after feldspars
        al1 = inp.al2o3 - out.Ab - out.An
        si1 = inp.sio2 - 6 * out.Ab - 2 * out.An

        # Stage III: Chlorite (uses Mg, Fe via k1-k4)
        k1 = inp.k1 if inp.k1 > 0 else 1e-10
        chl_mg = inp.mgo / (self.p["chl_mg_k1"] * k1)
        chl_fe = self.p["chl_fe_ratio"] * inp.feo / (self.p["chl_mg_k1"] * k1) if k1 > 0 else 0
        out.Chl = chl_mg + chl_fe

        # Illite (uses K, Al, Si, and optionally Fe)
        ill_mg = inp.mgo - k1 * out.Chl
        ill_fe = self.p["ill_fe_ratio"] * inp.feo
        if ill_mg > 0 or ill_fe > 0:
            out.Ill = ill_mg + ill_fe * 0.1  # Small Fe contribution
        else:
            out.Ill = 0.0

        # Orthoclase (K remaining after illite)
        out.Or = max(inp.k2o - self.p["ill_k_consumption"] * out.Ill, 0.0)

        # Kaolinite from remaining Al
        remaining_al = al1 - self.p["ill_al_ratio"] * out.Ill - out.Or
        if remaining_al > 0:
            out.Kn = self.p["kn_al_ratio"] * remaining_al
        else:
            out.Kn = remaining_al  # Keep negative if Al deficit

        # Gibbsite from any leftover Al
        kn_effective = out.Kn / self.p["kn_al_ratio"] if self.p["kn_al_ratio"] > 0 else 0
        remaining_al2 = remaining_al - kn_effective
        if remaining_al2 > 0:
            out.Gb = remaining_al2

        # Quartz = remaining Si
        remaining_si = si1 - self.p["ill_si_ratio"] * out.Ill - 6 * out.Or - 2 * out.Kn
        out.Q = max(remaining_si, 0.0)

        # Stage VI: Carbonates
        remaining_ca = inp.cao - out.An
        if remaining_ca > 0 and inp.mgo > 0:
            out.Dl = self.p["dl_ca_ratio"] * min(remaining_ca, inp.mgo)

        # Hematite from Fe (parameterized — can be 0)
        out.Ht = self.p["ht_feo_ratio"] * inp.feo / 2

        # Serpentine from Mg (parameterized — can be > 0)
        out.Srp = self.p["srp_mg_ratio"] * inp.mgo

        # Pyrolusite from Mn
        out.Prl = inp.mno

        # Montmorillonite (simplified)
        out.Mm = 0.0

        return out


class Calibrator:
    """Calibrate algorithm parameters to match expected Excel output."""

    def __init__(
        self,
        input_sample: Sample,
        expected: dict[str, float],
        config: CalculationConfig | None = None,
    ) -> None:
        self.sample = input_sample
        self.expected = expected
        self.config = config or CalculationConfig(timeout_seconds=30)
        self._param_names = list(PARAM_BOUNDS.keys())
        self._bounds = [PARAM_BOUNDS[k] for k in self._param_names]

    def _params_from_array(self, x: np.ndarray) -> dict[str, float]:
        """Convert optimizer array to parameter dict."""
        return {name: float(val) for name, val in zip(self._param_names, x)}

    def _run_with_params(self, params: dict[str, float]) -> dict[str, float]:
        """Run calculator with parameterized algorithm, return mineral wt%."""
        algorithm = ParameterizedAlgorithm(params)
        calc = Calculator(config=self.config, algorithm=algorithm)
        result = calc.calculate_single(self.sample)

        # Extract mineral weights as dict
        output = {}
        for mineral in EXPECTED_MINERALS:
            output[mineral] = getattr(result.minerals_weight, mineral, 0.0)
        return output

    def _cost_function(self, x: np.ndarray) -> float:
        """Compute weighted RMSE between stub and expected output."""
        params = self._params_from_array(x)

        try:
            output = self._run_with_params(params)
        except Exception as e:
            logger.warning("Calculation failed with params %s: %s", params, e)
            return 1e6  # Large penalty for failed calculations

        # Weighted RMSE
        total_error = 0.0
        total_weight = 0.0
        for mineral, expected_val in self.expected.items():
            if mineral not in output:
                continue
            weight = MINERAL_WEIGHTS.get(mineral, 1.0)
            diff = output[mineral] - expected_val
            total_error += weight * diff ** 2
            total_weight += weight

        if total_weight == 0:
            return 1e6

        return float(np.sqrt(total_error / total_weight))

    def calibrate(self, maxiter: int = 1000, seed: int = 42) -> CalibrationResult:
        """Run differential_evolution to find optimal parameters."""
        logger.info("Starting calibration for '%s'...", self.sample.name)

        # Get stub output (baseline)
        stub_params = dict(DEFAULT_PARAMS)
        stub_output = self._run_with_params(stub_params)
        rmse_before = self._cost_function(
            np.array([stub_params[k] for k in self._param_names])
        )
        logger.info("Stub RMSE before calibration: %.4f", rmse_before)

        # Run optimization
        result = differential_evolution(
            self._cost_function,
            bounds=self._bounds,
            maxiter=maxiter,
            seed=seed,
            tol=1e-8,
            polish=True,
            workers=1,  # Single-threaded for Windows compatibility
        )

        # Extract optimized parameters
        optimized_params = self._params_from_array(result.x)
        calibrated_output = self._run_with_params(optimized_params)
        rmse_after = result.fun

        logger.info("Calibration RMSE after: %.4f (converged: %s)", rmse_after, result.success)

        # Generate report
        report = self._generate_report(
            stub_output, calibrated_output, optimized_params,
            rmse_before, rmse_after, result.success,
        )

        return CalibrationResult(
            sample_name=self.sample.name,
            expected=self.expected,
            stub_output=stub_output,
            calibrated_output=calibrated_output,
            params=optimized_params,
            rmse_before=rmse_before,
            rmse_after=rmse_after,
            report=report,
            convergence=result.success,
        )

    def _generate_report(
        self,
        stub_output: dict[str, float],
        cal_output: dict[str, float],
        params: dict[str, float],
        rmse_before: float,
        rmse_after: float,
        converged: bool,
    ) -> str:
        """Generate human-readable calibration report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  CALIBRATION REPORT — {self.sample.name}")
        lines.append("=" * 70)
        lines.append("")

        # Table header
        header = f"{'Mineral':<12} {'Expected':>10} {'Stub':>10} {'Calibrated':>12} {'Δ Error':>10}"
        lines.append(header)
        lines.append("-" * 70)

        # Mineral rows
        for mineral in EXPECTED_MINERALS:
            if mineral not in self.expected:
                continue
            exp = self.expected[mineral]
            stub = stub_output.get(mineral, 0.0)
            cal = cal_output.get(mineral, 0.0)
            err = abs(cal - exp)

            # Format mineral name
            name_map = {
                "ab": "Ab", "an": "An", "or_": "Or", "q": "Q",
                "ill": "Ill", "chl": "Chl", "kn": "Kn", "mm": "Mm",
                "gb": "Gb", "ap": "Ap", "cc": "Cc", "dl": "Dl",
                "ank": "Ank", "rch": "Rch", "sd": "Sd", "srp": "Srp",
                "mst": "Mst", "ht": "Ht", "prl": "Prl",
            }
            display_name = name_map.get(mineral, mineral)

            lines.append(
                f"  {display_name:<10} {exp:>10.2f} {stub:>10.2f} {cal:>12.2f} {err:>10.4f}"
            )

        # Summary
        lines.append("-" * 70)
        lines.append(f"  {'RMSE':<10} {'':>10} {rmse_before:>10.4f} {rmse_after:>12.4f}")
        lines.append(f"  {'Converged':<10} {'':>10} {'':>10} {'Yes' if converged else 'No':>12}")
        lines.append("")

        # Parameters
        lines.append("Optimized Parameters:")
        lines.append("-" * 40)
        for name, val in params.items():
            default = DEFAULT_PARAMS[name]
            changed = " *" if abs(val - default) > 0.01 else ""
            lines.append(f"  {name:<25} {val:>8.4f}  (default: {default:.4f}){changed}")
        lines.append("")

        return "\n".join(lines)


def save_calibration_config(params: dict[str, float], path: Path) -> None:
    """Save calibrated parameters to JSON config file."""
    config = {
        "calibrated": True,
        "parameters": params,
        "description": "Auto-calibrated algorithm parameters from MINLITH Excel",
    }
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Calibration config saved: %s", path)


def load_calibration_config(path: Path) -> dict[str, float]:
    """Load calibrated parameters from JSON config file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("calibrated"):
        raise ValueError(f"File {path} is not a calibration config")
    return data["parameters"]
