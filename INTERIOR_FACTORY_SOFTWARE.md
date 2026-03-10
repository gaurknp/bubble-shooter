# Interior Factory Software Starter (Python)

This starter app combines five modules into one desktop tool:

1. **AutoCAD quantity extractor** (imports CSV exports from drawings)
2. **BOM calculator** (applies waste % to extracted quantities)
3. **Production planner** (creates day-wise schedule from BOM)
4. **Inventory tracker** (maintains stock, reorder level, adjustments)
5. **Dashboard & report** (live metrics + markdown report export)

## Quick start

```bash
python3 interior_factory_software.py
```

## AutoCAD CSV format

Use a CSV with these headers:

- Required: `item` (or `layer` / `name`)
- Required: `quantity` (or `qty`)
- Optional: `unit` (defaults to `nos`)

Example:

```csv
item,quantity,unit
Plywood 18mm,20,sheets
Laminate White,45,sqm
Edge Band 2mm,120,m
```

## Build EXE (Windows)

### Option A: one-command build script

1. Open **Command Prompt** in this project folder.
2. Run:

```bat
build_exe.bat
```

This installs `pyinstaller` automatically (if missing) and builds:

- `dist\InteriorFactoryStarter.exe`

### Option B: manual PyInstaller command

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name InteriorFactoryStarter interior_factory_software.py
```

Output executable:

- `dist/InteriorFactoryStarter.exe`

### If Windows blocks the EXE

- Right-click EXE -> **Properties** -> **Unblock** (if shown).
- Or build in a normal writable folder like `C:\Projects\...`.

## Data storage

The app creates `interior_factory.db` in the working directory.
