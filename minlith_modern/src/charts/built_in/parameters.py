"""Geochemical parameters — CIA, ICV, PIA, ASI, AI.

These are computed as additional columns in the results table,
not as separate diagrams (per CHARTS_CATALOG.md).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.core.models import OxideComposition


@dataclass
class GeoParameters:
    """Geochemical indices for a single sample."""

    CIA: float = 0.0   # Chemical Index of Alteration
    ICV: float = 0.0   # Index of Compositional Variability
    PIA: float = 0.0   # Plagioclase Index of Alteration
    ASI: float = 0.0   # Aluminum Saturation Index
    AI: float = 0.0    # Aluminum Index
    MW_ratio: float = 0.0  # Molar weight ratio (for reference)

    # Raw components for display
    CaO_star: float = 0.0
    molar_al2o3: float = 0.0
    molar_cao: float = 0.0
    molar_na2o: float = 0.0
    molar_k2o: float = 0.0


def compute_parameters(comp: OxideComposition) -> GeoParameters:
    """Compute geochemical parameters from oxide composition.

    Molecular weights for conversion:
        Al2O3: 101.96, CaO: 56.08, Na2O: 61.98, K2O: 94.20,
        Fe2O3: 159.69, MgO: 40.30, MnO: 70.94, TiO2: 79.87
    """
    # Molar proportions
    m_al2o3 = comp.al2o3 / 101.96
    m_cao = comp.cao / 56.08
    m_na2o = comp.na2o / 61.98
    m_k2o = comp.k2o / 94.20
    m_fe2o3 = comp.fe2o3 / 159.69
    m_mgo = comp.mgo / 40.30
    m_mno = comp.mno / 70.94
    m_tio2 = comp.tio2 / 79.87

    # CaO* (silicate CaO only) — simplified: assume all CaO is silicate
    # (proper correction requires carbonate check, simplified here)
    cao_star = m_cao

    # CIA = 100 × Al2O3 / (Al2O3 + CaO* + Na2O + K2O)
    denom_cia = m_al2o3 + cao_star + m_na2o + m_k2o
    cia = 100 * m_al2o3 / denom_cia if denom_cia > 0 else 0.0

    # ICV = (Fe2O3 + K2O + Na2O + CaO + MgO + MnO + TiO2) / Al2O3
    icv_num = m_fe2o3 + m_k2o + m_na2o + m_cao + m_mgo + m_mno + m_tio2
    icv = icv_num / m_al2o3 if m_al2o3 > 0 else 0.0

    # PIA = 100 × (Al2O3 - K2O) / (Al2O3 + CaO* + Na2O - K2O)
    pia_num = m_al2o3 - m_k2o
    pia_den = m_al2o3 + cao_star + m_na2o - m_k2o
    pia = 100 * pia_num / pia_den if pia_den > 0 else 0.0

    # ASI = Al2O3 / (CaO + Na2O + K2O) (molecular, mol)
    asi_den = m_cao + m_na2o + m_k2o
    asi = m_al2o3 / asi_den if asi_den > 0 else 0.0

    # AI = Al2O3 - (K2O + Na2O + CaO) (molecular)
    ai = m_al2o3 - (m_k2o + m_na2o + m_cao)

    return GeoParameters(
        CIA=round(cia, 2),
        ICV=round(icv, 4),
        PIA=round(pia, 2),
        ASI=round(asi, 4),
        AI=round(ai, 4),
        CaO_star=round(cao_star, 4),
        molar_al2o3=round(m_al2o3, 4),
        molar_cao=round(m_cao, 4),
        molar_na2o=round(m_na2o, 4),
        molar_k2o=round(m_k2o, 4),
    )


# Parameter metadata for display
PARAMETER_INFO = {
    "CIA": ("CIA", "Chemical Index of Alteration", "100×Al₂O₃/(Al₂O₃+CaO*+Na₂O+K₂O)", "50-100"),
    "ICV": ("ICV", "Index of Compositional Variability", "Σ(mafic)/Al₂O₃ (mol)", "<1 = mature"),
    "PIA": ("PIA", "Plagioclase Index of Alteration", "100×(Al₂O₃-K₂O)/(Al₂O₃+CaO*+Na₂O-K₂O)", "50-100"),
    "ASI": ("ASI", "Aluminum Saturation Index", "Al₂O₃/(CaO+Na₂O+K₂O) (mol)", ">1 = peraluminous"),
    "AI":  ("AI",  "Aluminum Index", "Al₂O₃-(K₂O+Na₂O+CaO) (mol)", ">0 = peraluminous"),
}
