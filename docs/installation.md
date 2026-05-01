# Installation

## Requirements

- **OS:** Windows 10 / 11 only (Pywinauto requires the Windows accessibility APIs)
- **Python:** 3.10 or later

## Project layout

The package follows the standard Python `src/` layout:

```text
pywin-gui-inspector/
├── src/
│   └── pywin_gui_inspector/   ← the installable package
│       ├── detector/
│       ├── helper/
│       ├── live/
│       └── recorder/
├── tests/                     ← pytest unit tests
├── pyproject.toml
└── gui_*.py                   ← thin CLI entry-point wrappers
```

## Install from source

Clone the repository and install in editable mode so that changes to `src/`
are immediately reflected without reinstalling:

```bash
git clone https://github.com/your-org/pywin-gui-inspector
cd pywin-gui-inspector

pip install -e .              # core only
pip install -e ".[ocr]"       # + EasyOCR text detection
pip install -e ".[image]"     # + OpenCV template matching
pip install -e ".[recorder]"  # + pystray / keyboard tray recorder
pip install -e ".[dev]"       # + pytest for running the test suite
pip install -e ".[all]"       # everything
```

## Dependency groups

All extras are defined in `pyproject.toml` and are lazy-loaded — each group
is only imported when the relevant feature is first used.

### Core *(always required)*

Enables the inspector CLI and both the `GUISession` and `LiveSession` APIs:

```bash
pip install pywinauto pyautogui
```

### `ocr` — text detection

Enables `--ocr`, `--find`, and `OCRWrapper`.
EasyOCR model weights (~100 MB) are downloaded on first use and cached in
`~/.EasyOCR/`.

```bash
pip install easyocr Pillow
```

### `image` — template matching

Enables `--image` and `ImageMatcher`:

```bash
pip install opencv-python
```

### `recorder` — system-tray recorder

Enables `gui_recorder.py` and the `pywin_gui_inspector.recorder` sub-package:

```bash
pip install keyboard pystray Pillow
```

`keyboard` — global hotkey registration and keystroke capture  
`pystray` — Windows system tray icon  
`Pillow` — programmatic icon image generation

### `dev` — test suite

```bash
pip install pytest pytest-cov
```

### Everything at once

```bash
pip install -e ".[all]"
```

## Verify the installation

```bash
python -c "import pywin_gui_inspector; print(pywin_gui_inspector.__version__)"
pytest tests/ -q    # should show 88 passed
```

## Using the entry-point wrappers

The root-level `gui_*.py` files are thin wrappers that add `src/` to
`sys.path` and re-export the package.  They allow running the tools directly
from the project root without an editable install:

```bash
python gui_detector.py --help
python gui_recorder.py
```

These wrappers also preserve backward-compatible imports for existing scripts:

```python
# still works (via the thin wrapper / re-export)
from gui_helper import GUISession

# preferred: import from the package directly
from pywin_gui_inspector import GUISession
```
