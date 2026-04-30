# CLI Reference — `gui_detector.py`

```
python gui_detector.py [OPTIONS]
```

## Modes

The four mode flags are mutually exclusive.

| Flag | Description |
|---|---|
| *(none)* | **Interactive** — lists all open windows, you pick one to inspect |
| `--pid PID` | Inspect the window belonging to the given process ID |
| `--title TEXT` | Inspect the first window whose title contains *TEXT* |
| `--dump` | List every visible top-level window and exit |
| `--watch PID` | Poll a window and print live element diffs |

## Options

| Flag | Default | Description |
|---|---|---|
| `--depth N` | `8` | Maximum recursion depth when walking the element tree |
| `--export FILE.json` | — | Save the full results (tree + OCR + images) to a JSON file |
| `--interval SECONDS` | `1.0` | Polling interval for `--watch` |
| `--ocr` | — | Run a full EasyOCR scan on the window screenshot |
| `--find TEXT` | — | OCR-search for *TEXT* (implies `--ocr`) |
| `--image FILE.png` | — | Search the screen for a reference image using PyAutoGUI |
| `--confidence N` | `0.9` | Match threshold for `--image` (0.0–1.0, requires `opencv-python`) |

## Examples

### List all open windows

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

### Inspect by title

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

### OCR search for specific text

```bash
python gui_detector.py --pid 1234 --find "Save"
```

```
[*] OCR search for 'Save' in window (PID 1234)…

──────────────────────────────────────────────────────────────────────
  OCR — 2 result(s) matching 'Save'
──────────────────────────────────────────────────────────────────────
  [ 96%]  'Save'       (412,310)→(463,328)
  [ 91%]  'Save As'    (412,332)→(490,350)
──────────────────────────────────────────────────────────────────────
```

### Image template search

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

### Watch mode

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

### Export everything to JSON

```bash
python gui_detector.py --pid 1234 --ocr --image save_icon.png --export dump.json
```

### Export window list to JSON

```bash
python gui_detector.py --dump --export windows.json
```

## Administrator privileges

`gui_detector.py` automatically requests elevation via UAC on launch.

| Situation | Behaviour |
|---|---|
| Already running as Administrator | Continues silently |
| UAC prompt → **Yes** | Elevated child launches; parent exits |
| UAC prompt → **No** | Warning printed, continues without admin rights |

Elevation is required to inspect elevated processes (installers, Task Manager,
system utilities). Everyday apps (Notepad, Chrome, VS Code) work without it.