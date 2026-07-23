"""Constants for MINLITH Modern: molar masses, formula weights, oxide aliases."""

from __future__ import annotations

# Molar masses (IUPAC)
MOLAR_MASSES_IUPAC: dict[str, float] = {
    "sio2": 60.084,
    "tio2": 79.866,
    "al2o3": 101.961,
    "fe2o3": 159.687,
    "feo": 71.844,
    "mgo": 40.304,
    "cao": 56.077,
    "na2o": 61.979,
    "k2o": 94.196,
    "p2o5": 141.945,
    "mno": 70.937,
    "c": 12.011,
    "so3": 80.063,
    "f": 18.998,
    "cl": 35.453,
    "s": 32.059,
    "co2": 44.010,
    "so": 48.064,
}

# Molar masses (MINLITH legacy)
MOLAR_MASSES_MINLITH: dict[str, float] = {
    "sio2": 60.09,
    "tio2": 79.87,
    "al2o3": 101.96,
    "fe2o3": 159.69,
    "feo": 71.85,
    "mgo": 40.32,
    "cao": 56.08,
    "na2o": 61.982,
    "k2o": 94.2,
    "p2o5": 141.95,
    "mno": 70.94,
    "c": 12.01,
    "so3": 80.066,
    "f": 19.0,
    "cl": 35.457,
    "s": 32.066,
    "co2": 44.011,
    "so": 48.064,
}

# Formula weights for minerals
FORMULA_WEIGHTS: dict[str, float] = {
    "Ab": 524.482,
    "An": 278.22,
    "Or": 556.7,
    "Q": 60.09,
    "Mm": 2202.6,
    "Ill": 2014.75,
    "Chl": 683.396,
    "Gb": 156.008,
    "Kn": 258.172,
    "Ap": 336.21,
    "Cc": 100.091,
    "Dl": 184.42,
    "Ank": 215.952,
    "Rch": 114.952,
    "Sd": 115.861,
    "Srp": 227.172,
    "Mst": 84.331,
    "Ht": 177.716,
    "Prl": 86.94,
    "Pr": 119.982,
    "Rt": 60.09,
    "Hl": 116.896,
    "Gy": 172.178,
    "Fl": 78.08,
}

# Oxide aliases (case-insensitive)
OXIDE_ALIASES: dict[str, list[str]] = {
    "sio2": ["sio2", "sio₂", "sio 2", "кремнезём", "кремнезем"],
    "tio2": ["tio2", "tio₂", "tio 2", "титан"],
    "al2o3": ["al2o3", "al₂o₃", "al2 o3", "глинозём", "глинозем"],
    "fe2o3": ["fe2o3", "fe₂o₃", "fe2 o3", "оксид железа (iii)"],
    "feo": ["feo", "оксид железа (ii)", "железо"],
    "mgo": ["mgo", "магнезия", "оксид магния"],
    "cao": ["cao", "кальция оксид", "известь"],
    "na2o": ["na2o", "na₂o", "na2 o", "натрия оксид"],
    "k2o": ["k2o", "k₂o", "k2 o", "калия оксид"],
    "p2o5": ["p2o5", "p₂o₅", "p2 o5", "фосфорный ангидрид"],
    "mno": ["mno", "оксид марганца"],
    "c": ["c", "углерод", "carbon"],
    "so3": ["so3", "so₃", "so 3", "сернистый ангидрид"],
    "f": ["f", "фтор", "fluorine"],
    "cl": ["cl", "хлор", "chlorine"],
    "s": ["s", "сера", "sulfur"],
    "co2": ["co2", "co₂", "co 2", "углекислый газ"],
    "so": ["so", "сернистый газ"],
}

# All oxide names in fixed order (matches Excel ИСХ ДАННЫЕ rows 2-19)
OXIDE_ORDER: list[str] = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]

# Mineral codes
MINERAL_CODES: list[str] = [
    "Ab", "An", "Or", "Q", "Mm", "Ill", "Chl", "Gb", "Kn",
    "Ap", "Cc", "Dl", "Ank", "Rch", "Sd", "Srp", "Mst",
    "Ht", "Prl", "Pr", "Rt", "Hl", "Gy", "Fl",
]

# Derived group formulas
DERIVED_GROUPS: dict[str, list[str]] = {
    "Pl": ["Ab", "An"],
    "Fsp": ["Ab", "An", "Or"],
    "Pel": ["Ill", "Chl", "Kn", "Mm", "Gb"],
    "PelFsp": ["Pel", "Fsp"],
    "Carsd": ["Cc", "Dl", "Ank", "Rch", "Sd"],
    "Ill+Kn": ["Ill", "Kn"],
    "Chl+Mm+Srp": ["Chl", "Mm", "Srp"],
}

# Coefficient thresholds for F ranges
# (start_F, end_F, k1_formula, k2_formula, k3_formula)
# k4 = 10 - k1 - k2 - 2*k3
F_RANGES: list[tuple[float, float, str, str, str]] = [
    (0.0, 0.21, "-5.18*F+4.42", "4.09*F", "(3.16-0.41*F)/2"),
    (0.21, 0.51, "3.93-2.96*F", "5.66*F-0.34", "(3.66-2.69*F)/2"),
    (0.51, 0.70, "5.13-5.32*F", "2.54*F+1.24", "(3.46*F+0.53)/2"),
    (0.70, 0.87, "6.2-12*F", "2.54*F+1.24", "(3.46*F+0.53)/2"),
    (0.87, 1.0, "4-4*F", "18.36*F-12.36", "(25-25*F)/2"),
]
