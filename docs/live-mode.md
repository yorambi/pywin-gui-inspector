# Live Mode — `gui_live.py`

`gui_live.py` automates Windows applications by querying the running UIA tree
directly, without requiring a JSON snapshot from `gui_detector.py`.

It complements {doc}`api/gui-session` (which works from pre-captured exports)
by adding live-search, a composable path syntax, and several robustness
improvements inspired by [pywinauto_recorder](https://github.com/beuaaa/pywinauto_recorder).

## When to use each module

| | `gui_helper.py` (GUISession) | `gui_live.py` (LiveSession) |
|---|---|---|
| Needs a JSON export | Yes | No |
| Works offline / headless | Yes | No |
| Path syntax | name / automation_id | `"Name\|\|Type->Child\|\|Type"` |
| Wildcard matching | No | Yes (`*`, regex) |
| Grid addressing | No | Yes (`#[row,col]`) |
| UIPath context scoping | No | Yes |
| Readiness wait | Fixed delay | Polls enabled + cursor state |
| Reliability for form fill | Good | Better (`set_text` triple-click) |
| Menu navigation | Manual | `menu_click("File->Save As")` |
| App lifecycle | Not included | start / connect / focus / close |

---

## Connecting to an application

```python
from gui_live import connect_application, start_application

# Attach to a running app by partial title
s = connect_application(title="Notepad")

# Attach by PID
s = connect_application(pid=1234)

# Launch a new app and attach automatically
s = start_application("notepad.exe")
s = start_application("C:/Apps/MyApp.exe", "--config", "prod.ini")
```

After connecting, call `s.summary()` to print the window title, handle, PID,
and screen rectangle.

---

## Path syntax

Paths are strings of the form:

```
"Name||ControlType->ChildName||ControlType->..."
```

The `->` separator adds a hierarchy level. `||` separates the element's name
from its control type. Either half may be omitted.

| Pattern | Meaning |
|---|---|
| `"Save\|\|Button"` | element whose name contains "Save" and type is Button |
| `"\|\|Edit"` | any Edit control (name not filtered) |
| `"File\|\|MenuItem"` | MenuItem named "File" |
| `"Toolbar\|\|ToolBar->Save\|\|Button"` | Save button inside Toolbar |
| `"*->\|\|Button"` | wildcard intermediate level, then any Button |
| `"RegEx: .*Save.*\|\|Button"` | regex on the name, type is Button |
| `"\|\|Button#[1,2]"` | row 1, col 2 when multiple buttons match |
| `"\|\|Slider%(0.8,0)"` | click 80% right of slider center |

### Wildcards and regex

`*` as a full node token matches any single level:

```python
s.click("*->OK||Button")         # OK button anywhere one level deep
s.click("*->*->Submit||Button")  # two wildcard levels
```

Prefix the name with `RegEx:` for regex matching:

```python
s.click("RegEx: .*Save.*||Button")
s.find("RegEx: Untitled.*||Window")
```

### Grid addressing `#[row,col]`

When a path matches multiple elements (e.g. a toolbar with several buttons),
append `#[row,col]` to select by position:

```python
# Second row, first column of all matched buttons
s.click("||Button#[1,0]")
```

Row and column indices are zero-based. Positions are determined by screen
coordinates (top to bottom, left to right).

### Click offset `%(dx,dy)`

Append `%(dx,dy)` to click at a fractional offset from element center. Values
are fractions of the element's half-dimensions:

```python
s.click("||Slider%(0.8, 0)")   # 80% right of slider center
s.click("||Slider%(-1.0, 0)")  # leftmost edge
```

---

## `UIPath` context manager

`s.path(prefix)` returns a context manager that prepends `prefix` to every
path inside the block. Nesting is supported.

```python
with s.path("My App||Window"):
    s.click("File||MenuItem")              # → "My App||Window->File||MenuItem"
    s.set_text("Search||Edit", "hello")    # → "My App||Window->Search||Edit"

# Nested
with s.path("My App||Window"):
    with s.path("Toolbar||ToolBar"):
        s.click("Save||Button")            # → "My App||Window->Toolbar||ToolBar->Save||Button"
```

---

## Clicking and interacting

```python
s.click("Save||Button")
s.double_click("item.txt||ListItem")
s.right_click("file.txt||ListItem")
s.drag_and_drop("Source||ListItem", "Target||Group")
```

All click methods call `wait_is_ready()` internally before clicking — no manual
`time.sleep()` needed.

---

## Reliable text entry

`set_text` uses triple-click + Ctrl+A before typing, which guarantees that all
existing content is replaced:

```python
s.set_text("File name:||Edit", "report.txt")
s.set_text("Search||Edit", "hello")
```

`set_combobox` opens the dropdown and waits 0.9 s for the animation:

```python
s.set_combobox("Format||ComboBox", "PDF")
```

---

## Multi-level menu navigation

```python
s.menu_click("File->Save As")
s.menu_click("Edit->Find->Find Next")
s.menu_click("View->Zoom->150%")
```

Each level is clicked in sequence with a short delay for the submenu to open.

---

## Smart click (UIA → OCR fallback)

```python
s.smart_click("Submit")   # tries UIA tree first, then EasyOCR
```

---

## OCR methods

```python
result = s.ocr_find("Save")           # returns OCRWrapper or None
results = s.ocr_find_all("Save")      # returns list[OCRWrapper]
s.ocr_click("Cancel")                 # click first OCR match
s.ocr_click("OK", exact=True)         # exact text match
```

`OCRWrapper` objects expose the same interface as pywinauto elements
(`.window_text()`, `.rectangle()`, `.click_input()`, etc.), so they can be
passed into any method that accepts an element.

---

## TTL element cache

Search results are cached for 2 seconds per path per window handle.  Repeated
calls to `s.click("Save||Button")` within 2 seconds re-use the cached element
without re-querying UIA.

Call `s.invalidate_cache()` to force an immediate re-query, for example after
an action that changes the UI.

---

## Full example

```python
from gui_live import connect_application

s = connect_application(title="Notepad")
s.focus()
s.summary()

with s.path("Untitled - Notepad||Window"):
    # Open Save As dialog
    s.menu_click("File->Save As")

    # Fill the filename
    s.set_text("File name:||Edit", "report.txt")

    # Confirm
    s.click("Save||Button")
```