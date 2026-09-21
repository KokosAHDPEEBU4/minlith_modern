"""Calculation worker — QThread + ProcessPoolExecutor for parallel batch processing."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.calculator import Calculator
from src.core.models import CalculationConfig, CalculationResult, Sample

logger = logging.getLogger(__name__)


def _calc_single(args: tuple) -> tuple[str, dict | None, str | None]:
    """Picklable top-level function for ProcessPoolExecutor.

    Returns (sample_name, result_dict_or_None, error_or_None).
    """
    sample_dict, config_dict = args
    try:
        sample = Sample(
            name=sample_dict["name"],
            composition=__import__(
                "src.core.models", fromlist=["OxideComposition"]
            ).OxideComposition(**sample_dict["composition"]),
        )
        config = CalculationConfig(**config_dict) if config_dict else CalculationConfig()
        calc = Calculator(config=config)
        result = calc.calculate_single(sample)

        # Serialize result for inter-process transfer
        return (sample_dict["name"], {
            "sample_name": result.sample_name,
            "rock_type": int(result.rock_type),
            "F": result.coefficients.F,
            "A": result.coefficients.A,
            "k1": result.coefficients.k1,
            "k2": result.coefficients.k2,
            "k3": result.coefficients.k3,
            "k4": result.coefficients.k4,
            "minerals_wt": {
                k: v for k, v in result.minerals_weight.__dict__.items()
                if not k.startswith("_")
            },
            "minerals_fu": {
                k: v for k, v in result.minerals_formula.__dict__.items()
                if not k.startswith("_")
            },
            "defect": result.defect,
            "input_composition": {k: v for k, v in result.input_composition.__dict__.items()},
            "warnings": result.warnings,
        }, None)
    except Exception as e:
        return (sample_dict["name"], None, str(e))


def _deserialize_result(data: dict) -> CalculationResult:
    """Reconstruct CalculationResult from serialized dict."""
    from src.core.models import (
        AdaptiveCoefficients,
        CalculationResult,
        FormulaUnits,
        MineralComposition,
        OxideComposition,
        RockType,
    )
    comp = OxideComposition(**data["input_composition"])
    fu = FormulaUnits(**{k: v for k, v in data.get("minerals_fu", {}).items()
                         if hasattr(FormulaUnits, k)})
    minerals_wt = MineralComposition(**{k: v for k, v in data["minerals_wt"].items()
                                       if hasattr(MineralComposition, k)})
    minerals_fu = MineralComposition(**{k: v for k, v in data["minerals_fu"].items()
                                       if hasattr(MineralComposition, k)})
    coeff = AdaptiveCoefficients(
        k1=data["k1"], k2=data["k2"], k3=data["k3"], k4=data["k4"],
        F=data["F"], A=data["A"],
    )
    return CalculationResult(
        sample_name=data["sample_name"],
        input_composition=comp,
        formula_units=fu,
        coefficients=coeff,
        rock_type=RockType(data["rock_type"]),
        minerals_formula=minerals_fu,
        minerals_weight=minerals_wt,
        defect=data["defect"],
        warnings=data["warnings"],
    )


class CalculationWorker(QThread):
    """Worker thread for batch calculations with parallel support."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    PARALLEL_THRESHOLD = 10

    def __init__(self, calculator: Calculator, samples: list[Sample], parent=None) -> None:
        super().__init__(parent)
        self._calculator = calculator
        self._samples = samples
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._samples)
        try:
            if total >= self.PARALLEL_THRESHOLD:
                results = self._run_parallel(total)
            else:
                results = self._run_sequential(total)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def _run_sequential(self, total: int) -> list[CalculationResult]:
        results = []
        for i, sample in enumerate(self._samples):
            if self._cancelled:
                break
            self.progress.emit(i + 1, total, sample.name)
            try:
                results.append(self._calculator.calculate_single(sample))
            except Exception as e:
                logger.error("Failed: %s: %s", sample.name, e)
        return results

    def _run_parallel(self, total: int) -> list[CalculationResult]:
        n_workers = min(os.cpu_count() or 4, max(2, total // 5))

        config_dict = {
            "molar_mass_source": self._calculator.config.molar_mass_source,
            "custom_molar_masses": self._calculator.config.custom_molar_masses,
            "sum_tolerance": self._calculator.config.sum_tolerance,
            "warn_negative": self._calculator.config.warn_negative,
            "decimal_places": self._calculator.config.decimal_places,
            "timeout_seconds": self._calculator.config.timeout_seconds,
            "calculation_engine": self._calculator.config.calculation_engine,
        }

        # Prepare tasks
        tasks = []
        for sample in self._samples:
            sample_dict = {
                "name": sample.name,
                "composition": {k: v for k, v in sample.composition.__dict__.items()},
            }
            tasks.append((sample_dict, config_dict))

        results = []
        done_count = 0

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(_calc_single, t): t[0]["name"] for t in tasks}

            for future in as_completed(futures):
                if self._cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                done_count += 1
                name, data, err = future.result()
                self.progress.emit(done_count, total, name)

                if err:
                    logger.error("Failed: %s: %s", name, err)
                elif data:
                    try:
                        results.append(_deserialize_result(data))
                    except Exception as e:
                        logger.error("Deserialize failed for %s: %s", name, e)

        return results
