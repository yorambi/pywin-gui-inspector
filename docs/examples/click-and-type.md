# 02 — Click and type

**Script:** `ExampleScripts/02_click_and_type.py`

Automates Notepad's **File → Save As** dialog using the Pywinauto element tree —
the most reliable layer because it uses stable automation IDs and control types.

## Prerequisites

```bash
# Open Notepad with some text, then:
python gui_detector.py --title "Notepad" --export notepad.json
```

## Run

```bash
python ExampleScripts/02_click_and_type.py
```

## What it demonstrates

```python
from gui_helper import GUISession, find_all, element_center

s = GUISession("notepad.json", click_delay=0.4, move_duration=0.15)

# Click by element name
s.click_by_name("File")
s.click_by_name("Save As")

# Type into an Edit field
s.type_into("File name:", "my_document.txt")

# exact=True avoids matching "Save As" again
s.click_by_name("Save", exact=True)
```

## Listing all elements

The script also prints every `Button` and `Edit` element with its automation
ID and screen center — useful when building your own automation:

```
--- All Button elements ---
  ['Save'     ]  auto_id='1'      center=(500, 420)
  ['Cancel'   ]  auto_id='2'      center=(590, 420)

--- All Edit fields ---
  ['File name:']  auto_id='1001'   center=(350, 320)
```