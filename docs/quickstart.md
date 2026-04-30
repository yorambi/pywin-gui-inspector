# Quickstart

## Step 1 — Inspect a window and export to JSON

Open the application you want to automate, then run `gui_detector.py` against
it.

**Interactive mode** — lists all open windows, you pick one:

```bash
python gui_detector.py --export dump.json
```

**By partial window title:**

```bash
python gui_detector.py --title "Notepad" --export notepad.json
```

**By process ID** (find PID in Task Manager):

```bash
python gui_detector.py --pid 1234 --export dump.json
```

**With OCR and image search enabled at the same time:**

```bash
python gui_detector.py --title "Notepad" --ocr --image save_icon.png --export notepad.json
```

The output is a structured JSON file containing the full UI element tree, OCR
results, and image matches. See {doc}`json-format` for the schema.

---

## Step 2 — Automate with `GUISession`

Load the export and start interacting:

```python
from gui_helper import GUISession

s = GUISession("notepad.json")
s.print_summary()
```

```
────────────────────────────────────────────────────────────
  GUISession: 'Untitled - Notepad'  (PID 1234)
────────────────────────────────────────────────────────────
  Export file    : notepad.json
  Total elements : 42
  Buttons        : 3
  Edit fields    : 1
  OCR results    : 18
  Image matches  : 1
────────────────────────────────────────────────────────────
```

### Clicking elements

```python
# By name — substring match, case-insensitive
s.click_by_name("Save")

# By automation ID — most reliable, exact match
s.click_by_auto_id("btn_save")

# By visible text found by OCR
s.click_ocr("Cancel")

# By pixel template image
s.click_image("save_icon.png")

# Automatic — tries all three layers in order
s.smart_click("Save")
```

### Typing text

```python
s.type_into("File name:", "report.txt")
```

### Three-layer priority

All search and click methods follow the same priority order:

| Priority | Layer | Best for |
|---|---|---|
| 1 | Element tree | Apps with stable automation IDs |
| 2 | OCR results | Custom-rendered text, Electron apps |
| 3 | Image template | Icon-only buttons, pixel-matched controls |

---

## What next?

- See {doc}`cli-reference` for all `gui_detector.py` flags
- See {doc}`api/gui-session` for the full `GUISession` API
- Browse the {doc}`examples/index` for complete worked examples