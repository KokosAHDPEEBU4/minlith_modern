import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws = wb.worksheets[6]  # Нач+Type 12
print(f"Sheet: {ws.title}, rows={ws.max_row}, cols={ws.max_column}")

# Read header row (row 1) to understand column layout
print("\n=== ROW 1 (headers) ===")
for c in range(1, min(ws.max_column+1, 30)):
    v = ws.cell(1, c).value
    if v: print(f"  Col {c} ({openpyxl.utils.get_column_letter(c)}): {v}")

# Read data row (row 4) - T-O2 input values
print("\n=== ROW 4 (T-O2 input) ===")
for c in range(1, min(ws.max_column+1, 30)):
    v = ws.cell(4, c).value
    if v is not None: print(f"  Col {c} ({openpyxl.utils.get_column_letter(c)}): {v}")

# Read key intermediate rows
print("\n=== ROWS 5-15 (Stage 0-1) ===")
for r in range(5, 16):
    vals = []
    for c in range(1, min(ws.max_column+1, 30)):
        v = ws.cell(r, c).value
        if v is not None:
            vals.append(f"  Col {c}({openpyxl.utils.get_column_letter(c)})={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)

# Read rows 130-165 - the mineral calculation section
print("\n=== ROWS 130-165 (mineral FU calculations) ===")
for r in range(130, 166):
    vals = []
    for c in range(1, min(ws.max_column+1, 30)):
        v = ws.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)

# Read rows 280-300 - the final result section
print("\n=== ROWS 280-300 (final results) ===")
for r in range(280, 301):
    vals = []
    for c in range(1, min(ws.max_column+1, 30)):
        v = ws.cell(r, c).value
        if v is not None:
            col_l = openpyxl.utils.get_column_letter(c)
            vals.append(f"  {col_l}{r}={v}")
    if vals:
        print(f"Row {r}:")
        for v in vals: print(v)
