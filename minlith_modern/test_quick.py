"""Quick test to verify MINLITH calculation works."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.models import OxideComposition, Sample
from src.core.calculator import Calculator
from src.core.constants import MOLAR_MASSES_MINLITH

# T-O2 sample data from Excel reference
t_o2_composition = OxideComposition(
    sio2=52.5,
    tio2=1.01,
    al2o3=23.41,
    fe2o3=1.71,
    feo=8.06,
    mgo=2.35,
    cao=0.28,
    na2o=0.94,
    k2o=3.45,
    p2o5=0.31,
    mno=0.157502,
    c=0.44,
    so3=0,
    f=0,
    cl=0,
    s=0,
    co2=0,
    so=0,
)

# Verify formula unit conversion
print("=== Formula Unit Verification (T-O2) ===")
comp = t_o2_composition
m = MOLAR_MASSES_MINLITH
print(f"SiO2: {comp.sio2} / {m['sio2']} * 10000 = {comp.sio2 / m['sio2'] * 10000:.0f}")
print(f"Al2O3: {comp.al2o3} / {m['al2o3']} * 10000 = {comp.al2o3 / m['al2o3'] * 10000:.0f}")
feo_total_wt = comp.fe2o3 * 0.9 + comp.feo
print(f"FeO_total_wt: {comp.fe2o3}*0.9 + {comp.feo} = {feo_total_wt}")
print(f"FeO_total_fu: {feo_total_wt} / {m['feo']} * 10000 = {feo_total_wt / m['feo'] * 10000:.0f}")
print(f"MgO: {comp.mgo} / {m['mgo']} * 10000 = {comp.mgo / m['mgo'] * 10000:.0f}")
print(f"CaO: {comp.cao} / {m['cao']} * 10000 = {comp.cao / m['cao'] * 10000:.0f}")
print(f"Na2O: {comp.na2o} / {m['na2o']} * 10000 = {comp.na2o / m['na2o'] * 10000:.2f}")
print(f"K2O: {comp.k2o} / {m['k2o']} * 10000 = {comp.k2o / m['k2o'] * 10000:.2f}")

# Expected values from Excel
print("\nExpected f.e.:")
print(f"  SiO2: 8737")
print(f"  Al2O3: 2296")
print(f"  FeO_total: 1336")
print(f"  MgO: 583")

# Create sample
sample = Sample(name="T-O2", composition=t_o2_composition)

# Run calculation
calculator = Calculator()
result = calculator.calculate_single(sample, debug=True)

# Print formula units
print(f"\n=== Calculated Formula Units ===")
fu = result.formula_units
print(f"  SiO2: {fu.sio2:.0f}")
print(f"  Al2O3: {fu.al2o3:.0f}")
print(f"  FeO_total: {fu.feo:.0f}")
print(f"  MgO: {fu.mgo:.0f}")
print(f"  CaO: {fu.cao:.0f}")
print(f"  Na2O: {fu.na2o:.2f}")
print(f"  K2O: {fu.k2o:.2f}")

# Print coefficients
print(f"\n=== Coefficients ===")
c = result.coefficients
print(f"  F={c.F}, A={c.A}")
print(f"  k1={c.k1}, k2={c.k2}, k3={c.k3}, k4={c.k4}")

# Print results
print(f"\n=== Results ===")
print(f"Sample: {result.sample_name}")
print(f"Rock Type: {result.rock_type}")
print(f"\nMineral Composition (weight %):")
print(f"  Ab: {result.minerals_weight.ab:.2f}%")
print(f"  An: {result.minerals_weight.an:.2f}%")
print(f"  Or: {result.minerals_weight.or_:.2f}%")
print(f"  Q:  {result.minerals_weight.q:.2f}%")
print(f"  Ill: {result.minerals_weight.ill:.2f}%")
print(f"  Chl: {result.minerals_weight.chl:.2f}%")
print(f"  Kn: {result.minerals_weight.kn:.2f}%")
print(f"  Gb: {result.minerals_weight.gb:.2f}%")

# Expected values from Excel reference (approximate)
print(f"\nExpected values (from Excel minerals sheet):")
print(f"  Ab: 7.82%")
print(f"  Or: 5.53%")
print(f"  Q:  31.38%")
print(f"  Ill: 36.26%")
print(f"  Chl: 25.74%")
print(f"  Kn: -9.77%")

# Print debug trace if available
if result.debug_trace:
    print(f"\nDebug Trace:")
    print(result.debug_trace.to_text())
