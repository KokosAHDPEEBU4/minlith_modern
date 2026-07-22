import zipfile
import re

xlsx_path = r"C:\Users\kokos\Desktop\Lene\MINLITH1.xlsx"

with zipfile.ZipFile(xlsx_path, 'r') as z:
    # List all files
    print("=== FILES IN XLSX ===")
    for name in z.namelist():
        print(f"  {name}")
    
    # Read vbaProject.bin if it exists
    vba_files = [n for n in z.namelist() if 'vba' in n.lower()]
    print(f"\nVBA files: {vba_files}")
    
    # Try to read any XML files that might contain macro data
    for name in z.namelist():
        if 'vmlDrawing' in name or 'activeX' in name or 'control' in name:
            try:
                content = z.read(name).decode('utf-8', errors='replace')
                print(f"\n=== {name} (first 2000 chars) ===")
                print(content[:2000])
            except:
                pass
