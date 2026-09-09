"""Calculation engine — orchestrates the full MINLITH calculation pipeline."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from src.core.algorithm import AlgorithmInput, AlgorithmOutput, MineralAlgorithm
from src.core.theory_algorithm import TheoryAlgorithm
from src.core.anomaly_detector import AnomalyDetector
from src.core.models import (
    AdaptiveCoefficients,
    CalculationConfig,
    CalculationResult,
    FormulaUnits,
    MineralComposition,
    OxideComposition,
    RockType,
    Sample,
)
from src.core.constants import (
    FORMULA_WEIGHTS,
    MOLAR_MASSES_IUPAC,
    MOLAR_MASSES_MINLITH,
    OXIDE_ORDER,
)
from src.core.coefficients import calculate_coefficients
from src.core.debug_tracer import DebugTraceCollector
from src.core.validation import validate_sample

logger = logging.getLogger(__name__)


class CalculationTimeoutError(Exception):
    """Raised when a calculation exceeds the time limit."""


class _TimeoutWrapper:
    """Cross-platform timeout wrapper using concurrent.futures."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self.result = None
        self.exception = None

    def run(self, func, *args, **kwargs):
        if self.seconds <= 0:
            raise CalculationTimeoutError(
                f"Расчёт превысил лимит {self.seconds} сек"
            )

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                self.result = future.result(timeout=self.seconds)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise CalculationTimeoutError(
                    f"Расчёт превысил лимит {self.seconds} сек"
                )
        return self.result


