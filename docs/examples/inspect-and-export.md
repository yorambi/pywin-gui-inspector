# 01 — Inspect and export

**Script:** `ExampleScripts/01_inspect_and_export.py`

Loads a JSON export and prints a high-level summary: window name, PID,
element type counts, and any OCR results.

## Prerequisites

```bash
python gui_detector.py --title "Notepad" --ocr --export dump.json
```

## Run

```bash
python ExampleScripts/01_inspect_and_export.py
```

## What it does

```python
import json
from pathlib import Path

EXPORT = "dump.json"

with open(EXPORT, encoding="utf-8") as f:
    data = json.load(f)

tree        = data.get("element_tree", data)
ocr_results = data.get("ocr_results", [])

print(f"Window   : {tree.get('name')!r}")
print(f"PID      : {tree.get('process_id')}")
```

It then counts every control type found in the tree:

```
Window   : 'Untitled - Notepad'
PID      : 1234
Framework: Win32
Rect     : (100, 200, 900, 700)
OCR hits : 6

Element types found:
  Edit                 1
  MenuItem             4
  MenuBar              1
  StatusBar            1
  Window               1
```