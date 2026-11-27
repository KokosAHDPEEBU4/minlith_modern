import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws = wb.worksheets[6]  # Нач+Type 12

# Key cells referenced in named ranges:
# al_1 = I173, al_2 = I174, si_1 = I175, si_2 = I176, si_3 = I177
# fe_1 = I21, mg = D7, k = D10, na = D9, ca = D8
# fe3_1 = Type 3 sheet I21 (need to check)
# mg_1 = Type 3 sheet I56 (need to check)

# Read all key cells
print("=== KEY VARIABLE VALUES ===")
keys = {
    'D4': 'Al2O3_fu', 'D6': 'FeO_total_fu', 'D7': 'MgO_fu', 'D8': 'CaO_fu',
    'D9': 'Na2O_fu', 'D10': 'K2O_fu', 'D2': 'SiO2_fu',
    'I173': 'al_1 (from named range)', 'I174': 'al_2', 'I175': 'si_1', 'I176': 'si_2', 'I177': 'si_3',
    'I21': 'fe_1 (from named range)',
    'C174': 'Ab (row 174)', 'C175': 'Si1 (row 175)',
    'C205': 'K_ill (row 205)',
    'C214': 'Ill 2x (row 214)', 'C215': 'Or 2x (row 215)',
    'C222': 'Ill Mg>=Fe1 (row 222)', 'C223': 'Or Mg>=Fe1 (row 223)',
    'C230': 'Ill Mg<Fe1 (row 230)', 'C231': 'Or Mg<Fe1 (row 231)',
    'C252': 'Ill K/2 (row 252)',
    'C275': 'Ill 3x (row 275)', 'C276': 'Or 3x (row 276)',
    'F147': 'Ab FU (row 147)', 'H147': 'Chl FU (row 147)', 'I147': 'Ill FU (row 147)',
    'J147': 'Or FU (row 147)', 'M147': 'Q FU (row 147)', 'X147': 'Kn FU (row 147)',
    'B93': 'Ca_n', 'F93': 'Si_n', 'B94': 'Mg_n', 'B95': 'Fe_n',
}

for cell, label in keys.items():
    v = ws[cell].value
    print(f"  {cell} ({label}) = {v}")

# Now read the named range fe3_1 from Type 3 sheet
ws3 = wb.worksheets[5]  # Нач+Type 3
print("\n=== TYPE 3 SHEET KEY VALUES ===")
for cell in ['I21', 'I47', 'I48', 'I49', 'I50', 'I51', 'I53', 'I55', 'I56', 'I57']:
    v = ws3[cell].value
    print(f"  {cell} = {v}")
