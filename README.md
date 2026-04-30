# pywin-gui-inspector

A Windows GUI inspection and automation toolkit built on [Pywinauto](https://pywinauto.readthedocs.io/), [EasyOCR](https://github.com/JaidedAI/EasyOCR), and [PyAutoGUI](https://github.com/asweigart/pyautogui).

**Inspect** any running application's UI element tree, **search** it by text or pixel template, **export** the results to JSON, and **drive** any automation script from that export using the companion helper library.

---

## Repository Structure

```
pywin-gui-inspector/
├── gui_detector.py   # CLI tool — inspect, OCR, image-search, export
├── gui_helper.py     # Python library — load exports and drive automation
└── README.md
```

| File | Purpose |
|---|---|
| `gui_detector.py` | Run from the command line to inspect a window and produce a JSON export |
| `gui_helper.py` | Import in your own scripts to load the export and interact with the UI |

---

## Features

**gui_detector.py**
- **Interactive mode** — lists all open windows and lets you pick one to inspect
- **Connect by PID or title** — target any running process directly
- **Full element tree** — recursively walks every UI control and prints a readable tree
- **Rich property extraction** — captures name, control type, class, automation ID, bounding rectangle, visibility, enabled state, handle, PID, and framework ID per element
- **Watch mode** — polls a window at a configurable interval and prints live diffs of added/removed elements
- **JSON export** — saves the full element tree, OCR results, and image matches to a single structured JSON file
- **Configurable depth** — limit recursion to avoid noise in deeply nested UIs
- **Auto UAC elevation** — requests Administrator privileges on launch; falls back gracefully if declined
- **EasyOCR text search** — screenshots the window and finds any visible text by keyword, with screen coordinates and confidence score
- **Image / template search** — finds icon-only or custom-drawn controls by supplying a reference `.png` screenshot

**gui_helper.py**
- **`GUISession`** — high-level automation session loaded from a JSON export
- **Three-layer smart click** — tries element tree → OCR → image match automatically
- **Live Pywinauto actions** — click, type, and interact with elements using stable automation IDs
- **Pixel click fallback** — PyAutoGUI clicks for when live automation is not available
- **Standalone tree helpers** — `find_by_name`, `find_by_automation_id`, `find_all`, `flatten_tree`, and more

---

## Requirements

| | Details |
|---|---|
| OS | Windows only |
| Python | 3.9+ |

### Install dependencies

**Core (required for `gui_detector.py`):**
```bash
pip install pywinauto
```

**OCR mode — `--ocr` / `--find` (and `gui_helper.py` OCR actions):**
```bash
pip install easyocr Pillow
```
> EasyOCR is a pure-Python deep-learning engine — no external binary needed. Model weights (~100 MB) are downloaded automatically on first use.

**Image / template search — `--image` (and `gui_helper.py` image actions):**
```bash
pip install pyautogui opencv-python
```

**Install everything at once:**
```bash
pip install pywinauto easyocr Pillow pyautogui opencv-python
```

> Each optional dependency group is lazy-loaded and only checked when the relevant feature is actually used.

---

## Quickstart

### Step 1 — Inspect a window and export to JSON

```bash
# By window title (partial match)
python gui_detector.py --title "Notepad" --ocr --export notepad.json

# By process ID, with image template search too
python gui_detector.py --pid 1234 --find "Save" --image save_icon.png --export dump.json

# Interactive — pick from a list of all open windows
python gui_detector.py --export dump.json
```

### Step 2 — Use the export in your automation script

```python
from gui_helper import GUISession

s = GUISession("dump.json")
s.print_summary()

# Click by element name (Pywinauto tree)
s.click_by_name("Save")

# Click by automation ID (most reliable)
s.click_by_auto_id("btn_ok")

# Type into a text field
s.type_into("File name:", "report.txt")

# Click visible text found by OCR
s.click_ocr("Cancel")

# Click an icon-only button found by image template
s.click_image("save_icon.png")

# Let the library figure out the best method automatically
s.smart_click("Save")
```

---

## gui_detector.py — CLI Reference

```
python gui_detector.py [OPTIONS]
```

### Modes

| Command | Description |
|---|---|
| `python gui_detector.py` | **Interactive** — shows all open windows, you pick one |
| `python gui_detector.py --pid 1234` | Inspect by process ID |
| `python gui_detector.py --title "Notepad"` | Inspect by partial window title |
| `python gui_detector.py --dump` | List every open top-level window |
| `python gui_detector.py --watch 1234` | Watch a PID for GUI changes in real time |

> `--pid`, `--title`, `--dump`, and `--watch` are mutually exclusive.

### Options

| Flag | Default | Description |
|---|---|---|
| `--pid PID` | — | Connect by process ID |
| `--title TEXT` | — | Connect by partial window title |
| `--dump` | — | Dump all open windows to console |
| `--watch PID` | — | Poll a window and print element diffs |
| `--depth N` | `8` | Maximum recursion depth |
| `--export FILE.json` | — | Save results to a JSON file |
| `--interval SECONDS` | `1.0` | Polling interval for `--watch` |
| `--ocr` | — | Full EasyOCR scan of the window after Pywinauto inspection |
| `--find TEXT` | — | OCR-search for a specific text string (implies `--ocr`) |
| `--image FILE.png` | — | Search the screen for a reference image using PyAutoGUI |
| `--confidence N` | `0.9` | Match threshold for `--image` (0.0–1.0) |

### Examples

**List all open windows:**
```bash
python gui_detector.py --dump
```
```
──────────────────────────────────────────────────────────────────────
  Found 12 open window(s)
──────────────────────────────────────────────────────────────────────
  [  1] PID=1234    handle=65842     title='Untitled - Notepad'
  [  2] PID=5678    handle=131174    title='Task Manager'
──────────────────────────────────────────────────────────────────────
```

**Inspect Notepad by title:**
```bash
python gui_detector.py --title "Notepad"
```
```
[+] Inspecting: 'Untitled - Notepad'

[Window] 'Untitled - Notepad'  class='Notepad'  rect=(100, 200, 900, 700)
  [MenuBar] '<no name>'  rect=(100, 200, 900, 221)
    [MenuItem] 'File'  auto_id='Item 1'
    [MenuItem] 'Edit'  auto_id='Item 2'
  [Edit] 'Text Editor'  class='Edit'  rect=(100, 221, 900, 700)
  [StatusBar] '<no name>'  class='msctls_statusbar32'
```

**Find visible button text with OCR:**
```bash
python gui_detector.py --pid 1234 --find "Save"
```
```
[*] OCR search for 'Save' in window (PID 1234)…

──────────────────────────────────────────────────────────────────────
  OCR — 2 result(s) matching 'Save'
──────────────────────────────────────────────────────────────────────
  [ 96%]  'Save'                          (412,310)→(463,328)
  [ 91%]  'Save As'                       (412,332)→(490,350)
──────────────────────────────────────────────────────────────────────
```

**Find an icon-only button by image template:**
```bash
python gui_detector.py --pid 1234 --image save_icon.png
```
```
[*] Image search for template 'save_icon.png'  (confidence=0.9)…

──────────────────────────────────────────────────────────────────────
  Image search — 1 match(es) for 'save_icon.png'
──────────────────────────────────────────────────────────────────────
  [1]  center=(437,319)  rect=(412,304)→(462,334)
──────────────────────────────────────────────────────────────────────
```

**Watch a window for UI changes:**
```bash
python gui_detector.py --watch 1234 --interval 0.5
```
```
[*] Watching PID 1234 every 0.5s  (Ctrl-C to stop)

  [*] Baseline: 18 element(s)
  [=] No change
  [+] New elements:     ['Save As', 'File name:', 'Cancel']
  [-] Removed elements: ['Save As', 'File name:', 'Cancel']
```

**All three search modes combined:**
```bash
python gui_detector.py --pid 1234 --find "Save" --image save_icon.png --export dump.json
```

---

## gui_helper.py — Library Reference

`gui_helper.py` loads a JSON export from `gui_detector.py` and provides a clean API for automation scripts. No separate installation — just place it alongside your script.

### Self-test

Pass any export directly to verify the file loaded correctly and see what was captured:
```bash
python gui_helper.py dump.json
```

### `GUISession`

The main class. Loads an export and exposes all interaction methods.

```python
from gui_helper import GUISession

s = GUISession("dump.json")
s.print_summary()
```
```
────────────────────────────────────────────────────────────
  GUISession: 'Untitled - Notepad'  (PID 1234)
────────────────────────────────────────────────────────────
  Export file    : dump.json
  Total elements : 42
  Buttons        : 3
  Edit fields    : 1
  OCR results    : 18
  Image matches  : 1
────────────────────────────────────────────────────────────
```

#### Constructor

```python
GUISession(
    export_path,          # path to the JSON file from gui_detector.py
    click_delay=0.3,      # pause (seconds) after every click
    move_duration=0.1,    # mouse move speed for PyAutoGUI
)
```

#### Element tree methods

| Method | Description |
|---|---|
| `s.find(name)` | Find an element node by name; returns dict or `None` |
| `s.find_auto_id(auto_id)` | Find by exact automation ID |
| `s.click_by_name(name)` | Click the first element matching *name* |
| `s.click_by_auto_id(auto_id)` | Click by automation ID |
| `s.click_by_name(name, live=True)` | Use Pywinauto `click_input()` instead of pixel click |
| `s.type_into(name, text)` | Click an Edit field and type text |
| `s.type_into(name, text, clear_first=False)` | Type without clearing the field first |
| `s.all_buttons()` | List all enabled visible Button elements |
| `s.all_edits()` | List all Edit (text input) elements |
| `s.all_checkboxes()` | List all CheckBox elements |
| `s.all_of_type(control_type)` | List all elements of any control type |

#### OCR methods

| Method | Description |
|---|---|
| `s.click_ocr(query)` | Click the screen position of the first OCR match for *query* |
| `s.click_ocr(query, exact=True)` | Require an exact text match |
| `s.ocr_text_at(query)` | Return the exact OCR string matched by *query* |
| `s.all_ocr_text()` | Return a flat list of all detected OCR strings |

#### Image methods

| Method | Description |
|---|---|
| `s.click_image(template)` | Click the center of the first image template match |
| `s.click_image()` | Click the first match regardless of template filename |

#### Smart click

```python
s.smart_click("Save")
```

Tries all three layers automatically in priority order:
1. Element tree (name match)
2. OCR results (text match)
3. Image results (template filename match)

Returns `True` on first success, `False` if nothing found in any layer.

#### Introspection

```python
s.summary()         # dict with element counts, OCR count, image count
s.print_summary()   # prints the summary table
repr(s)             # GUISession(window='...', pid=..., elements=..., ...)
```

---

### Standalone helper functions

These work directly on the tree dict without a session object.

```python
from gui_helper import (
    load_export, flatten_tree,
    find_by_name, find_by_automation_id, find_by_control_type, find_all,
    element_rect, element_center,
    find_ocr, find_all_ocr, ocr_center,
    find_image_result, image_center,
    print_flat,
)
```

| Function | Description |
|---|---|
| `load_export(path)` | Load a JSON export and return the raw dict |
| `flatten_tree(node)` | Return a flat list of every element, depth-first |
| `find_by_name(node, name)` | Depth-first search by name (substring, case-insensitive) |
| `find_by_automation_id(node, id)` | Find by exact automation ID |
| `find_by_control_type(node, type)` | Find the first element of a given control type |
| `find_all(node, name=, control_type=, enabled_only=, visible_only=)` | Collect all elements matching all supplied filters |
| `element_rect(node)` | Return `(left, top, right, bottom)` from a node |
| `element_center(node)` | Return `(x, y)` center of a node |
| `find_ocr(results, query)` | Find the first OCR result containing *query* |
| `find_all_ocr(results, query)` | Find all OCR results containing *query* |
| `ocr_center(ocr_result)` | Return `(x, y)` center of an OCR result |
| `find_image_result(results, template)` | Find the first image result by template filename |
| `image_center(image_result)` | Return `(x, y)` center of an image result |
| `print_flat(node)` | Print a flat readable list of all elements |

### Usage patterns

**Pattern 1 — Automate a Save dialog:**
```python
from gui_helper import GUISession

s = GUISession("dump.json")
s.type_into("File name:", "report.txt")
s.click_by_name("Save")
```

**Pattern 2 — Drive by automation ID (most robust):**
```python
s = GUISession("dump.json")
s.click_by_auto_id("FileNameBox", live=True)   # Pywinauto click_input
s.click_by_auto_id("SaveButton",  live=True)
```

**Pattern 3 — OCR fallback for unlabelled controls:**
```python
s = GUISession("dump.json")
if not s.click_by_name("Submit"):     # try element tree first
    s.click_ocr("Submit")             # fall back to OCR
```

**Pattern 4 — Bulk element processing:**
```python
from gui_helper import load_export, find_all, element_center

data = load_export("dump.json")
tree = data["element_tree"]

for edit in find_all(tree, control_type="Edit"):
    x, y = element_center(edit)
    print(f"{edit['name']:30}  auto_id={edit['automation_id']}  center=({x},{y})")
```

**Pattern 5 — Filter with list comprehensions:**
```python
from gui_helper import load_export, flatten_tree

data  = load_export("dump.json")
nodes = flatten_tree(data["element_tree"])

visible_buttons = [
    n for n in nodes
    if n.get("control_type") == "Button"
    and n.get("is_visible")
    and n.get("is_enabled")
]
```

---

## JSON Export Format

When `--export` is used the output contains up to three sections:

```json
{
  "element_tree": {
    "name": "Untitled - Notepad",
    "control_type": "Window",
    "class_name": "Notepad",
    "automation_id": "",
    "rectangle": "(100, 200, 900, 700)",
    "is_visible": true,
    "is_enabled": true,
    "handle": 65842,
    "process_id": 1234,
    "framework_id": "Win32",
    "depth": 0,
    "children": [ { "name": "", "control_type": "MenuBar", "...": "..." } ]
  },
  "ocr_results": [
    {
      "text": "Save",
      "confidence": 0.963,
      "rect": { "left": 412, "top": 310, "right": 463, "bottom": 328 }
    }
  ],
  "image_results": [
    {
      "template": "save_icon.png",
      "confidence": 0.9,
      "center": { "x": 437, "y": 319 },
      "rect": { "left": 412, "top": 304, "right": 462, "bottom": 334 }
    }
  ]
}
```

`ocr_results` is present only when `--ocr` or `--find` was used.
`image_results` is present only when `--image` was used.
When `--dump` is used the output is a flat JSON array of window objects instead.

---

## Supported Frameworks

The Pywinauto UIA backend works with:

- Native Win32 applications
- WinForms / WPF (.NET)
- Qt (via Windows accessibility APIs)
- Electron / CEF-based apps
- MFC applications

The `--image` template search and `gui_helper.py` image methods work on **any application** regardless of framework, since they match pixels directly on screen.

---

## Administrator Privileges

`gui_detector.py` automatically requests elevated privileges on launch:

| Situation | Behaviour |
|---|---|
| Already running as Administrator | Continues silently |
| UAC prompt → **Yes** | Elevated child launches with all original arguments; parent exits |
| UAC prompt → **No** | Prints a warning and continues without admin rights |
| UAC unavailable | Same — falls back to normal execution |

> **Why it matters:** Windows blocks non-elevated processes from inspecting elevated ones (Task Manager, installers, system utilities). For everyday apps like Notepad or Chrome, elevation is not required.

---

## How It Works

```
gui_detector.py
├── is_admin() / elevate() / require_admin()        — UAC elevation
├── _require_ocr_deps() / _get_ocr_reader()         — lazy EasyOCR init & cache
├── capture_window()                                — Pillow ImageGrab screenshot
├── _easyocr_results_to_dicts()                     — normalise quad-bbox → rect dicts
├── ocr_find_text() / ocr_scan_all()                — EasyOCR search / full scan
├── _require_image_deps() / image_find()            — PyAutoGUI template matching
├── list_all_windows()                              — enumerate via Desktop(uia)
├── inspect_by_pid() / inspect_by_title()           — connect & walk target window
├── walk_elements() / get_element_info()            — recursive DFS + property extraction
├── watch_window()                                  — polling loop with snapshot diffing
└── main() / build_parser()                         — argparse CLI entry point

gui_helper.py
├── find_by_name/auto_id/control_type()             — tree search helpers
├── find_all() / flatten_tree()                     — bulk tree traversal
├── find_ocr() / find_all_ocr()                     — OCR result search
├── find_image_result()                             — image result lookup
├── GUISession.__init__()                           — load + parse JSON export
├── GUISession.click_by_name/auto_id()              — tree-driven pixel/live click
├── GUISession.type_into()                          — find Edit field + type text
├── GUISession.click_ocr() / click_image()          — OCR and image-driven clicks
└── GUISession.smart_click()                        — three-layer auto-fallback click
```

---

## Limitations

- **Windows only** — Pywinauto does not support macOS or Linux
- **Some apps restrict access** — protected processes require Administrator rights; the script requests elevation automatically and falls back gracefully if declined
- **Electron / web-based UIs** — automation IDs are often sparse or absent; use `--depth 3` to keep output manageable
- **EasyOCR speed** — accurate but slow on CPU; use `--find` with a short keyword rather than `--ocr` full scans; a CUDA-capable GPU speeds it up significantly
- **Image template matching** — breaks if the window is resized or DPI changes; capture the reference `.png` at the exact same resolution and zoom level you will run the search at
- **Dynamic UIs** — rapidly changing windows (games, video players) may produce noisy watch output
- **`gui_helper.py` live actions** — `live=True` requires the target process to still be running and accessible

---

## License

MIT — free to use, modify, and distribute.
