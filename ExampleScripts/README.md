# ExampleScripts

Ready-to-run reference scripts for the `pywin-gui-inspector` toolkit.
Each script is self-contained, heavily commented, and covers one specific
feature or pattern. Run them in order or jump to whichever example matches
your use case.

---

## Prerequisites

All scripts expect:
- `gui_helper.py` to be in the **parent directory** (i.e. `../gui_helper.py`)
- A JSON export produced by `gui_detector.py` (each script tells you which command to run)

Install dependencies once:
```bash
pip install pywinauto easyocr Pillow pyautogui opencv-python
```

---

## Scripts

| File | What it shows |
|---|---|
| `01_inspect_and_export.py` | Run `gui_detector.py` to export a window; load and summarise the JSON |
| `02_click_and_type.py` | Click elements and type text using the Pywinauto element tree |
| `03_ocr_text_search.py` | Find and click buttons by visible text using EasyOCR results |
| `04_image_template_search.py` | Find and click icon-only controls using PyAutoGUI image matching |
| `05_smart_click.py` | Auto-resolve clicks across all three layers with `smart_click` |
| `06_script_writer.py` | Generate a Python automation script from plain-English instructions |
| `07_bulk_element_processing.py` | Traverse the tree, fill forms, filter elements in bulk |
| `08_watch_mode.py` | Poll a live window and react when a specific element appears |
| `09_full_workflow.py` | End-to-end workflow combining all layers and techniques |

---

## Typical workflow

```
1. Inspect a window and export to JSON
   ─────────────────────────────────────────────────────────────────
   python gui_detector.py --title "MyApp" --ocr --export dump.json

2. (Optional) Generate an automation script from plain English
   ─────────────────────────────────────────────────────────────────
   python gui_helper.py dump.json "click Login, type admin into Username, press Enter" login.py

3. Run the generated or hand-written script
   ─────────────────────────────────────────────────────────────────
   python login.py
```

---

## Search layer priority

Every `click_by_*` method and `smart_click` resolves targets in this order:

```
1. automation_id   → click_by_auto_id(live=True)   most reliable
2. element name    → click_by_name()
3. OCR text        → click_ocr()
4. image template  → click_image()
5. not found       → smart_click() warns and returns False
```

Use the highest layer that works for your target application.
Electron apps and custom-drawn UIs often need layers 3 or 4.
