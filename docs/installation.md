# Installation

## Requirements

- **OS:** Windows only (Pywinauto requires the Windows accessibility APIs)
- **Python:** 3.9 or later

## Core install

The core dependency enables element-tree inspection:

```bash
pip install pywinauto
```

## Optional dependencies

Each optional group is lazy-loaded — it is only checked when the relevant
feature is actually used, so you only install what you need.

### OCR mode (`--ocr` / `--find`)

Enables text search via EasyOCR. Model weights (~100 MB) are downloaded
automatically on first use.

```bash
pip install easyocr Pillow
```

### Image / template search (`--image`)

Enables pixel-level template matching via PyAutoGUI and OpenCV.

```bash
pip install pyautogui opencv-python
```

### Everything at once

```bash
pip install pywinauto easyocr Pillow pyautogui opencv-python
```

## No package install needed

`gui_detector.py` and `gui_helper.py` are self-contained scripts. Copy them
into your project directory and import or run them directly — no build step or
`setup.py` required.