class Calculator:
    """Main calculation engine for MINLITH mineralogical norm."""

    def __init__(
        self,
        config: Optional[CalculationConfig] = None,
        algorithm: Optional[MineralAlgorithm] = None,
    ):
        self.config = config or CalculationConfig()
        self.algorithm = algorithm or TheoryAlgorithm()

    def _get_molar_masses(self) -> dict[str, float]:
        """Get molar masses based on config source."""
        if self.config.molar_mass_source == "minlith":
            masses = dict(MOLAR_MASSES_MINLITH)
        else:
            masses = dict(MOLAR_MASSES_IUPAC)
        masses.update(self.config.custom_molar_masses)
        return masses

    def _stage_0(
        self, samples: list[Sample], tracer: Optional[DebugTraceCollector] = None
    ) -> tuple[np.ndarray, np.ndarray, list[AdaptiveCoefficients], list[RockType], np.ndarray]:
        """
        Stage 0: Preparation (vectorized with numpy).

        1. Convert weight % to formula units
        2. Fe2O3 -> FeO equivalent
        3. Correct CaO (apatite), F (fluorite), Na (halite)
        4. Calculate F, A, k1-k4
        5. Classify rock type (1-5)
        """
        masses = self._get_molar_masses()
        n = len(samples)

        oxides = np.zeros((n, len(OXIDE_ORDER)), dtype=np.float64)
        for i, s in enumerate(samples):
            oxides[i] = s.composition.to_array()

        feo_idx = OXIDE_ORDER.index("feo")
        fe2o3_idx = OXIDE_ORDER.index("fe2o3")
        feo_total_wt = oxides[:, fe2o3_idx] * 0.9 + oxides[:, feo_idx]

        oxides_for_fu = oxides.copy()
        oxides_for_fu[:, feo_idx] = feo_total_wt

        molar_arr = np.array([masses[k] for k in OXIDE_ORDER], dtype=np.float64)
        fe = oxides_for_fu / molar_arr * 10000

        # Original FeO (before correction) for FormulaUnits.fe1
        feo_original = oxides[:, feo_idx] / masses["feo"] * 10000

        cao_idx = OXIDE_ORDER.index("cao")
        p2o5_idx = OXIDE_ORDER.index("p2o5")
        apatite_ca = 3.36 * oxides[:, p2o5_idx] / masses["p2o5"] * 10000
        fe[:, cao_idx] -= apatite_ca

        f_idx = OXIDE_ORDER.index("f")
        p2o5_fu = fe[:, p2o5_idx]
        fe[:, f_idx] -= 0.67 * p2o5_fu

        na2o_idx = OXIDE_ORDER.index("na2o")
        cl_idx = OXIDE_ORDER.index("cl")
        cl_fu = fe[:, cl_idx]
        fe[:, na2o_idx] -= cl_fu / 2

        # Clamp negative formula units to 0
        np.clip(fe, 0, None, out=fe)

        al2o3_idx = OXIDE_ORDER.index("al2o3")
        mgo_idx = OXIDE_ORDER.index("mgo")
        fe_total = fe[:, feo_idx]
        mg_fu = fe[:, mgo_idx]

        with np.errstate(divide="ignore", invalid="ignore"):
            F_values = np.where(
                fe_total + mg_fu > 0,
                fe_total / (fe_total + mg_fu),
                0.0,
            )

            al_fu = fe[:, al2o3_idx]
            A_values = np.where(
                2 * al_fu + fe_total + mg_fu > 0,
                2 * al_fu / (2 * al_fu + fe_total + mg_fu),
                0.0,
            )

        F_values = np.round(F_values, 3)
        A_values = np.round(A_values, 3)

        coefficients = []
        for i in range(n):
            coeff = calculate_coefficients(float(F_values[i]), float(A_values[i]))
            coefficients.append(coeff)

        k2o_idx = OXIDE_ORDER.index("k2o")
        rock_types = []
        for i in range(n):
            na = fe[i, na2o_idx]
            k = fe[i, k2o_idx]
            mg = fe[i, mgo_idx]
            al = fe[i, al2o3_idx]
            coeff = coefficients[i]
            rt = self._classify_type(al, na, k, mg, coeff)
            rock_types.append(rt)

        return fe, fe_total, coefficients, rock_types, feo_original

    def _classify_type(
        self, al: float, na: float, k: float, mg: float, coeff: AdaptiveCoefficients
    ) -> RockType:
        """Classify rock type based on thresholds."""
        if al <= 1.2 * na + k:
            return RockType.TYPE_1
        elif al <= 1.2 * na + 3.25 * k:
            return RockType.TYPE_2
        if coeff.k1 < 1e-10:
            return RockType.TYPE_5
        t3 = 1.2 * na + 3.25 * k + (mg - 0.5 * k * coeff.k3) / coeff.k1
        if al <= t3:
            return RockType.TYPE_3
        t4 = 5 * na + 3.25 * k + (mg - 0.5 * k - 2 * na) * coeff.k3 / coeff.k1
        if al <= t4:
            return RockType.TYPE_4
        return RockType.TYPE_5

    def _build_algorithm_input(
        self, fe: np.ndarray, coeff: AdaptiveCoefficients, rock_type: RockType
    ) -> AlgorithmInput:
        """Build AlgorithmInput from prepared formula unit array."""
        return AlgorithmInput(
            sio2=float(fe[OXIDE_ORDER.index("sio2")]),
            tio2=float(fe[OXIDE_ORDER.index("tio2")]),
            al2o3=float(fe[OXIDE_ORDER.index("al2o3")]),
            feo=float(fe[OXIDE_ORDER.index("feo")]),
            mgo=float(fe[OXIDE_ORDER.index("mgo")]),
            cao=float(fe[OXIDE_ORDER.index("cao")]),
            na2o=float(fe[OXIDE_ORDER.index("na2o")]),
            k2o=float(fe[OXIDE_ORDER.index("k2o")]),
            p2o5=float(fe[OXIDE_ORDER.index("p2o5")]),
            mno=float(fe[OXIDE_ORDER.index("mno")]),
            c=float(fe[OXIDE_ORDER.index("c")]),
            so3=float(fe[OXIDE_ORDER.index("so3")]),
            f=float(fe[OXIDE_ORDER.index("f")]),
            cl=float(fe[OXIDE_ORDER.index("cl")]),
            s=float(fe[OXIDE_ORDER.index("s")]),
            co2=float(fe[OXIDE_ORDER.index("co2")]),
            so=float(fe[OXIDE_ORDER.index("so")]),
            k1=coeff.k1,
            k2=coeff.k2,
            k3=coeff.k3,
            k4=coeff.k4,
            F=coeff.F,
            A=coeff.A,
            rock_type=int(rock_type),
        )

    @staticmethod
    def _output_to_mineralComposition(out: AlgorithmOutput) -> MineralComposition:
        """Map algorithm output to MineralComposition dataclass."""
        return MineralComposition(
            ab=out.Ab,
            an=out.An,
            or_=out.Or,
            ill=out.Ill,
            chl=out.Chl,
            kn=out.Kn,
            mm=out.Mm,
            gb=out.Gb,
            q=out.Q,
            dl=out.Dl,
            ank=out.Ank,
            cc=out.Cc,
            rch=out.Rch,
            sd=out.Sd,
            srp=out.Srp,
            mst=out.Mst,
            ht=out.Ht,
            prl=out.Prl,
        )

    def calculate_single(
        self, sample: Sample, debug: bool = False
    ) -> CalculationResult:
        """Calculate mineral composition for a single sample."""
        tracer = DebugTraceCollector(sample.name) if debug else None

        is_valid, warnings = validate_sample(
            sample.composition, self.config
        )
        if tracer:
            tracer.record("Валидация", "is_valid", is_valid)

        # Stage 0: preparation
        fe_arr, fe_total_arr, coeffs, rtypes, feo_orig = self._stage_0([sample], tracer)
        fe = fe_arr[0]
        fe_total = fe_total_arr[0]
        coeff = coeffs[0]
        rock_type = rtypes[0]

        if tracer:
            tracer.record("Коэффициенты", "F", coeff.F)
            tracer.record("Коэффициенты", "A", coeff.A)
            tracer.record("Коэффициенты", "k1", coeff.k1)
            tracer.record("Коэффициенты", "k2", coeff.k2)
            tracer.record("Коэффициенты", "k3", coeff.k3)
            tracer.record("Коэффициенты", "k4", coeff.k4)
            tracer.record("Тип породы", "rock_type", rock_type.name)

        # Build AlgorithmInput
        alg_input = self._build_algorithm_input(fe, coeff, rock_type)

        # Run algorithm with timeout
        wrapper = _TimeoutWrapper(self.config.timeout_seconds)
        alg_output = wrapper.run(self.algorithm.compute, alg_input)
        if tracer:
            tracer.record("Алгоритм", "Ab", alg_output.Ab)
            tracer.record("Алгоритм", "An", alg_output.An)
            tracer.record("Алгоритм", "Or", alg_output.Or)
            tracer.record("Алгоритм", "Q", alg_output.Q)
            tracer.record("Алгоритм", "Ill", alg_output.Ill)
            tracer.record("Алгоритм", "Chl", alg_output.Chl)
            tracer.record("Алгоритм", "Kn", alg_output.Kn)

        # Map to MineralComposition
        minerals = self._output_to_mineralComposition(alg_output)

        # Add accessory minerals (computed outside main algorithm)
        minerals = MineralComposition(
            ab=minerals.ab,
            an=minerals.an,
            or_=minerals.or_,
            ill=minerals.ill,
            chl=minerals.chl,
            kn=minerals.kn,
            mm=minerals.mm,
            gb=minerals.gb,
            q=minerals.q,
            dl=minerals.dl,
            ank=minerals.ank,
            cc=minerals.cc,
            rch=minerals.rch,
            sd=minerals.sd,
            srp=minerals.srp,
            mst=minerals.mst,
            ht=minerals.ht,
            prl=minerals.prl,
            ap=float(fe[OXIDE_ORDER.index("p2o5")]),
            pr=float(fe[OXIDE_ORDER.index("s")]) / 2.0,
            hl=float(fe[OXIDE_ORDER.index("cl")]) / 2.0,
            fl=float(fe[OXIDE_ORDER.index("f")]) / 2.0,
            c=float(fe[OXIDE_ORDER.index("c")]),
        )

        # Stage VII: convert to weight %
        minerals_weight = self._to_weight_percent(minerals)

        # Normalize to 100%
        minerals_weight, norm_factor = self._normalize(minerals_weight)
        if tracer:
            tracer.record("Нормализация", "factor", norm_factor)
            tracer.record("Нормализация", "Ab_м.д.%", minerals_weight.ab)
            tracer.record("Нормализация", "Q_м.д.%", minerals_weight.q)

        # Build formula units for output
        formula_units = FormulaUnits(
            sio2=float(fe[OXIDE_ORDER.index("sio2")]),
            tio2=float(fe[OXIDE_ORDER.index("tio2")]),
            al2o3=float(fe[OXIDE_ORDER.index("al2o3")]),
            fe2o3=float(fe[OXIDE_ORDER.index("fe2o3")]),
            feo=float(fe[OXIDE_ORDER.index("feo")]),
            mgo=float(fe[OXIDE_ORDER.index("mgo")]),
            cao=float(fe[OXIDE_ORDER.index("cao")]),
            na2o=float(fe[OXIDE_ORDER.index("na2o")]),
            k2o=float(fe[OXIDE_ORDER.index("k2o")]),
            p2o5=float(fe[OXIDE_ORDER.index("p2o5")]),
            mno=float(fe[OXIDE_ORDER.index("mno")]),
            c=float(fe[OXIDE_ORDER.index("c")]),
            so3=float(fe[OXIDE_ORDER.index("so3")]),
            f=float(fe[OXIDE_ORDER.index("f")]),
            cl=float(fe[OXIDE_ORDER.index("cl")]),
            s=float(fe[OXIDE_ORDER.index("s")]),
            co2=float(fe[OXIDE_ORDER.index("co2")]),
            so=float(fe[OXIDE_ORDER.index("so")]),
            cao_corrected=float(fe[OXIDE_ORDER.index("cao")]),
            na2o_corrected=float(fe[OXIDE_ORDER.index("na2o")]),
            fe_total=fe_total,
            fe1=float(feo_orig[0]),
        )

        # Calculate defect
        if alg_output.residuals is not None:
            defect = {
                oxide: float(alg_output.residuals.get(oxide, 0.0))
                for oxide in OXIDE_ORDER
            }
        else:
            defect = self._calculate_defect(sample.composition, minerals_weight, coeff)

        # Calculate geochemical parameters
        from src.charts.built_in.parameters import compute_parameters
        geo_params = compute_parameters(sample.composition)

        # Build preliminary result for anomaly detection
        _pre_result = CalculationResult(
            sample_name=sample.name,
            input_composition=sample.composition,
            formula_units=formula_units,
            coefficients=coeff,
            rock_type=rock_type,
            minerals_formula=minerals,
            minerals_weight=minerals_weight,
            defect=defect,
            warnings=warnings,
            debug_trace=tracer,
            geo_params=geo_params,
        )

        # Detect anomalies
        detector = AnomalyDetector.instance()
        anomalies = detector.analyze(_pre_result)

        return CalculationResult(
            sample_name=sample.name,
            input_composition=sample.composition,
            formula_units=formula_units,
            coefficients=coeff,
            rock_type=rock_type,
            minerals_formula=minerals,
            minerals_weight=minerals_weight,
            defect=defect,
            warnings=warnings,
            debug_trace=tracer,
            geo_params=geo_params,
            anomalies=anomalies,
        )

    def _to_weight_percent(self, minerals: MineralComposition) -> MineralComposition:
        """Convert formula units to weight percent."""
        fw = FORMULA_WEIGHTS
        scale = 1.0 / 10000.0

        return MineralComposition(
            ab=minerals.ab * fw["Ab"] * scale,
            an=minerals.an * fw["An"] * scale,
            or_=minerals.or_ * fw["Or"] * scale,
            ill=minerals.ill * fw["Ill"] * scale,
            chl=minerals.chl * fw["Chl"] * scale,
            kn=minerals.kn * fw["Kn"] * scale,
            mm=minerals.mm * fw["Mm"] * scale,
            gb=minerals.gb * fw["Gb"] * scale,
            cc=minerals.cc * fw["Cc"] * scale,
            dl=minerals.dl * fw["Dl"] * scale,
            ank=minerals.ank * fw["Ank"] * scale,
            rch=minerals.rch * fw["Rch"] * scale,
            sd=minerals.sd * fw["Sd"] * scale,
            q=minerals.q * fw["Q"] * scale,
            ap=minerals.ap * fw["Ap"] * scale,
            c=minerals.c * 12.011 * scale,  # Carbon: molar mass 12.011
            srp=minerals.srp * fw["Srp"] * scale,
            mst=minerals.mst * fw["Mst"] * scale,
            ht=minerals.ht * fw["Ht"] * scale,
            prl=minerals.prl * fw["Prl"] * scale,
            pr=minerals.pr * fw["Pr"] * scale,
            rt=minerals.rt * fw["Rt"] * scale,
            hl=minerals.hl * fw["Hl"] * scale,
            gy=minerals.gy * fw["Gy"] * scale,
            fl=minerals.fl * fw["Fl"] * scale,
        )

    # Fields derived from other minerals (always 0, excluded from normalization)
    _DERIVED_FIELDS = frozenset({"pl", "fsp", "pel", "pel_fsp", "carsd", "ill_kn", "chl_mm_srp"})

    def _normalize(self, minerals: MineralComposition) -> tuple[MineralComposition, float]:
        """Normalize mineral weights to sum to 100%. Returns (normalized, factor)."""
        d = minerals.__dict__
        total = sum(v for k, v in d.items() if not k.startswith("_") and k not in self._DERIVED_FIELDS)
        if total == 0:
            return minerals, 1.0
        factor = 100.0 / total
        return MineralComposition(**{k: v * factor for k, v in d.items()}), factor

    def _calculate_defect(
        self, comp: OxideComposition, minerals: MineralComposition,
        coeff: Optional[AdaptiveCoefficients] = None,
    ) -> dict[str, float]:
        """Calculate defect (oxide residuals) using verified consumption matrix.

        Uses real k1-k4 coefficients from AdaptiveCoefficients for chlorite.
        """
        masses = self._get_molar_masses()
        oxide_array = comp.to_array()
        molar_arr = np.array([masses[k] for k in OXIDE_ORDER], dtype=np.float64)
        input_fu = oxide_array / molar_arr * 10000

        k1 = coeff.k1 if coeff else 1.0
        k2 = coeff.k2 if coeff else 1.0
        k3 = coeff.k3 if coeff else 1.0
        k4 = coeff.k4 if coeff else 1.0

        mineral_fu = np.zeros(18, dtype=np.float64)

        # Verified consumption matrix from Excel rows 155-162
        # SiO2
        mineral_fu[OXIDE_ORDER.index("sio2")] = (
            6 * minerals.ab + 2 * minerals.an + 6 * minerals.or_
            + 16 * minerals.ill + k4 * minerals.chl
            + 2 * minerals.kn + 24 * minerals.mm
            + minerals.q + 2 * minerals.srp
        )
        # Al2O3
        mineral_fu[OXIDE_ORDER.index("al2o3")] = (
            minerals.ab + minerals.an + minerals.or_
            + 6.5 * minerals.ill + k3 * minerals.chl
            + minerals.kn + minerals.gb + minerals.mm * 5
        )
        # MgO
        mineral_fu[OXIDE_ORDER.index("mgo")] = (
            k1 * minerals.chl + minerals.ill
            + minerals.dl + 3 * minerals.srp + minerals.mst
        )
        # FeO
        mineral_fu[OXIDE_ORDER.index("feo")] = (
            k2 * minerals.chl + minerals.ill
            + minerals.ank + minerals.sd + 2 * minerals.ht
        )
        # Na2O
        mineral_fu[OXIDE_ORDER.index("na2o")] = minerals.ab + minerals.mm
        # K2O
        mineral_fu[OXIDE_ORDER.index("k2o")] = 2 * minerals.ill + minerals.or_
        # CaO
        mineral_fu[OXIDE_ORDER.index("cao")] = (
            minerals.an + minerals.dl + minerals.ank + minerals.cc
            + minerals.ap * 3.36
        )
        # MnO
        mineral_fu[OXIDE_ORDER.index("mno")] = minerals.rch + minerals.prl

        defect = {}
        for i, oxide in enumerate(OXIDE_ORDER):
            defect[oxide] = float(input_fu[i] - mineral_fu[i])

        return defect

    def calculate(
        self, samples: list[Sample], debug: bool = False
    ) -> list[CalculationResult]:
        """Calculate mineral composition for multiple samples (sequential)."""
        results = []
        for sample in samples:
            try:
                result = self.calculate_single(sample, debug=debug)
                results.append(result)
            except Exception as e:
                logger.error("Calculation failed for %s: %s", sample.name, e)
                raise
        return results

    def calculate_batch(
        self, samples: list[Sample], max_workers: int | str = "auto",
        debug: bool = False,
    ) -> list[CalculationResult]:
        """Calculate mineral composition for multiple samples in parallel.

        Uses ProcessPoolExecutor for CPU-bound work.

        Args:
            samples: List of samples to calculate.
            max_workers: Number of workers. "auto" = min(4, cpu_count).
            debug: Enable debug tracing.

        Returns:
            List of CalculationResult in the same order as input samples.
        """
        import os
        from concurrent.futures import ProcessPoolExecutor, as_completed

        if max_workers == "auto":
            max_workers = min(4, os.cpu_count() or 1)
        max_workers = max(1, int(max_workers))

        if len(samples) <= 1 or max_workers == 1:
            return self.calculate(samples, debug=debug)

        logger.info("Batch calculation: %d samples, %d workers", len(samples), max_workers)

        # Serialize config for pickling
        config_dict = {
            "molar_mass_source": self.config.molar_mass_source,
            "custom_molar_masses": self.config.custom_molar_masses,
            "sum_tolerance": self.config.sum_tolerance,
            "warn_negative": self.config.warn_negative,
            "auto_correct_sum": self.config.auto_correct_sum,
            "decimal_places": self.config.decimal_places,
            "timeout_seconds": self.config.timeout_seconds,
            "algorithm_mode": self.config.algorithm_mode,
        }

        results: list[CalculationResult | None] = [None] * len(samples)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            for i, sample in enumerate(samples):
                future = executor.submit(
                    _calculate_single_worker, sample, config_dict, debug,
                )
                future_to_idx[future] = i

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error("Batch calculation failed for sample %d: %s", idx, e)
                    raise

        return [r for r in results if r is not None]


def _calculate_single_worker(
    sample: Sample, config_dict: dict, debug: bool,
) -> CalculationResult:
    """Standalone function for ProcessPoolExecutor (must be picklable)."""
    config = CalculationConfig(**config_dict)
    calc = Calculator(config=config)
    return calc.calculate_single(sample, debug=debug)
