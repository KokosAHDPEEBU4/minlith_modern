import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws = wb.worksheets[6]  # Нач+Type 12

# Read rows 50-130
print("=== ROWS 50-130 ===")
for r in range(50, 131):
    vals = []
    for c in range(1, min(ws.max_column+1, 30)):
        v = ws.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)
