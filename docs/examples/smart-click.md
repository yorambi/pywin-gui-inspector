# 05 — Smart click

**Script:** `ExampleScripts/05_smart_click.py`

Demonstrates `smart_click` — the automatic three-layer fallback that tries
every search method in priority order, so you don't need to know in advance
which layer will work.

## Run

```bash
python ExampleScripts/05_smart_click.py
```

## Priority order

```
1. Element tree  (name match)    → click_by_name / click_by_auto_id
2. OCR results   (text match)    → click_ocr
3. Image results (filename match) → click_image
```

## What it demonstrates

```python
from gui_helper import GUISession

s = GUISession("myapp.json", click_delay=0.5)

targets = [
    "File",           # found in element tree
    "Save",           # found in element tree or OCR
    "toolbar.png",    # found in image results
    "Submit",         # OCR fallback for custom-rendered button
    "Nonexistent",    # warns and returns False — no crash
]

for target in targets:
    success = s.smart_click(target)
    print("✓ clicked" if success else "✗ not found")
```

## Custom fallback chain

Use this pattern when you want explicit control over the fallback order:

```python
if   s.click_by_name("OK", exact=True): print("tree")
elif s.click_ocr("OK", exact=True):     print("ocr")
elif s.click_image("ok_button.png"):    print("image")
else:                                   print("not found")
```