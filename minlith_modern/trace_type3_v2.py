import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws3 = wb.worksheets[5]  # Нач+Type 3

# Read rows 59-120 (sections 3,2,1 onwards)
print("=== TYPE 3 SHEET ROWS 59-160 ===")
for r in range(59, 161):
    vals = []
    for c in range(1, min(ws3.max_column+1, 20)):
        v = ws3.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)
