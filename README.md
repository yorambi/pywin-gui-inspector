# pywin-gui-inspector

A Windows GUI inspection, automation, and recording toolkit built on
[Pywinauto](https://pywinauto.readthedocs.io/),
[EasyOCR](https://github.com/JaidedAI/EasyOCR), and
[PyAutoGUI](https://github.com/asweigart/pyautogui).

**Inspect** any running application's UI element tree, **export** the results
to JSON, **automate** from the export or live, **record** your own interactions
and replay them as a Python script.

---

## Repository Structure

```
pywin-gui-inspector/
├── gui_detector.py   # CLI — inspect windows, OCR, image-search, JSON export
├── gui_helper.py     # Library — load JSON exports, drive automation (GUISession, ScriptWriter)
├── gui_live.py       # Library — live automation without a snapshot (LiveSession, UIPath)
├── gui_recorder.py   # App — system-tray recorder → generates gui_live.py scripts
└── ExampleScripts/   # Nine worked examples
```

| File | Purpose |
|---|---|
| `gui_detector.py` | Inspect any window and produce a structured JSON export |
| `gui_helper.py` | Load exports and automate via element tree, OCR, or image match |
| `gui_live.py` | Automate live against the running UIA tree — no snapshot needed |
| `gui_recorder.py` | Record your mouse and keyboard → output a ready-to-run script |

---

## Features

### `gui_detector.py` — Inspector CLI
- **Interactive / PID / title mode** — pick or target any running window
- **Full element tree** — name, control type, automation ID, rect, visibility, handle, PID, framework
- **Watch mode** — polls a window and prints live element diffs
- **EasyOCR text search** — `--find "Save"` locates any visible text with screen coordinates
- **Image template search** — `--image icon.png` finds pixel-matched controls
- **JSON export** — element tree + OCR + image results in one file
- **Auto UAC elevation** — requests admin rights on launch, falls back gracefully

### `gui_helper.py` — Automation Library (JSON-based)
- **`GUISession`** — loads a JSON export and drives automation
- **Three-layer smart click** — element tree → OCR → image, in priority order
- **`ScriptWriter`** — generates `gui_live.py` scripts from plain-English instructions
- **Standalone tree helpers** — `find_by_name`, `find_all`, `flatten_tree`, and more

### `gui_live.py` — Live Automation Library
- **`LiveSession`** — connects directly to the running UIA tree, no JSON snapshot required
- **Path syntax** — `"Window||Window->Button||Button"` with wildcards (`*`) and regex
- **`UIPath` context** — `with s.path("App||Window"):` scopes all calls inside the block
- **Grid addressing** — `#[row,col]` picks from a group of matching elements
- **`wait_is_ready`** — waits for enabled + visible + cursor not busy before clicking
- **`OCRWrapper`** — EasyOCR results usable as drop-in UIA elements
- **`set_text` / `set_combobox`** — reliable text entry (triple-click + Ctrl+A)
- **`menu_click`** — `"File->Save As->PDF"` multi-level menu navigation
- **App lifecycle** — `start_application`, `connect_application`, `focus`, `close`

### `gui_recorder.py` — Background Recorder
- **System tray icon** — sits in the Windows tray until you need it
- **Start hotkey** — press **F7** (configurable) to begin recording
- **Stop hotkey** — press **F9** (configurable) to stop and save
- **Live element highlight** — green border tracks the element under your cursor
- **Path tooltip** — floating label shows the element's UIA path as you hover
- **Records** — left/right clicks, keyboard input, hotkeys (Ctrl+S, etc.)
- **Generates** — a complete, ready-to-run `gui_live.py` script
- **Tray menu** — Start / Stop / Cancel / Open last script / Exit

---

## Requirements

| | |
|---|---|
| OS | Windows only |
| Python | 3.9 or later |

### Install

**Core inspection and JSON-based automation:**
```bash
pip install pywinauto pyautogui
```

**OCR features (`--ocr`, `--find`, `OCRWrapper`):**
```bash
pip install easyocr Pillow
```

**Image template search (`--image`):**
```bash
pip install opencv-python
```

**Recorder and live-mode extras:**
```bash
pip install keyboard pystray
```

**Everything at once:**
```bash
pip install pywinauto pyautogui easyocr Pillow opencv-python keyboard pystray
```

---

## Quickstart

### 1 — Inspect a window and export to JSON

```bash
# Interactive — pick from all open windows
python gui_detector.py --export dump.json

# By title, with OCR scan
python gui_detector.py --title "Notepad" --ocr --export notepad.json

# By PID, with image search
python gui_detector.py --pid 1234 --image save_icon.png --export dump.json
```

### 2 — Automate from the export (`GUISession`)

```python
from gui_helper import GUISession

s = GUISession("notepad.json")
s.click_by_name("File")
s.click_by_name("Save As")
s.type_into("File name:", "report.txt")
s.smart_click("Save")            # tries tree → OCR → image automatically
```

### 3 — Generate a script from plain English (`ScriptWriter`)

```python
from gui_helper import ScriptWriter

sw = ScriptWriter("notepad.json")
sw.preview(
    "click File, click Save As, "
    "type report.txt into File name:, click Save"
)
```

Output:
```python
s.click_by_auto_id('file_menu')
s.click_ocr('Save As')
s.type_into('File name:', 'report.txt')
s.click_by_auto_id('btn_save')
```

### 4 — Live automation without a snapshot (`LiveSession`)

```python
from gui_live import connect_application

s = connect_application(title="Notepad")
s.summary()

# Path syntax: "Name||ControlType->Child||Type"
s.menu_click("File->Save As")
s.set_text("File name:||Edit", "report.txt")
s.click("Save||Button")

# Scope all calls to a container with UIPath
with s.path("Untitled - Notepad||Window"):
    s.click("Edit||MenuItem")
    s.click("Find||MenuItem")
```

### 5 — Record interactions and replay them (`gui_recorder.py`)

```bash
python gui_recorder.py                 # saves to recorded.py
python gui_recorder.py -o login.py     # custom output file
python gui_recorder.py --start F6 --stop F8   # custom hotkeys
```

1. A **tray icon** appears in the system tray (bottom-right)
2. Press **F7** (or right-click tray → Start) to begin recording
3. **Hover** over elements to see the green highlight and path tooltip
4. **Click and type** normally — every action is captured
5. Press **F9** (or right-click tray → Stop) to stop and save the script

The generated script uses `gui_live.py` calls and is ready to run immediately.

---

## `gui_detector.py` — CLI Reference

```
python gui_detector.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--pid PID` | — | Inspect by process ID |
| `--title TEXT` | — | Inspect by partial window title |
| `--dump` | — | List all open windows |
| `--watch PID` | — | Poll a window and print element diffs |
| `--depth N` | `8` | Max recursion depth |
| `--export FILE.json` | — | Save results to JSON |
| `--interval SECS` | `1.0` | Polling interval for `--watch` |
| `--ocr` | — | Full EasyOCR scan of the window |
| `--find TEXT` | — | OCR-search for a specific string |
| `--image FILE.png` | — | PyAutoGUI image template search |
| `--confidence N` | `0.9` | Match threshold for `--image` |

---

## `gui_helper.py` — Library Reference

### `GUISession`

```python
from gui_helper import GUISession

s = GUISession("dump.json", click_delay=0.3, move_duration=0.1)
s.print_summary()
```

| Method | Description |
|---|---|
| `s.click_by_name(name)` | Click element by name (substring) |
| `s.click_by_auto_id(id)` | Click by exact automation ID (most robust) |
| `s.type_into(name, text)` | Find Edit field and type |
| `s.click_ocr(query)` | Click by visible OCR text |
| `s.click_image(template)` | Click by pixel template match |
| `s.smart_click(query)` | Auto-fallback: tree → OCR → image |
| `s.all_buttons()` | List all Button elements |
| `s.all_edits()` | List all Edit controls |
| `s.summary()` | Return summary dict |

### `ScriptWriter`

```python
from gui_helper import ScriptWriter

sw = ScriptWriter("dump.json")
sw.preview("click File, click Save As, type report.txt into File name:, click Save")
sw.write("...", output="my_script.py")
script = sw.generate("...")
```

Supported step syntax: `click`, `type X into Y`, `press`, `hotkey`, `wait N seconds`,
`screenshot as file.png`, `open the X menu`, `close`.

---

## `gui_live.py` — Live Session Reference

### Connecting

```python
from gui_live import connect_application, start_application

s = connect_application(title="Notepad")       # attach to running app
s = connect_application(pid=1234)
s = start_application("notepad.exe")           # launch and attach
```

### Path syntax

| Pattern | Matches |
|---|---|
| `"OK\|\|Button"` | element named "OK" of type Button |
| `"\|\|Edit"` | any Edit control |
| `"Toolbar\|\|ToolBar->Save\|\|Button"` | Save button inside Toolbar |
| `"*->\|\|Button"` | wildcard level, then any Button |
| `"RegEx: .*Save.*\|\|Button"` | regex name match |
| `"\|\|Button#[1,2]"` | row 1, col 2 of matched Buttons |
| `"\|\|Slider%(0.8,0)"` | click 80% right of slider center |

### `LiveSession` methods

| Method | Description |
|---|---|
| `s.click(path)` | Click first matching element |
| `s.double_click(path)` | Double-click |
| `s.right_click(path)` | Right-click |
| `s.set_text(path, text)` | Triple-click + Ctrl+A then type |
| `s.set_combobox(path, text)` | Open dropdown and select |
| `s.menu_click("File->Save As")` | Multi-level menu navigation |
| `s.send_keys(text)` | Type a string |
| `s.hotkey("ctrl", "s")` | Press a keyboard shortcut |
| `s.smart_click(query)` | Tree → OCR fallback |
| `s.ocr_find(query)` | Return `OCRWrapper` for first OCR match |
| `s.ocr_click(query)` | Click first OCR match |
| `s.drag_and_drop(src, tgt)` | Drag from one element to another |
| `s.focus()` | Bring window to foreground |
| `s.close()` | Close the application |
| `s.path(prefix)` | `UIPath` context manager |
| `s.find(path)` | Return element or `None` |
| `s.find_all(path)` | Return list of matching elements |

---

## `gui_recorder.py` — Recorder Reference

```bash
python gui_recorder.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `-o / --output` | `recorded.py` | Output script path |
| `--start KEY` | `f7` | Start-recording hotkey |
| `--stop KEY` | `f9` | Stop-recording hotkey |

### Tray icon states

| Icon | State |
|---|---|
| Green circle (🟢) | Idle — waiting |
| Red circle (🔴) | Recording |

### Tray menu

| Item | Action |
|---|---|
| ▶ Start Recording (F7) | Begin capturing |
| ■ Stop Recording (F9) | Stop and write script |
| ✕ Cancel | Stop and discard all events |
| 📄 Open last script | Open output file in Notepad |
| Exit | Quit |

### Controls

| Key | Action |
|---|---|
| **F7** | Start recording |
| **F9** | Stop and save |
| **Esc** | Cancel (discard events) |

---

## JSON Export Format

```json
{
  "element_tree": {
    "name": "Untitled - Notepad",
    "control_type": "Window",
    "automation_id": "",
    "rectangle": "(100, 200, 900, 700)",
    "is_visible": true,
    "is_enabled": true,
    "process_id": 1234,
    "depth": 0,
    "children": [ { "...": "..." } ]
  },
  "ocr_results": [
    { "text": "Save", "confidence": 96.3,
      "rect": { "left": 412, "top": 310, "right": 463, "bottom": 328 } }
  ],
  "image_results": [
    { "template": "save_icon.png", "confidence": 0.9,
      "center": { "x": 437, "y": 319 },
      "rect": { "left": 412, "top": 304, "right": 462, "bottom": 334 } }
  ]
}
```

---

## How It Works

```
gui_detector.py      inspect → walk UIA tree → screenshot → OCR / image search → JSON
gui_helper.py        load JSON → search tree / OCR / images → pixel click / live click
gui_live.py          connect live → path-based UIA search → TTL cache → smart click
gui_recorder.py      tray + hotkeys → track cursor → UIA lookup → record events → script
```

**Three search layers (used across all files):**

| Priority | Layer | Best for |
|---|---|---|
| 1 | UIA element tree | Apps with automation IDs; most stable |
| 2 | OCR (EasyOCR) | Custom-rendered text, Electron apps |
| 3 | Image template | Icon-only buttons, pixel-matched controls |

---

## Supported Frameworks

Pywinauto UIA works with Win32, WinForms, WPF, Qt, Electron/CEF, MFC, and UWP.
Image and OCR features work on **any application** (pixel-level, framework-agnostic).

---

## Limitations

- **Windows only** — Pywinauto requires the Windows accessibility APIs
- **Protected processes** — Task Manager and system utilities need elevation (auto-requested)
- **Electron / web UIs** — sparse automation IDs; use `--depth 3` and OCR fallback
- **EasyOCR speed** — 2–5 s on CPU; a CUDA GPU reduces it to under 1 s
- **Image matching** — breaks if DPI or zoom changes; capture at 100% scale

---

## License

MIT — free to use, modify, and distribute.