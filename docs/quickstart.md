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

## Step 3 — Live automation without a snapshot (`LiveSession`)

For scripts that need to run against a live, changing UI — or when you
don't want the JSON round-trip — use `gui_live.py`:

```python
from gui_live import connect_application

s = connect_application(title="Notepad")

# Path syntax: "Name||ControlType->Child||Type"
s.menu_click("File->Save As")
s.set_text("File name:||Edit", "report.txt")
s.click("Save||Button")

# Scope all calls to a window prefix
with s.path("Untitled - Notepad||Window"):
    s.click("Edit||MenuItem")
```

See {doc}`live-mode` for the full path syntax and {doc}`api/live-session`
for the complete API.

---

## Step 4 — Record and replay (`gui_recorder.py`)

The fastest way to build an automation script is to just do the task once
and let the recorder capture it:

```bash
python gui_recorder.py -o login_flow.py
```

1. A **tray icon** appears in the system tray
2. Press **F7** to start recording
3. Hover to see the green highlight and path tooltip
4. Do the UI actions you want to automate
5. Press **F9** to stop — the script is written to `login_flow.py`

The generated script uses `gui_live.py` calls and runs immediately after
you update the `connect_application(title="...")` line.

See {doc}`recorder` for full controls and options.

---

## What next?

- {doc}`cli-reference` — all `gui_detector.py` flags
- {doc}`live-mode` — live-mode path syntax and features
- {doc}`recorder` — recorder controls and generated script format
- {doc}`api/gui-session` — full `GUISession` API
- {doc}`api/live-session` — full `LiveSession` API
- {doc}`examples/index` — nine complete worked examples