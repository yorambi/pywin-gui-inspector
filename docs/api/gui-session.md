# `GUISession`

The main high-level automation class. Loads a JSON export produced by
`gui_detector.py` and exposes click, type, and search methods across three
search layers.

## Constructor

```python
from gui_helper import GUISession

s = GUISession(
    export_path,          # str | Path — JSON file from gui_detector.py
    click_delay=0.3,      # float — pause in seconds after every click
    move_duration=0.1,    # float — PyAutoGUI mouse move speed in seconds
)
```

**Parameters**

`export_path`
: Path to the JSON file produced by `gui_detector.py --export`.

`click_delay`
: Seconds to sleep after every click action (default `0.3`). Increase this for
  slower applications that need time to react.

`move_duration`
: Mouse move duration passed to PyAutoGUI's `moveTo()` (default `0.1`).

---

## Search layer priority

All find/click methods try layers in this order and stop at the first hit:

1. **Element tree** — Pywinauto UIA tree (automation ID → name → control type)
2. **OCR results** — visible text detected by EasyOCR
3. **Image results** — pixel-matched reference screenshots (PyAutoGUI)

---

## Element tree methods

### `find(name, exact=False)`

Search the element tree by name. Returns the matching node dict or `None`.

```python
node = s.find("Save")           # substring match
node = s.find("Save", exact=True)  # exact match
```

### `find_auto_id(auto_id)`

Find the first element whose `automation_id` exactly matches `auto_id`.

```python
node = s.find_auto_id("btn_save")
```

### `click_by_name(name, exact=False, live=False)`

Click the first visible, enabled element whose name contains `name`.

```python
s.click_by_name("Save")
s.click_by_name("Save", exact=True)    # avoids matching "Save As"
s.click_by_name("OK", live=True)       # uses Pywinauto click_input()
```

`live=True` routes the click through Pywinauto's `click_input()` instead of
a raw pixel click. More reliable for keyboard-focus-sensitive controls, but
requires the target process to still be running.

Returns `True` on success, `False` if the element was not found.

### `click_by_auto_id(auto_id, live=False)`

Click the element with the given automation ID (exact match).

```python
s.click_by_auto_id("btn_ok")
s.click_by_auto_id("FileNameBox", live=True)
```

Returns `True` on success, `False` if not found.

### `type_into(name, text, clear_first=True)`

Click the Edit control matching `name` and type `text` into it.

```python
s.type_into("File name:", "report.txt")
s.type_into("Search", "hello", clear_first=False)  # appends instead of replacing
```

If no Edit element is found by name, falls back to the first visible Edit
control in the tree.

Returns `True` on success, `False` if no Edit field was found.

### `all_buttons()`

Return a list of all enabled, visible `Button` elements.

```python
for btn in s.all_buttons():
    print(btn["name"], btn["automation_id"])
```

### `all_edits()`

Return a list of all enabled, visible `Edit` (text input) elements.

### `all_checkboxes()`

Return a list of all `CheckBox` elements.

### `all_of_type(control_type)`

Return all elements of any control type string.

```python
menus = s.all_of_type("MenuItem")
combos = s.all_of_type("ComboBox")
```

---

## OCR methods

These methods require `ocr_results` to be present in the export (use
`gui_detector.py --ocr` or `--find` when exporting).

### `click_ocr(query, exact=False)`

Click the screen position of the first OCR result whose text contains `query`.

```python
s.click_ocr("Submit")
s.click_ocr("OK", exact=True)   # exact text match
```

Returns `True` on success, `False` if no match found.

### `ocr_text_at(query)`

Return the exact OCR-detected text of the first result matching `query`, or
`None`.

```python
label = s.ocr_text_at("Version")
```

### `all_ocr_text()`

Return a flat list of every OCR-detected string in the export.

```python
for text in s.all_ocr_text():
    print(text)
```

---

## Image methods

These methods require `image_results` to be present in the export (use
`gui_detector.py --image` when exporting).

### `click_image(template="")`

Click the center of the first image template match.

```python
s.click_image("save_icon.png")  # filter by template filename
s.click_image()                  # click any match regardless of template
```

Returns `True` on success, `False` if no match found.

---

## Smart click

### `smart_click(query)`

Try all three search layers automatically, in priority order:

1. Element tree name match → `click_by_name`
2. OCR result text match → `click_ocr`
3. Image result template match → `click_image`

```python
s.smart_click("Save")       # resolves whichever layer finds it first
s.smart_click("Cancel")     # returns False without crashing if not found
```

Returns `True` on first successful hit, `False` if nothing was found.

---

## Introspection

### `summary()`

Return a dict summarising what the session contains.

```python
s.summary()
# {
#   "export": "dump.json",
#   "process_id": 1234,
#   "window_name": "Untitled - Notepad",
#   "total_elements": 42,
#   "ocr_results": 18,
#   "image_results": 1,
#   "buttons": 3,
#   "edits": 1,
# }
```

### `print_summary()`

Print a formatted summary table to stdout.

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

### `repr(s)`

```python
GUISession(window='Untitled - Notepad', pid=1234, elements=42, ocr=18, images=1)
```