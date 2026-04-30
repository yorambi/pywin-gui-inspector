# `LiveSession`

The main class in `gui_live.py`. Connects to a running application and
automates it by querying the live UIA tree directly — no JSON snapshot needed.

See {doc}`../live-mode` for a conceptual overview and path syntax reference.

## Connecting

```python
from gui_live import connect_application, start_application

s = connect_application(title="Notepad")     # partial title match
s = connect_application(pid=1234)
s = connect_application(title_re=r".*\.txt - Notepad")   # regex
s = start_application("notepad.exe")         # launch and attach
```

### `connect_application(pid=, title=, title_re=)`

Connect to an already-running application and return a `LiveSession`.
Exactly one of `pid`, `title`, or `title_re` must be supplied.

### `start_application(executable, *args, timeout=15.0)`

Launch `executable` with optional `args`, wait up to `timeout` seconds for
its window to appear, and return a `LiveSession`.

Uses a before/after window-handle diff so it reliably identifies the new
window even when other applications are open.

---

## Finding elements

### `find(path, timeout=5.0) → element | None`

Return the first element matching `path`, or `None`.  Retries for up to
`timeout` seconds so it handles delayed rendering.

```python
btn = s.find("Save||Button")
el  = s.find("RegEx: .*dialog.*||Window", timeout=10.0)
```

### `find_all(path, timeout=5.0) → list`

Return all elements matching `path`.

```python
buttons = s.find_all("||Button")
```

---

## Clicking

### `click(path, timeout=5.0) → bool`

Click the first element matching `path`.  Calls `wait_is_ready()` before
clicking.  Returns `True` on success, `False` if not found.

Supports `%(dx,dy)` offset suffix:

```python
s.click("||Slider%(0.8, 0)")    # 80% to the right
```

### `double_click(path, timeout=5.0) → bool`

Double-click the first matching element.

### `right_click(path, timeout=5.0) → bool`

Right-click the first matching element.

### `drag_and_drop(source, target, timeout=5.0) → bool`

Drag from the center of `source` path to the center of `target` path.

```python
s.drag_and_drop("item.txt||ListItem", "Trash||Group")
```

---

## Text input

### `set_text(path, text, timeout=5.0) → bool`

Click an Edit control and replace its content with `text`.

Uses triple-click + Ctrl+A before typing to guarantee all existing text is
selected, making it more reliable than a single Ctrl+A.

```python
s.set_text("File name:||Edit", "report.txt")
```

### `set_combobox(path, text, timeout=5.0) → bool`

Open a ComboBox and type `text` into it.  Waits 0.9 s after clicking to
let the dropdown animation finish before sending keystrokes.

```python
s.set_combobox("Format||ComboBox", "PDF")
```

---

## Keyboard

### `send_keys(text)`

Type `text` character by character via pyautogui.

### `hotkey(*keys)`

Press a keyboard shortcut.

```python
s.hotkey("ctrl", "s")
s.hotkey("alt", "f4")
```

### `press(key)`

Press a single named key.

```python
s.press("enter")
s.press("tab")
s.press("f5")
```

---

## Menu navigation

### `menu_click(menu_path, delay=0.35, timeout=5.0) → bool`

Navigate and click a multi-level menu.  `menu_path` is a `"->"` separated
string of item labels.

```python
s.menu_click("File->Save As")
s.menu_click("Edit->Find->Find Next")
s.menu_click("View->Zoom->150%")
```

Each level is clicked in order with `delay` seconds between items to allow
submenus to open.

---

## OCR methods

These require `pip install easyocr Pillow`.

### `ocr_find(query, exact=False, timeout=5.0) → OCRWrapper | None`

Screenshot the active window and return the first EasyOCR detection whose
text contains `query`.  Retries until `timeout` expires.

```python
result = s.ocr_find("Submit")
result = s.ocr_find("OK", exact=True)
```

### `ocr_find_all(query="") → list[OCRWrapper]`

Return all OCR detections in the current window, optionally filtered by
`query`.

### `ocr_click(query, exact=False, timeout=5.0) → bool`

Click the first OCR match for `query`.

---

## Smart click

### `smart_click(query, timeout=5.0) → bool`

Try clicking `query` via the UIA element tree first, then fall back to OCR.
Returns `True` on first success, `False` if nothing was found.

```python
s.smart_click("Submit")
```

---

## UIPath context manager

### `path(prefix) → UIPath`

Return a context manager that prepends `prefix` to every path inside the
block.  Nesting is supported.

```python
with s.path("My App||Window"):
    s.click("File||MenuItem")          # resolved as "My App||Window->File||MenuItem"

with s.path("My App||Window"):
    with s.path("Toolbar||ToolBar"):
        s.click("Save||Button")
```

---

## Application lifecycle

### `focus()`

Bring the application window to the foreground using `SetForegroundWindow`.

### `close()`

Kill the application process.

---

## Cache control

### `invalidate_cache()`

Force the next element search to bypass the 2-second TTL cache and re-query
the live UIA tree.  Call this after an action that changes the UI structure.

---

## Introspection

### `summary()`

Print a formatted summary:

```
────────────────────────────────────────────────────────────
  LiveSession : 'Untitled - Notepad'
  PID         : 1234
  Handle      : 0x000a0b4c
  Rect        : (100,200) → (900,700)
  Path stack  : (none)
────────────────────────────────────────────────────────────
```

---

## Module-level helpers

### `wait_is_ready(element, timeout=8.0, poll=0.1) → bool`

Wait until `element` is enabled, visible, and the system cursor is not the
hourglass.  Returns `True` when ready, `False` on timeout.

### `get_sorted_region(elements, ...) → (nrows, ncols, grid)`

Sort a list of elements by screen position into a 2-D grid.  Used internally
for `#[row,col]` path addressing.

```python
from gui_live import get_sorted_region

buttons = s.find_all("||Button")
nrows, ncols, grid = get_sorted_region(buttons)
second_row_first = grid[1][0]
```

### `OCRWrapper`

Wraps an EasyOCR detection as a duck-typed pywinauto element.  Returned by
`ocr_find()` and `ocr_find_all()`.

```python
result = s.ocr_find("Cancel")
if result:
    print(result.window_text(), result.confidence)
    result.click_input()
```