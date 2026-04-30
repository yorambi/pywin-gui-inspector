# pywin-gui-inspector

A Windows GUI inspection and automation toolkit built on
[Pywinauto](https://pywinauto.readthedocs.io/),
[EasyOCR](https://github.com/JaidedAI/EasyOCR), and
[PyAutoGUI](https://github.com/asweigart/pyautogui).

**Inspect** any running application's UI element tree, **search** it by text or
pixel template, **export** the results to JSON, and **drive** any automation
script from that export using the companion helper library.

---

## At a glance

```bash
# Inspect Notepad and export everything
python gui_detector.py --title "Notepad" --ocr --export notepad.json

# Use the export to drive automation
python
>>> from gui_helper import GUISession
>>> s = GUISession("notepad.json")
>>> s.type_into("File name:", "report.txt")
>>> s.smart_click("Save")
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
api/gui-session
api/script-writer
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