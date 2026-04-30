# OCR helper functions

Standalone functions for working with OCR results from a
`gui_detector.py --ocr` export.

```python
from gui_helper import find_ocr, find_all_ocr, ocr_center
```

OCR results are produced by EasyOCR and stored in the `ocr_results` key of
the JSON export. Each result is a dict:

```python
{
    "text":       "Save",
    "confidence": 96.3,       # 0–100
    "rect": {
        "left": 412, "top": 310,
        "right": 463, "bottom": 328
    }
}
```

---

## Functions

### `find_ocr(results, query, exact=False) → dict | None`

Return the first OCR result whose text contains `query` (case-insensitive
substring by default).

```python
ocr_results = data["ocr_results"]

result = find_ocr(ocr_results, "Save")
result = find_ocr(ocr_results, "OK", exact=True)  # exact match only
```

### `find_all_ocr(results, query) → list[dict]`

Return all OCR results whose text contains `query`.

```python
matches = find_all_ocr(ocr_results, "Save")
for m in matches:
    print(m["text"], m["confidence"])
```

### `ocr_center(ocr_result) → tuple[int, int]`

Return the center `(x, y)` screen pixel of an OCR result dict.

```python
result = find_ocr(ocr_results, "Submit")
if result:
    x, y = ocr_center(result)
    pyautogui.click(x, y)
```

---

## Example

```python
from gui_helper import load_export, find_all_ocr, ocr_center
import pyautogui

data = load_export("dump.json")
ocr  = data.get("ocr_results", [])

# Print all detected text with position and confidence
for r in ocr:
    x, y = ocr_center(r)
    print(f"  [{r['confidence']:5.1f}%]  {r['text']!r:30}  center=({x},{y})")

# Click the first result matching "Cancel"
result = find_all_ocr(ocr, "Cancel")
if result:
    x, y = ocr_center(result[0])
    pyautogui.click(x, y)
```