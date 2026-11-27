"""Shared classification fields for the sedimentary diagrams.

Only A-CN-K (Nesbitt & Young, 1984) needs shared geometry: the weathering
triangle and its reference minerals.  Igneous classification fields (TAS,
QAPF, feldspar, AFM, SiO2-K2O) were removed with their charts — MINLITH
Modern is a sedimentary-rock tool.

Coordinates are molar ``(A, CN, K)`` fractions.
"""

from __future__ import annotations

# --- A-CN-K (Nesbitt & Young, 1984) ----------------------------------------

CIA_LEVELS: tuple[int, ...] = (50, 60, 70, 80, 90)

# Reference minerals in molar (A, CN, K) coordinates.  Plagioclase endmembers
# collapse onto the same point because A-CN-K does not distinguish Ca from Na.
ACNK_MINERALS: list[tuple[str, float, float, float]] = [
    ("Плагиоклаз", 0.5, 0.5, 0.0),
    ("К-полевой шпат", 0.5, 0.0, 0.5),
    ("Иллит/мусковит", 1.5, 0.0, 0.5),
    ("Каолинит/гиббсит", 1.0, 0.0, 0.0),
]

# Idealised weathering path: plagioclase -> kaolinite/gibbsite.
ACNK_WEATHERING: tuple[tuple[float, float, float], tuple[float, float, float]] = (
    (0.5, 0.5, 0.0),
    (1.0, 0.0, 0.0),
)
