# 06 — Script writer

**Script:** `ExampleScripts/06_script_writer.py`

Generates ready-to-run Python automation scripts from plain-English
instructions. Steps are resolved against the JSON export so the output code
uses the best available method for each action.

## Prerequisites

```bash
python gui_detector.py --title "Notepad" --ocr --export notepad.json
```

## Run

```bash
python ExampleScripts/06_script_writer.py
```

## What it demonstrates

### Preview a generated script

```python
from gui_helper import ScriptWriter

sw = ScriptWriter("notepad.json")

sw.preview(
    "click File, "
    "click Save As, "
    "type my_report.txt into File name:, "
    "click Save"
)
```

Output:

```python
import time, sys
from pathlib import Path
import pyautogui
sys.path.insert(0, ...)
from gui_helper import GUISession

s = GUISession('notepad.json', click_delay=0.4, move_duration=0.15)

s.click_by_auto_id('file_menu')
s.click_ocr('Save As')
s.type_into('File name:', 'my_report.txt')
s.click_by_auto_id('btn_save')
```

### Write to a file

```python
sw.write(
    "click File, click Save As, type report.txt into File name:, click Save",
    output="generated_save_as.py",
)
```

### Multi-line instructions

```python
sw.preview("""
click Username
type admin into Username
click Password
type secret123 into Password
wait 1 second
click Login
press Enter
screenshot as login_result.png
""")
```

### Batch generation

```python
workflows = {
    "open_file.py":  "click File, click Open, type report.txt into File name:, press Enter",
    "find_text.py":  "click Edit, click Find, type hello into Find what:, press Enter, close",
    "print_doc.py":  "hotkey ctrl+p, wait 1 second, click Print",
}

for filename, steps in workflows.items():
    sw.write(steps, output=filename)
```