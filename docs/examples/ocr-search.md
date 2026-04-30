# 03 — OCR text search

**Script:** `ExampleScripts/03_ocr_text_search.py`

Uses EasyOCR results to find and click elements by their visible text. Useful
for custom-rendered buttons, Electron apps, and any control without a stable
automation ID.

## Prerequisites

```bash
python gui_detector.py --title "MyApp" --ocr --export myapp.json
```

## Run

```bash
python ExampleScripts/03_ocr_text_search.py
```

## What it demonstrates

```python
from gui_helper import GUISession, find_all_ocr, ocr_center

s = GUISession("myapp.json")

# Print all OCR-detected text with position and confidence
for r in s.ocr_results:
    x, y = ocr_center(r)
    print(f"  [{r['confidence']:5.1f}%]  {r['text']!r:30}  center=({x},{y})")

# Click the first result matching "Submit"
s.click_ocr("Submit")

# Use exact=True to avoid partial matches
s.click_ocr("OK", exact=True)

# Fall back to smart_click if exact OCR fails
if not s.click_ocr("OK", exact=True):
    s.smart_click("OK")
```