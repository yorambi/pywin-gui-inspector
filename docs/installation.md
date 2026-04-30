# Installation

## Requirements

- **OS:** Windows only (Pywinauto requires the Windows accessibility APIs)
- **Python:** 3.9 or later

## Core install

Enables element-tree inspection (`gui_detector.py`) and JSON-based automation
(`gui_helper.py`):

```bash
pip install pywinauto pyautogui
```

## Optional dependencies

Each optional group is lazy-loaded and only checked when the relevant feature
is actually used.

### OCR mode — `--ocr`, `--find`, `OCRWrapper`

EasyOCR model weights (~100 MB) are downloaded on first use.

```bash
pip install easyocr Pillow
```

### Image / template search — `--image`

```bash
pip install opencv-python
```

### Live automation — `gui_live.py`

No extra packages beyond the core install.  OCR features in `LiveSession`
additionally require `easyocr Pillow`.

### Recorder — `gui_recorder.py`

```bash
pip install keyboard pystray
```

`keyboard` — global hotkey and keystroke capture  
`pystray` — Windows system tray icon

### Everything at once

```bash
pip install pywinauto pyautogui easyocr Pillow opencv-python keyboard pystray
```

## No build step needed

All four scripts (`gui_detector.py`, `gui_helper.py`, `gui_live.py`,
`gui_recorder.py`) are self-contained. Copy them into your project directory
and import or run them directly.