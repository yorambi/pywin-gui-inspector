# `ScriptWriter`

Generates ready-to-run Python automation scripts from plain-English
instructions. Each instruction step is resolved against the JSON export so the
emitted code uses the most reliable available method for each action.

## Constructor

```python
from gui_helper import ScriptWriter

sw = ScriptWriter("dump.json")
```

Loads the same JSON export format as `GUISession`.

---

## Resolution priority

For every `click <target>` step, `ScriptWriter` checks the export in order:

| Priority | Condition | Emitted code |
|---|---|---|
| 1 | Element found **with** `automation_id` | `s.click_by_auto_id(...)` |
| 2 | Element found **without** `automation_id` | `s.click_by_name(...)` |
| 3 | Found in OCR results | `s.click_ocr(...)` |
| 4 | Found in image results | `s.click_image(...)` |
| 5 | Not found anywhere | `s.smart_click(...)` + `# WARNING` comment |

---

## Instruction syntax

Instructions are a comma-separated or newline-separated list of steps:

| Instruction | Emitted code |
|---|---|
| `click Save` | `s.click_by_auto_id('btn_save')` *(if automation_id found)* |
| `click Save As` | `s.click_ocr('Save As')` *(if only in OCR)* |
| `type report.txt into File name:` | `s.type_into('File name:', 'report.txt')` |
| `press enter` | `pyautogui.press('enter')` |
| `hotkey ctrl+s` | `pyautogui.hotkey('ctrl', 's')` |
| `wait 2 seconds` | `time.sleep(2)` |
| `wait 0.5 seconds` | `time.sleep(0.5)` |
| `screenshot as result.png` | `pyautogui.screenshot('result.png')` |
| `open the Edit menu` | resolved via element tree / OCR |
| `close` | `pyautogui.hotkey('alt', 'f4')` |

---

## Methods

### `generate(instructions) → str`

Return a complete, ready-to-run Python script as a string.

```python
script = sw.generate("click File, click Save As, type report.txt into File name:, click Save")
print(script)
```

```python
import time
import sys
from pathlib import Path

import pyautogui

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession

s = GUISession('dump.json', click_delay=0.4, move_duration=0.15)

s.click_by_auto_id('file_menu')
s.click_ocr('Save As')
s.type_into('File name:', 'report.txt')
s.click_by_auto_id('btn_save')
```

### `preview(instructions)`

Print the generated script to stdout. Equivalent to `print(sw.generate(...))`.

```python
sw.preview(
    "click File, "
    "click Save As, "
    "type report.txt into File name:, "
    "click Save"
)
```

### `write(instructions, output="generated_script.py") → Path`

Write the generated script to a file and return its path.

```python
sw.write(
    "click File, click Save As, type report.txt into File name:, click Save",
    output="save_as_workflow.py",
)
# [ScriptWriter] Written → save_as_workflow.py
```

---

## Multi-line instructions

Use a triple-quoted string for multi-step workflows — newlines are treated as
step separators:

```python
sw.preview("""
open the Edit menu
click Find
type hello into Find what:
press Enter
wait 2 seconds
close
""")
```

---

## Batch generation

```python
workflows = {
    "open_file.py":  "click File, click Open, type report.txt into File name:, press Enter",
    "find_text.py":  "click Edit, click Find, type hello into Find what:, press Enter, close",
    "print_doc.py":  "hotkey ctrl+p, wait 1 second, click Print",
}

for filename, steps in workflows.items():
    sw.write(steps, output=filename)
```