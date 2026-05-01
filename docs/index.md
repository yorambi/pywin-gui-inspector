# pywin-gui-inspector

A Windows GUI inspection, automation, and recording toolkit built on
[Pywinauto](https://pywinauto.readthedocs.io/),
[EasyOCR](https://github.com/JaidedAI/EasyOCR), and
[PyAutoGUI](https://github.com/asweigart/pyautogui).

**Inspect** any running application's UI element tree, **export** it to JSON,
**automate** from the export or live, and **record** your own interactions to
generate a replay script — all through the `pywin_gui_inspector` package.

---

## At a glance

```bash
# Install
pip install -e ".[all]"

# 1. Inspect Notepad and export to JSON
python gui_detector.py --title "Notepad" --ocr --export notepad.json
```

```python
# 2. Automate from the export
from pywin_gui_inspector import GUISession

s = GUISession("notepad.json")
s.smart_click("Save")

# 3. Live automation — no snapshot needed
from pywin_gui_inspector import connect_application

s = connect_application(title="Notepad")
s.menu_click("File->Save As")
s.set_text("File name:||Edit", "report.txt")
```

```bash
# 4. Record interactions → replay script
python gui_recorder.py      # press F7 to start, F9 to stop
```

```bash
# 5. Run the tests
pytest tests/ -v            # 88 unit tests, no live session needed
```

---

## Contents

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
```

```{toctree}
:maxdepth: 2
:caption: Reference

cli-reference
json-format
live-mode
recorder
api/gui-session
api/script-writer
api/live-session
api/tree-helpers
api/ocr-helpers
api/image-helpers
```

```{toctree}
:maxdepth: 1
:caption: Examples

examples/index
examples/inspect-and-export
examples/click-and-type
examples/ocr-search
examples/image-template
examples/smart-click
examples/script-writer
examples/bulk-processing
examples/watch-mode
examples/full-workflow
```

```{toctree}
:maxdepth: 1
:caption: Internals

how-it-works
limitations
```