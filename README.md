# pywin-gui-inspector

A Windows GUI inspection, automation, and recording toolkit built on
[Pywinauto](https://pywinauto.readthedocs.io/),
[EasyOCR](https://github.com/JaidedAI/EasyOCR), and
[PyAutoGUI](https://github.com/asweigart/pyautogui).

**Inspect** any running application's UI element tree, **export** the results
to JSON, **automate** from the export or live, **record** your own interactions
and replay them as a Python script.

---

## Project Structure

```
pywin-gui-inspector/
├── src/
│   └── pywin_gui_inspector/       ← installable Python package
│       ├── __init__.py            ← public API: GUISession, LiveSession, …
│       ├── detector/              ← ElevationManager, OCRProcessor, WindowInspector, …
│       ├── helper/                ← GUISession, ScriptWriter, TreeSearch, …
│       ├── live/                  ← LiveSession, DesktopSession, PathSyntax, …
│       └── recorder/              ← TrayApp, Recorder, ScriptExporter, …
├── tests/                         ← 88 unit tests (pytest)
├── docs/                          ← Sphinx / ReadTheDocs documentation
├── ExampleScripts/                ← nine worked examples
├── gui_detector.py                ← CLI entry-point (thin wrapper)
├── gui_helper.py                  ← backward-compat re-export shim
├── gui_live.py                    ← backward-compat re-export shim
├── gui_recorder.py                ← CLI entry-point (thin wrapper)
└── pyproject.toml
```

The four root-level `gui_*.py` files are **thin wrappers** for convenience —
all real logic lives in `src/pywin_gui_inspector/`.

---

## Installation

### From source (development)

```bash
git clone https://github.com/your-org/pywin-gui-inspector
cd pywin-gui-inspector
pip install -e .                    # core only
pip install -e ".[ocr]"             # + EasyOCR text detection
pip install -e ".[image]"           # + OpenCV template matching
pip install -e ".[recorder]"        # + pystray / keyboard tray recorder
pip install -e ".[all]"             # everything
```

### Dependency groups (defined in `pyproject.toml`)

| Extra | Packages | Enables |
|---|---|---|
| *(core)* | `pywinauto pyautogui` | Inspector CLI, GUISession, LiveSession |
| `ocr` | `easyocr Pillow` | `--ocr`, `--find`, `OCRWrapper` |
| `image` | `opencv-python` | `--image` template matching |
| `recorder` | `keyboard pystray Pillow` | System-tray recorder |
| `all` | all of the above | Everything |

---

## Requirements

| | |
|---|---|
| OS | Windows 10 / 11 only |
| Python | 3.10 or later |

---

## Quickstart

### 1 — Import the package

```python
from pywin_gui_inspector import GUISession, LiveSession, DesktopSession
from pywin_gui_inspector import connect_application, start_application
```

Or run the CLI scripts directly from the project root (thin wrappers that add
`src/` to `sys.path` automatically):

```bash
python gui_detector.py --help
python gui_recorder.py
```

### 2 — Inspect a window and export to JSON

```bash
python gui_detector.py --title "Notepad" --ocr --export notepad.json
python gui_detector.py --pid 1234 --image save_icon.png --export dump.json
python gui_detector.py --export dump.json          # interactive picker
```

### 3 — Automate from the export (`GUISession`)

```python
from pywin_gui_inspector import GUISession

s = GUISession("notepad.json")
s.click_by_name("File")
s.click_by_name("Save As")
s.type_into("File name:", "report.txt")
s.smart_click("Save")            # tries tree → OCR → image automatically
```

### 4 — Generate a script from plain English (`ScriptWriter`)

```python
from pywin_gui_inspector import ScriptWriter

sw = ScriptWriter("notepad.json")
sw.preview("click File, click Save As, type report.txt into File name:, click Save")
```

### 5 — Live automation without a snapshot (`LiveSession`)

```python
from pywin_gui_inspector import connect_application

s = connect_application(title="Notepad")

s.menu_click("File->Save As")
s.set_text("File name:||Edit", "report.txt")
s.click("Save||Button")

with s.path("Untitled - Notepad||Window"):
    s.click("Edit||MenuItem")
```

### 6 — Record interactions and replay them

```bash
python gui_recorder.py -o login_flow.py
python gui_recorder.py --start F6 --stop F8 --exit F10
```

1. A **tray icon** appears (bottom-right corner)
2. Press **F7** to start recording
3. Hover over elements to see the green highlight and path tooltip
4. Click and type normally — every action is captured
5. Press **F9** to stop; the script is written to `login_flow.py`

The generated script imports `DesktopSession` from the package and runs immediately.

---

## Package API

### `pywin_gui_inspector` — top-level exports

```python
from pywin_gui_inspector import (
    GUISession,           # JSON-export automation session
    ScriptWriter,         # plain-English → Python script generator
    LiveSession,          # live UIA automation (no snapshot needed)
    DesktopSession,       # LiveSession with no app connection required
    connect_application,  # attach to a running app → LiveSession
    start_application,    # launch an exe and attach → LiveSession
)
```

### Sub-packages

| Sub-package | Key classes |
|---|---|
| `pywin_gui_inspector.detector` | `ElevationManager`, `OCRProcessor`, `ImageMatcher`, `WindowInspector`, `ChangeMonitor`, `Renderer` |
| `pywin_gui_inspector.helper` | `GUISession`, `ScriptWriter`, `TreeSearch`, `OCRSearch`, `ImageSearch`, `RectHelper` |
| `pywin_gui_inspector.live` | `LiveSession`, `DesktopSession`, `PathSyntax`, `ElementSearch`, `TTLCache`, `ReadinessChecker`, `GridLayout`, `OCRWrapper`, `OCREngine`, `UIPath`, `ApplicationFactory` |
| `pywin_gui_inspector.recorder` | `TrayApp`, `Recorder`, `ScriptExporter`, `TrayIconFactory`, `HotkeyManager`, `PathBuilder`, `TkOverlay`, `Win32Mouse`, `ClickEvent`, `TypeEvent`, `HotkeyEvent` |

---

## CLI Reference — `gui_detector.py`

| Flag | Default | Description |
|---|---|---|
| `--pid PID` | — | Inspect by process ID |
| `--title TEXT` | — | Inspect by partial window title |
| `--dump` | — | List all open windows |
| `--watch PID` | — | Poll a window and print element diffs |
| `--depth N` | `8` | Max element-tree recursion depth |
| `--export FILE.json` | — | Save full results to JSON |
| `--interval SECS` | `1.0` | Polling interval for `--watch` |
| `--ocr` | — | Full EasyOCR scan of the window |
| `--find TEXT` | — | OCR-search for a specific string |
| `--image FILE.png` | — | PyAutoGUI image template search |
| `--confidence N` | `0.9` | Match threshold for `--image` |

---

## Live Path Syntax

| Pattern | Matches |
|---|---|
| `"OK\|\|Button"` | Element named "OK" of type Button |
| `"\|\|Edit"` | Any Edit control |
| `"Toolbar\|\|ToolBar->Save\|\|Button"` | Save button inside Toolbar |
| `"*->\|\|Button"` | Wildcard level, then any Button |
| `"RegEx: .*Save.*\|\|Button"` | Regex name match |
| `"\|\|Button#[1,2]"` | Row 1, col 2 of matched Buttons |
| `"\|\|Slider%(0.8,0)"` | Click 80% right of slider center |

---

## Running the Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

88 unit tests covering pure-Python logic (no live Windows session required):
`RectHelper`, `TreeSearch`, `OCRSearch`, `ImageSearch`, `PathSyntax`, `TTLCache`,
`ScriptExporter`, and `ScriptWriter`.

---

## How It Works

```
detector/    inspect → walk UIA tree → OCR/image search → JSON export
helper/      load JSON → search tree / OCR / images → pixel or live click
live/        connect live → path-based UIA search → TTL cache → smart click
recorder/    tray + hotkeys → track cursor → UIA lookup → record events → script
```

**Three search layers (used across all sub-packages):**

| Priority | Layer | Best for |
|---|---|---|
| 1 | UIA element tree | Apps with stable automation IDs |
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
- **Image matching** — breaks if DPI or zoom changes; capture at 100 % scale

---

## License

MIT — free to use, modify, and distribute.