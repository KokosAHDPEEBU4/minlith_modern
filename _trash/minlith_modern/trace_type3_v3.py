import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=True)
ws3 = wb.worksheets[5]  # Нач+Type 3

print("=== TYPE 3 SHEET INPUT DATA (data_only=True) ===")
for r in range(1, 20):
    vals = []
    for c in range(1, 10):
        v = ws3.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)

# Read the key computed values
print("\n=== TYPE 3 SHEET KEY COMPUTED VALUES ===")
keys3 = {
    'D4': 'Al2O3_fu', 'D6': 'FeO_total_fu', 'D7': 'MgO_fu', 'D8': 'CaO_fu',
    'D9': 'Na2O_fu', 'D10': 'K2O_fu', 'D2': 'SiO2_fu',
    'F12': 'k1', 'F13': 'k2', 'F14': 'k3', 'F15': 'k4',
    'G2': 'F', 'I2': 'A',
    'C46': 'Ab=Na', 'C47': 'Si1', 'C48': 'Al1',
    'C50': 'check Ca>=0.2Na', 'C51': 'check Si1<6K+0.4Na',
    'C52': 'check Ca<0.2Na', 'C53': 'check Si1<6K+2Ca',
    'C60': 'check Ca>=0.2Na (321)', 'C61': 'check Si1>=6K+0.4Na (321)',
    'C62': 'An=0.2Na (321)', 'C63': 'Si2 (321)', 'C64': 'Al2 (321)',
    'C67': 'check Ca<0.2Na (322)', 'C68': 'check Si1>=6K+2Ca (322)',
    'C69': 'An=Ca (322)', 'C70': 'Si2 (322)', 'C71': 'Al2 (322)',
    'C74': 'k1=0?', 'C75': 'k2=0?', 'C76': 'k3=0?',
    'C77': 'Or=K', 'C78': 'Si3 (331)', 'C79': 'Al3 (331)',
    'C81': 'check 2Al3>=Si3 (3311)', 'C82': 'Kn (3311)', 'C83': 'Gb (3311)',
    'C86': 'check 2Al3<Si3 (3312)', 'C87': 'Kn (3312)',
    'C90': 'check 4.5Mg-Al2+K>=0 (3321)', 'C93': 'check K/2>=threshold (3321)',
    'C95': 'Chl (4x)', 'C97': 'Ill (4x)', 'C98': 'Or (4x)',
    'C100': 'Fe2 (4x)', 'C101': 'Si3 (4x)',
    'C105': 'check Fe2>=0', 'C106': 'check Si3>=0',
    'C109': 'check Fe2<0 (332112)', 'C112': 'check Si3<0 (332113)',
    'C114': 'check K/2<threshold (33212)',
    'C116': 'ill=K/2', 'C120': 'Chl (332121)', 'C121': 'Mg1 (332121)',
    'C122': 'Fe2 (332121)', 'C123': 'Si3 (332121)',
    'C126': 'check Mg-K/2-k1/k3*(Al-3.25K)<0 (332122)',
    'C127': 'Chl (332122)', 'C129': 'Fe2 (332122)', 'C130': 'Si3 (332122)',
    'C132': 'check Fe2<0 (3321221)', 'C136': 'check Si3<0 (3321222)',
    'C139': 'check Si3>=0 (3321223)',
    'C141': 'check 4.5Mg-Al2+K<0 (3322)', 'C142': 'Ill=Mg (3322)',
    'C143': 'Or=K-2Ill (3322)', 'C145': 'Fe2 (3322)', 'C146': 'Si3 (3322)', 'C147': 'Al3 (3322)',
    'C149': 'check Fe2<0 (33221)', 'C153': 'check Si3<0 (33222)',
    'C156': 'check Si3>=0 (33223)',
    'C158': 'check 4.5Fe-Al2+K>=0 (3331)', 'C159': 'check 4.5k1-k2>0 (3331)',
}

for cell, label in keys3.items():
    v = ws3[cell].value
    print(f"  {cell:6s} ({label:45s}) = {v}")
