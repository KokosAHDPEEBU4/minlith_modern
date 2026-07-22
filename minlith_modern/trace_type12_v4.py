import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx", data_only=False)
ws = wb.worksheets[6]  # Нач+Type 12

# Check named ranges
print("=== NAMED RANGES ===")
if wb.defined_names:
    for name, defn in wb.defined_names.items():
        print(f"  {name} = {defn.attr_text}")

# Key: I need to find where ill, or, chl, q, kn are computed
# They are referenced in rows 147+155+162 areas
# Let me search ALL cells for formulas containing these names

print("\n=== SEARCHING FOR ill_, or_, chl_, q_, kn_ formulas ===")
for r in range(1, ws.max_row+1):
    for c in range(1, ws.max_column+1):
        v = ws.cell(r, c).value
        if isinstance(v, str) and v.startswith('='):
            vl = v.lower()
            if any(x in vl for x in ['ill', 'chl', 'kn', '"or"', '_or']):
                col_l = openpyxl.utils.get_column_letter(c)
                print(f"  {col_l}{r}={v}")
