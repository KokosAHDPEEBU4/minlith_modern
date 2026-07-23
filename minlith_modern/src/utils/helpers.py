"""Utility helpers for MINLITH Modern — formatting, normalization, geochemical ratios."""

from __future__ import annotations

import math
import hashlib
from pathlib import Path
from datetime import datetime


# ── Formatting ──────────────────────────────────────────────────────────────


def fmt_pct(value: float, places: int = 2) -> str:
    """Format as percentage string."""
    return f"{value:.{places}f}%"


def fmt_ratio(value: float, places: int = 3) -> str:
    """Format ratio (e.g. A/CNK)."""
    if math.isnan(value) or math.isinf(value):
        return "—"
    return f"{value:.{places}f}"


def fmt_oxide_name(field: str) -> str:
    """Convert internal field name to chemical formula: 'sio2' → 'SiO₂'."""
    _sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    mapping = {
        "sio2": "SiO₂", "al2o3": "Al₂O₃", "fe2o3": "Fe₂O₃", "feo": "FeO",
        "feot": "FeOᵀ", "mgo": "MgO", "cao": "CaO", "na2o": "Na₂O",
        "k2o": "K₂O", "tio2": "TiO₂", "p2o5": "P₂O₅", "mno": "MnO",
        "so3": "SO₃", "h2o": "H₂O", "co2": "CO₂", "cr2o3": "Cr₂O₃",
        "nio": "NiO", "bao": "BaO", "sr": "SrO",
    }
    return mapping.get(field.lower(), field.upper())


def fmt_mineral_name(name: str) -> str:
    """Capitalize mineral name."""
    _map = {
        "q": "Quartz", "ab": "Albite", "an": "Anorthite", "or_": "Orthoclase",
        "ill": "Illite", "chl": "Chlorite", "kn": "Kaolinite", "dl": "Dickite",
        "gb": "Gibbsite", "srp": "Serpentine", "prl": "Pyrophyllite",
        "act": "Actinolite", "hb": "Hornblende", "di": "Diopside",
        "cc": "Calcite", "dl": "Dolomite", "ms": "Muscovite", "bt": "Biotite",
    }
    return _map.get(name.lower(), name.capitalize())


# ── Normalization ───────────────────────────────────────────────────────────


def normalize_to_sum(values: dict[str, float], target: float = 100.0) -> dict[str, float]:
    """Normalize mineral/oxide dict so values sum to target."""
    total = sum(values.values())
    if total == 0:
        return values
    factor = target / total
    return {k: v * factor for k, v in values.items()}


def normalize_composition(comp) -> dict[str, float]:
    """Return normalized oxide composition (sum=100%)."""
    fields = ["sio2", "al2o3", "fe2o3", "feo", "mgo", "cao", "na2o", "k2o", "p2o5", "mno"]
    raw = {f: getattr(comp, f, 0.0) for f in fields if getattr(comp, f, 0.0) > 0}
    return normalize_to_sum(raw)


# ── Geochemical ratios ──────────────────────────────────────────────────────


def molar_ratio(oxide_val: float, oxide_mw: float, element_count: int,
                divisor_val: float, divisor_mw: float, divisor_count: int) -> float:
    """Generic molar ratio: (oxide/mw * el_count) / (divisor/mw * el_count)."""
    num = (oxide_val / oxide_mw) * element_count
    den = (divisor_val / divisor_mw) * divisor_count
    if den == 0:
        return float("nan")
    return num / den


# Cation mole fractions (molar basis)
def cation_moles(oxide_val: float, mw: float, n_cations: int) -> float:
    return (oxide_val / mw) * n_cations


# ── Rock classification helpers ─────────────────────────────────────────────


def tas_classify(total_alkali: float, silica: float) -> str:
    """Simple TAS classification (Le Maitre et al. 2002)."""
    if silica < 45:
        if total_alkali < 1.0: return "Picrobasalt"
        if total_alkali < 5.0: return "Basalt"
        return "Tephrite/Phonolite"
    if silica < 52:
        if total_alkali < 5.0: return "Basalt"
        if total_alkali < 7.0: return "Basaltic Andesite"
        return "Trachybasalt"
    if silica < 57:
        if total_alkali < 6.0: return "Andesite"
        return "Trachyandesite"
    if silica < 63:
        if total_alkali < 7.0: return "Dacite"
        return "Trachyte"
    if total_alkali < 8.0: return "Rhyolite"
    return "Alkaline Rhyolite"


def cipw_normative_feldspar(ab: float, an: float, or_: float) -> str:
    """Simplified feldspar name from normative Ab, An, Or."""
    total = ab + an + or_
    if total == 0:
        return "N/A"
    p_ab = ab / total * 100
    p_an = an / total * 100
    p_or = or_ / total * 100
    if p_an > 90:
        return "Anorthosite"
    if p_ab > 50 and p_or > 20:
        return "Granite"
    if p_ab > 60:
        return "Trondhjemite"
    if p_or > 50:
        return "Alkali Feldspar Granite"
    return "Diorite"


# ── File hashing ────────────────────────────────────────────────────────────


def sha256_file(path: Path | str) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Timestamp ───────────────────────────────────────────────────────────────


def now_iso() -> str:
    """ISO-8601 timestamp."""
    return datetime.now().isoformat(timespec="seconds")
