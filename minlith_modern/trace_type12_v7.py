import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=True)
ws = wb.worksheets[6]  # Нач+Type 12

# Read all key cells with COMPUTED values
print("=== COMPUTED VARIABLE VALUES ===")
keys = {
    'D4': 'Al2O3_fu', 'D6': 'FeO_total_fu', 'D7': 'MgO_fu', 'D8': 'CaO_fu',
    'D9': 'Na2O_fu', 'D10': 'K2O_fu', 'D2': 'SiO2_fu',
    'E47': 'Al1 (row 47)', 'E46': 'Si2 (row 46)', 'E45': 'Si1 (row 45)',
    'B45': 'Ab=Na (row 45)', 'B46': 'Or=K (row 46)',
    'E21': 'Type check 1 Al<=1.2Na+K', 'E22': 'Type check 2 Al<=1.2Na+3.25K',
    'E24': 'Type check 3', 'E25': 'Type check 4', 'E26': 'Type check 5',
    'I173': 'al_1 (2,0)', 'I174': 'al_2', 'I176': 'si_2 (2,1)',
    'I21': 'fe_1', 
    'H20': 'pr0', 'H21': 'fe_1 = Fe total - Fe pr',
    # Stage II branches
    'C180': 'Or K (2,1,1)', 'C181': 'Si2 (2,1,1)', 'C182': 'An (2,1,1)',
    'C183': 'Al1 (2,1,1)', 'C184': 'Gb (2,1,1)',
    'C193': 'An 0.2Na (2,2,1)', 'C195': 'Al1 (2,2,1)',
    # Section 2,2,2,1,1,1
    'C205': 'K_ill (2,2,2,1,1)', 'C214': 'Ill 2x', 'C215': 'Or 2x',
    'C216': 'Fe2 2x', 'C217': 'Mg1 2x', 'C218': 'Si3 2x',
    # Section 2,2,2,1,1,2
    'C222': 'Ill Mg>=Fe1', 'C223': 'Or Mg>=Fe1',
    # Section 2,2,2,1,1,3
    'C230': 'Ill Mg<Fe1', 'C231': 'Or Mg<Fe1',
    'C232': 'Fe2 Mg<Fe1', 'C233': 'Mg1 Mg<Fe1', 'C234': 'Si3 Mg<Fe1', 'C235': 'Al2 Mg<Fe1',
    # Section 2,2,2,1,1,3,1
    'C238': 'Si3>=2Al2', 'C239': 'Kn Si3>=2Al2', 'C240': 'Si4 Si3>=2Al2',
    'C243': 'Si3<2Al2', 'C244': 'Kn Si3<2Al2', 'C245': 'Gb Si3<2Al2',
    # Section 2,2,2,1,2
    'C248': 'check 0.2Na-Ca>=3.25K',
    'C250': 'Mg>=0.5K', 'C251': 'Fe>=0.5K',
    'C252': 'Ill K/2', 'C253': 'Si3 K/2', 'C254': 'Fe2 K/2', 'C255': 'Al2 K/2', 'C256': 'Mg1 K/2',
    # Section 2,2,2,2
    'C271': 'check Si2<(11.5K+2Al)/2.25',
    # Section 2,2,2,2,1
    'C273': 'Fe1>=(Si2-6K)/4', 'C274': 'Mg>=(Si2-6K)/4',
    'C275': 'Ill 3x', 'C276': 'Or 3x', 'C277': 'Gb 3x',
    'C278': 'Fe2 3x', 'C279': 'Mg1 3x',
    # Final mineral FU
    'F147': 'Ab FU', 'G147': 'An FU', 'H147': 'Chl FU', 'I147': 'Ill FU',
    'J147': 'Or FU', 'M147': 'Q FU', 'X147': 'Kn FU',
    'P147': 'Dl FU', 'T147': 'Srp FU', 'S147': 'Prl FU',
    # Residuals
    'D164': 'Si residual', 'D165': 'Al residual', 'D167': 'K residual', 'D168': 'Mg residual', 'D169': 'Fe residual',
    # Branching conditions
    'D177': 'Si1<6K+0.4Na?', 'D179': 'Ca1>=(Si1-6K)/2?',
    'D192': 'Ca1>=0.2Na?', 'D198': 'Ca1<0.2Na?',
    'D204': 'Si2>=(11.5K+2Al1)/2.25?',
    'C208': '0.2Na-Ca<3.25K?', 'C210': 'Al1<2.25K?',
    'D213': 'Fe1>=(Al1-K)/4.5 AND Mg>=(Al1-K)/4.5?',
    'D221': 'Mg>=Fe1?', 'D229': 'Mg<Fe1?',
    'D238': 'Si3>=2Al2?', 'D243': 'Si3<2Al2?',
    'D248': '0.2Na-Ca>=3.25K?', 'D258': 'Si3>=2Al2 (K/2)?',
    'D271': 'Si2<(11.5K+2Al1)/2.25?',
    'D274': 'Fe1>=(Si2-6K)/4 AND Mg>=(Si2-6K)/4?',
}

for cell, label in keys.items():
    v = ws[cell].value
    print(f"  {cell:6s} ({label:45s}) = {v}")

# Read Type 3 sheet computed values too
ws3 = wb.worksheets[5]
print("\n=== TYPE 3 SHEET COMPUTED VALUES ===")
for cell in ['I21', 'I47', 'I48', 'I49', 'I50', 'I51', 'I53', 'I55', 'I56', 'I57',
             'H271', 'H272', 'H273', 'H274', 'H275', 'H276', 'H277', 'H278', 'H279', 'H280',
             'H281', 'H282', 'H283', 'H284', 'H285', 'H286',
             'F16']:
    v = ws3[cell].value
    print(f"  {cell} = {v}")
