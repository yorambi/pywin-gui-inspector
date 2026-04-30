# How it works

## Architecture

The toolkit has two files with a clean separation of concerns:

```
gui_detector.py   — inspect, screenshot, search, export (run once per target)
gui_helper.py     — load export, drive automation (used in your scripts)
```

---

## `gui_detector.py`

```
main() / build_parser()
├── require_admin()                   UAC elevation via ShellExecuteW runas
│
├── --dump path
│   └── list_all_windows()            Desktop(uia).windows() enumeration
│
├── --watch path
│   └── watch_window()                polling loop → snapshot() diffing
│
├── --pid / --title / interactive path
│   ├── inspect_by_pid()
│   ├── inspect_by_title()            Application(uia).connect()
│   └── interactive_mode()
│       └── walk_elements()           recursive DFS on children()
│           └── get_element_info()    extracts 10 properties per element
│
├── OCR path (--ocr / --find)
│   ├── _require_ocr_deps()           checks easyocr + Pillow at runtime
│   ├── capture_window()              Pillow ImageGrab.grab(bbox)
│   ├── _get_ocr_reader()             cached EasyOCR Reader (lazy init)
│   └── ocr_find_text() / ocr_scan_all()
│       └── _easyocr_results_to_dicts()   quad-bbox → rect dicts
│
└── Image path (--image)
    ├── _require_image_deps()         checks pyautogui + cv2 at runtime
    └── image_find()                  pyautogui.locateAllOnScreen()
```

---

## `gui_helper.py`

```
GUISession.__init__()
└── json.load()                       loads element_tree + ocr + image results

GUISession.click_by_name()
└── find_by_name()                    DFS on children[] list
    └── _click() or click_input()     PyAutoGUI pixel click or Pywinauto live

GUISession.click_ocr()
└── find_ocr()                        linear scan of ocr_results list
    └── _click()                      PyAutoGUI pixel click at OCR rect center

GUISession.click_image()
└── find_image_result()               linear scan of image_results list
    └── _click()                      PyAutoGUI pixel click at pre-computed center

GUISession.smart_click()
├── find_by_name()  → click_by_name()
├── find_ocr()      → click_ocr()
└── find_image_result() → click_image()

ScriptWriter.generate()
├── _parse_steps()                    split on comma or newline
├── _step_to_code()                   regex dispatch per instruction verb
│   ├── click → _resolve_click()      checks tree → OCR → image → fallback
│   ├── type into → type_into()
│   ├── press / hotkey / wait / screenshot → pyautogui / time.sleep
│   └── open / close
└── returns complete Python script string
```

---

## Three-layer search

Every find/click operation resolves by trying layers in priority order:

```
Layer 1  Element tree   — parsed from UIA accessibility tree at export time
         automation_id  → most stable, survives window reopen
         name           → falls back if no automation_id

Layer 2  OCR results    — text regions detected by EasyOCR on the screenshot
         substring      → case-insensitive, configurable exact mode

Layer 3  Image results  — pixel regions matched by PyAutoGUI template matching
         template name  → optional filter, otherwise first match
```

The layers are independent — a match in Layer 1 never consults Layer 2 or 3.
`smart_click` is the only method that traverses all three automatically.

---

## Watch mode internals

`watch_window()` maintains a `snapshot` — a flat `set[str]` of all element
names in the tree at a given moment. On each poll it:

1. Re-connects to the process via `Application(uia).connect(process=pid)`
2. Re-walks the element tree to build a new snapshot
3. Computes `added = current - previous` and `removed = previous - current`
4. Prints any changes and updates `previous`