# How it works

## Architecture

The toolkit is four files with a clear separation of concerns:

```
gui_detector.py   — inspect, screenshot, search, export (run once per target)
gui_helper.py     — load JSON export, drive automation (GUISession / ScriptWriter)
gui_live.py       — live UIA automation, no snapshot required (LiveSession / UIPath)
gui_recorder.py   — system tray recorder → captures actions → generates gui_live scripts
```

```
┌─────────────────┐   JSON export   ┌──────────────────┐
│ gui_detector.py │ ─────────────▶  │  gui_helper.py   │
│  (inspector)    │                 │  (GUISession)     │
└─────────────────┘                 └──────────────────┘

┌─────────────────┐   live UIA      ┌──────────────────┐
│ gui_live.py     │ ◀──────────────  Windows UIA tree  │
│  (LiveSession)  │                 └──────────────────┘
└─────────────────┘                          ▲
         ▲                                   │ records
┌─────────────────┐   generates script       │
│ gui_recorder.py │ ─────────────────────────┘
│  (tray app)     │
└─────────────────┘
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

---

## `gui_live.py`

```
connect_application() / start_application()
└── Application(uia).connect()           pywinauto connection

LiveSession._search(path)
├── _parse(path)                         split "Name||Type->..." into _Entry list
├── _path_find(root, entries)            recursive subtree search per entry
│   └── _subtree_find(node, entry)       DFS collecting matches, depth ≤ 12
├── _TTLCache.get/set                    2-second result cache per (handle, path)
└── get_sorted_region(matches)           grid layout for #[row,col] selection

LiveSession._do_click(element, offset)
├── wait_is_ready(element)               polls enabled + visible + cursor
├── element.rectangle()                  get screen coords
└── pyautogui.moveTo() + click()         pixel click with optional %(dx,dy) offset

LiveSession.menu_click("File->Save As")
└── for each label: find() → _do_click() → sleep(delay)

LiveSession.ocr_find(query)
└── _ocr_scan(window)                    PIL screenshot → EasyOCR → OCRWrapper list

UIPath.__enter__ / __exit__
└── session._path_stack.append/pop       composable path prefix stack
```

---

## `gui_recorder.py`

```
TrayApp.run()                            pystray.Icon.run() blocks main thread
├── TkOverlay.start()                    Tkinter in its own daemon thread
│   └── _flush() via root.after(50)      drains queue → updates strips + tooltip
├── _register_hotkeys()                  keyboard.add_hotkey for start / stop
└── pystray menu callbacks               on_start → begin(), on_stop → end()

TrayApp._start_recording()
├── Recorder.begin()
│   ├── threading.Thread(_track_loop)    polls cursor + UIA → overlay queue
│   └── threading.Thread(_click_loop)   polls GetAsyncKeyState → ClickEvent
├── keyboard.on_press(_on_key)           TypeEvent / HotkeyEvent
└── update tray icon → red

TrayApp._stop_recording()
├── Recorder.end() → list[events]
├── generate_script(events)              events → gui_live.py Python source
├── Path.write_text(script)             save to output file
├── icon.notify(...)                    Windows tray notification
└── update tray icon → green

generate_script(events)
└── for each event:
    ClickEvent   → s.click() / s.right_click()
    TypeEvent    → s.set_text()
    HotkeyEvent  → s.hotkey() / s.press()
    gap > 1.5 s  → time.sleep(N)
```