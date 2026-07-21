"""Calculation engine — orchestrates the full MINLITH calculation pipeline."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

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
from src.core.types_logic import (
    calculate_type1,
    calculate_type2,
    calculate_type3,
    calculate_type4,
    calculate_type5,
    stage_vi,
)
from src.core.validation import validate_sample

logger = logging.getLogger(__name__)


class Calculator:
    """Main calculation engine for MINLITH mineralogical norm."""

    def __init__(self, config: Optional[CalculationConfig] = None):
        self.config = config or CalculationConfig()

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
    ) -> tuple[np.ndarray, np.ndarray, list[AdaptiveCoefficients], list[RockType]]:
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

        # Build oxide weight% array (n x 18)
        oxides = np.zeros((n, len(OXIDE_ORDER)), dtype=np.float64)
        for i, s in enumerate(samples):
            oxides[i] = s.composition.to_array()

        # Compute FeO_total in weight% FIRST: FeO_total_wt = Fe2O3_wt * 0.9 + FeO_wt
        feo_idx = OXIDE_ORDER.index("feo")
        fe2o3_idx = OXIDE_ORDER.index("fe2o3")
        feo_total_wt = oxides[:, fe2o3_idx] * 0.9 + oxides[:, feo_idx]

        # Replace FeO column with total for formula unit conversion
        oxides_for_fu = oxides.copy()
        oxides_for_fu[:, feo_idx] = feo_total_wt

        # Convert to formula units: fe = wt / M * 10000
        molar_arr = np.array([masses[k] for k in OXIDE_ORDER], dtype=np.float64)
        fe = oxides_for_fu / molar_arr * 10000

        # Correct CaO (subtract apatite): CaO_fu -= ROUND(3.33 * P2O5_wt / M_P2O5 * 10000)
        cao_idx = OXIDE_ORDER.index("cao")
        p2o5_idx = OXIDE_ORDER.index("p2o5")
        apatite_ca = 3.33 * oxides[:, p2o5_idx] / masses["p2o5"] * 10000
        fe[:, cao_idx] -= apatite_ca

        # Correct F (subtract fluorite): F_fu -= 0.67 * P2O5_fu
        f_idx = OXIDE_ORDER.index("f")
        p2o5_fu = fe[:, p2o5_idx]
        fe[:, f_idx] -= 0.67 * p2o5_fu

        # Correct Na (subtract halite): Na2O_fu -= Cl_fu / 2
        na2o_idx = OXIDE_ORDER.index("na2o")
        cl_idx = OXIDE_ORDER.index("cl")
        cl_fu = fe[:, cl_idx]
        fe[:, na2o_idx] -= cl_fu / 2

        # Calculate F = FeO_total_fu / (FeO_total_fu + MgO_fu)
        # (matches Excel: =ROUND(D6/(D6+D7),3))
        al2o3_idx = OXIDE_ORDER.index("al2o3")
        mgo_idx = OXIDE_ORDER.index("mgo")
        fe_total = fe[:, feo_idx]  # Already FeO total in formula units
        mg_fu = fe[:, mgo_idx]

        F_values = np.where(
            fe_total + mg_fu > 0,
            fe_total / (fe_total + mg_fu),
            0.0,
        )

        # Calculate A = 2*Al_fu / (2*Al_fu + FeO_total_fu + MgO_fu)
        # (matches Excel: =ROUND(2*D4/(2*D4+D6+D7),3))
        al_fu = fe[:, al2o3_idx]
        A_values = np.where(
            2 * al_fu + fe_total + mg_fu > 0,
            2 * al_fu / (2 * al_fu + fe_total + mg_fu),
            0.0,
        )

        # Round to 3 decimal places (matching Excel ROUND(...,3))
        F_values = np.round(F_values, 3)
        A_values = np.round(A_values, 3)

        # Calculate coefficients for each sample
        coefficients = []
        for i in range(n):
            coeff = calculate_coefficients(float(F_values[i]), float(A_values[i]))
            coefficients.append(coeff)

        # Classify rock types
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

        return fe, fe_total, coefficients, rock_types

    def _classify_type(
        self, al: float, na: float, k: float, mg: float, coeff: AdaptiveCoefficients
    ) -> RockType:
        """Classify rock type based on thresholds."""
        if al <= 1.2 * na + k:
            return RockType.TYPE_1
        elif al <= 1.2 * na + 3.25 * k:
            return RockType.TYPE_2
        elif al <= 1.2 * na + 3.25 * k + (mg - 0.5 * k * coeff.k3) / coeff.k1:
            return RockType.TYPE_3
        elif al <= 5 * na + 3.25 * k + (mg - 0.5 * k - 2 * na) * coeff.k3 / coeff.k1:
            return RockType.TYPE_4
        else:
            return RockType.TYPE_5

    def calculate_single(
        self, sample: Sample, debug: bool = False
    ) -> CalculationResult:
        """Calculate mineral composition for a single sample."""
        tracer = DebugTraceCollector(sample.name) if debug else None

        # Validate
        is_valid, warnings = validate_sample(
            sample.composition, self.config
        )

        # Stage 0: preparation
        fe_arr, fe_total_arr, coeffs, rtypes = self._stage_0([sample], tracer)
        fe = fe_arr[0]
        fe_total = fe_total_arr[0]
        coeff = coeffs[0]
        rock_type = rtypes[0]

        # Build formula units
        formula_units = self._build_formula_units(fe, fe_total, sample.composition)

        # Calculate minerals based on type
        minerals = self._calculate_by_type(
            formula_units, fe, coeff, rock_type, tracer
        )

        # Add apatite, pyrite, halite, fluorite
        p2o5_fu = fe[OXIDE_ORDER.index("p2o5")]
        ap = p2o5_fu
        s_fu = fe[OXIDE_ORDER.index("s")]
        pr = s_fu / 2
        cl_fu = fe[OXIDE_ORDER.index("cl")]
        hl = cl_fu / 2
        f_fu = fe[OXIDE_ORDER.index("f")]
        fl = f_fu / 2

        # Stage VI: final distribution
        minerals = stage_vi(formula_units, minerals, fe, coeff, tracer)

        # Stage VII: convert to weight %
        minerals_weight = self._to_weight_percent(minerals)

        # Normalize to 100%
        minerals_weight = self._normalize(minerals_weight)

        # Calculate defect
        defect = self._calculate_defect(sample.composition, minerals_weight)

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
        )

    def _build_formula_units(
        self, fe: np.ndarray, fe_total: float, comp: OxideComposition
    ) -> FormulaUnits:
        """Build FormulaUnits from prepared array."""
        # Calculate apatite from P2O5
        p2o5_fu = fe[OXIDE_ORDER.index("p2o5")]
        ap = p2o5_fu  # Apatite formula units = P2O5 formula units

        # Calculate pyrite from S
        s_fu = fe[OXIDE_ORDER.index("s")]
        pr = s_fu / 2  # Pyrite: FeS2

        # Calculate halite from Cl
        cl_fu = fe[OXIDE_ORDER.index("cl")]
        hl = cl_fu / 2  # Halite: NaCl

        # Calculate fluorite from F
        f_fu = fe[OXIDE_ORDER.index("f")]
        fl = f_fu / 2  # Fluorite: CaF2

        return FormulaUnits(
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
            fe1=0.0,
        )

    def _calculate_by_type(
        self,
        fu: FormulaUnits,
        fe: np.ndarray,
        coeff: AdaptiveCoefficients,
        rock_type: RockType,
        tracer: Optional[DebugTraceCollector] = None,
    ) -> MineralComposition:
        """Dispatch to type-specific calculation."""
        match rock_type:
            case RockType.TYPE_1:
                return calculate_type1(fu, coeff, tracer)
            case RockType.TYPE_2:
                return calculate_type2(fu, coeff, tracer)
            case RockType.TYPE_3:
                return calculate_type3(fu, coeff, tracer)
            case RockType.TYPE_4:
                return calculate_type4(fu, coeff, tracer)
            case RockType.TYPE_5:
                return calculate_type5(fu, coeff, tracer)
        return MineralComposition()

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
            c=minerals.c,
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

    def _normalize(self, minerals: MineralComposition) -> MineralComposition:
        """Normalize mineral weights to sum to 100%."""
        d = minerals.__dict__
        total = sum(v for k, v in d.items() if not k.startswith("_"))
        if total == 0:
            return minerals
        factor = 100.0 / total
        return MineralComposition(**{k: v * factor for k, v in d.items()})

    def _calculate_defect(
        self, comp: OxideComposition, minerals: MineralComposition
    ) -> dict[str, float]:
        """Calculate defect (oxide residuals).

        Defect = input oxides - oxides consumed by minerals (in formula units).
        Positive defect = oxide missing in minerals.
        Negative defect = oxide excess in minerals.
        """
        from src.core.constants import MOLAR_MASSES_IUPAC, OXIDE_ORDER

        # Convert input composition to formula units
        masses = self._get_molar_masses()
        oxide_array = comp.to_array()
        molar_arr = np.array([masses[k] for k in OXIDE_ORDER], dtype=np.float64)
        input_fu = oxide_array / molar_arr * 10000

        # Calculate oxide consumption by minerals (simplified)
        # This is a rough estimate - proper implementation needs mineral chemistry
        mineral_fu = np.zeros(18, dtype=np.float64)

        # Feldspars consume Si, Al, Na, K, Ca
        mineral_fu[OXIDE_ORDER.index("sio2")] = (
            minerals.ab * 6 + minerals.an * 2 + minerals.or_ * 6
        )
        mineral_fu[OXIDE_ORDER.index("al2o3")] = (
            minerals.ab + minerals.an + minerals.or_
        )
        mineral_fu[OXIDE_ORDER.index("na2o")] = minerals.ab
        mineral_fu[OXIDE_ORDER.index("k2o")] = minerals.or_
        mineral_fu[OXIDE_ORDER.index("cao")] = minerals.an

        # Clay minerals
        mineral_fu[OXIDE_ORDER.index("sio2")] += (
            minerals.ill * 2 + minerals.chl * 4 + minerals.kn * 2 +
            minerals.mm * 4 + minerals.srp * 2
        )
        mineral_fu[OXIDE_ORDER.index("al2o3")] += (
            minerals.ill + minerals.chl + minerals.kn + minerals.mm
        )
        mineral_fu[OXIDE_ORDER.index("mgo")] = minerals.chl + minerals.srp
        mineral_fu[OXIDE_ORDER.index("feo")] = minerals.chl

        # Carbonates
        mineral_fu[OXIDE_ORDER.index("cao")] += minerals.cc + minerals.dl / 2
        mineral_fu[OXIDE_ORDER.index("mgo")] += minerals.dl / 2
        mineral_fu[OXIDE_ORDER.index("feo")] += minerals.ank + minerals.sd
        mineral_fu[OXIDE_ORDER.index("mno")] = minerals.rch

        # Calculate defect
        defect = {}
        for i, oxide in enumerate(OXIDE_ORDER):
            if oxide in ["c", "so3", "f", "cl", "s", "co2", "so"]:
                continue  # Skip minor elements for now
            defect[oxide] = float(input_fu[i] - mineral_fu[i])

        return defect

    def calculate(
        self, samples: list[Sample], debug: bool = False
    ) -> list[CalculationResult]:
        """Calculate mineral composition for multiple samples."""
        results = []
        for sample in samples:
            try:
                result = self.calculate_single(sample, debug=debug)
                results.append(result)
            except Exception as e:
                logger.error("Calculation failed for %s: %s", sample.name, e)
                raise
        return results
