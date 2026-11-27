import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws = wb.worksheets[6]  # Нач+Type 12

# ill = I147, or = J147, chl = H147, q = M147, kn = X147
# I need to find what formulas are ABOVE row 147 that compute these
# The named ranges reference these cells, but row 147 itself has hardcoded values
# Let me search for formulas in rows 160-290 that might reference these cells

print("=== ROWS 160-290 (looking for computation of ill, or, chl, q, kn) ===")
for r in range(160, 291):
    vals = []
    for c in range(1, min(ws.max_column+1, 40)):
        v = ws.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)

# Also check rows 165-170 for Stage IV-V
print("\n=== ROWS 165-175 ===")
for r in range(165, 176):
    vals = []
    for c in range(1, min(ws.max_column+1, 40)):
        v = ws.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)
