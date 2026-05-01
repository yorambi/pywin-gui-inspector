# Quickstart

## Install

```bash
pip install -e ".[all]"
```

See {doc}`installation` for individual dependency groups.

---

## Step 1 — Inspect a window and export to JSON

Open the application you want to automate, then run the inspector:

```bash
# Interactive — lists all open windows, you pick one
python gui_detector.py --export dump.json

# By partial window title, with OCR scan
python gui_detector.py --title "Notepad" --ocr --export notepad.json

# By process ID, with image template search
python gui_detector.py --pid 1234 --image save_icon.png --export dump.json
```

The output is a structured JSON file with the full UI element tree, OCR results,
and image matches.  See {doc}`json-format` for the schema.

---

## Step 2 — Automate from the export (`GUISession`)

```python
from pywin_gui_inspector import GUISession

s = GUISession("notepad.json")
s.print_summary()
```

```text
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

### Clicking and typing

```python
s.click_by_name("File")            # substring match, case-insensitive
s.click_by_auto_id("btn_save")     # exact automation ID — most robust
s.click_ocr("Cancel")              # visible text found by EasyOCR
s.click_image("save_icon.png")     # pixel template match
s.smart_click("Save")              # auto-fallback: tree → OCR → image
s.type_into("File name:", "report.txt")
```

### Three-layer search priority

| Priority | Layer | Best for |
| --- | --- | --- |
| 1 | Element tree | Apps with stable automation IDs |
| 2 | OCR results | Custom-rendered text, Electron apps |
| 3 | Image template | Icon-only buttons, pixel-matched controls |

---

## Step 3 — Generate a script from plain English (`ScriptWriter`)

```python
from pywin_gui_inspector import ScriptWriter

sw = ScriptWriter("notepad.json")
sw.preview(
    "click File, click Save As, "
    "type report.txt into File name:, click Save"
)
sw.write("click OK", output="my_automation.py")
```

Supported step syntax: `click`, `type X into Y`, `press`, `hotkey`,
`wait N seconds`, `screenshot as file.png`, `open the X menu`, `close`.

---

## Step 4 — Live automation without a snapshot (`LiveSession`)

```python
from pywin_gui_inspector import connect_application

s = connect_application(title="Notepad")  # attach to running app
# s = start_application("notepad.exe")   # or launch and attach

s.menu_click("File->Save As")
s.set_text("File name:||Edit", "report.txt")
s.click("Save||Button")

# Scope all calls to a window with UIPath
with s.path("Untitled - Notepad||Window"):
    s.click("Edit||MenuItem")
    s.click("Find||MenuItem")
```

See {doc}`live-mode` for the full path syntax and {doc}`api/live-session`
for the complete API reference.

---

## Step 5 — Record and replay (`gui_recorder.py`)

The fastest way to build an automation script is to record it once:

```bash
python gui_recorder.py -o login_flow.py
python gui_recorder.py --start F6 --stop F8 --exit F10
```

1. A **tray icon** appears in the system tray
2. Press **F7** to start recording
3. Hover to see the green highlight and element path tooltip
4. Perform the UI actions you want to automate
5. Press **F9** to stop — the script is written immediately

The generated script uses `DesktopSession` from the package and runs without
any pre-connection setup:

```python
from pywin_gui_inspector.live import DesktopSession

s = DesktopSession()
s.click('Calculator||Window->Seven||Button')
s.click('Calculator||Window->Plus||Button')
```

See {doc}`recorder` for full controls and options.

---

## Running the tests

```bash
pytest tests/ -v
# 88 passed — pure Python, no live Windows session required
```

---

## What next?

- {doc}`cli-reference` — all `gui_detector.py` flags
- {doc}`live-mode` — live-mode path syntax and features
- {doc}`recorder` — recorder controls and generated script format
- {doc}`api/gui-session` — full `GUISession` API
- {doc}`api/live-session` — full `LiveSession` API
- {doc}`examples/index` — nine complete worked examples
