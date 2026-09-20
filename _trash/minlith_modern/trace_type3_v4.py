import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=True)
ws3 = wb.worksheets[5]  # Нач+Type 3

# Check column H and I values (where named ranges point)
print("=== TYPE 3 SHEET COLUMN H & I VALUES (data_only=True) ===")
for r in range(44, 90):
    h_val = ws3.cell(r, 8).value  # Column H
    i_val = ws3.cell(r, 9).value  # Column I
    if h_val is not None or i_val is not None:
        print(f"  Row {r}: H={h_val}, I={i_val}")

# Check the key named range cells
print("\n=== KEY NAMED RANGE CELLS ON TYPE 3 SHEET ===")
for cell in ['I47', 'I48', 'I49', 'I50', 'I51', 'I52', 'I53', 'I54', 'I55', 'I56', 'I57', 'I21']:
    v = ws3[cell].value
    print(f"  {cell} = {v}")

# Check the named range cells on Type 12 sheet
ws12 = wb.worksheets[6]
print("\n=== KEY NAMED RANGE CELLS ON TYPE 12 SHEET ===")
for cell in ['I173', 'I174', 'I175', 'I176', 'I177', 'I21']:
    v = ws12[cell].value
    print(f"  {cell} = {v}")

# Check what Type 3 I47-I57 actually contain
print("\n=== TYPE 3 SHEET ROW 47-57 ALL COLUMNS ===")
for r in range(47, 58):
    vals = []
    for c in range(1, 15):
        v = ws3.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}={v}")
    if vals:
        print(f"  Row {r}:")
        for v in vals: print(f"    {v}")
