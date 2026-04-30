# Examples

Each example is a self-contained script in the `ExampleScripts/` directory.
Run `gui_detector.py` first to produce the required JSON export, then run the
example script.

| Script | What it shows |
|---|---|
| {doc}`inspect-and-export` | Load and summarise a JSON export |
| {doc}`click-and-type` | Click and type via the element tree |
| {doc}`ocr-search` | Find and click elements by visible text |
| {doc}`image-template` | Find and click icon-only buttons by template image |
| {doc}`smart-click` | Automatic three-layer fallback |
| {doc}`script-writer` | Generate automation scripts from plain-English steps |
| {doc}`bulk-processing` | Bulk element traversal and form filling |
| {doc}`watch-mode` | Monitor a window for UI changes |
| {doc}`full-workflow` | End-to-end example combining all layers |

## Prerequisites

All examples require a JSON export:

```bash
# Generic export
python gui_detector.py --title "MyApp" --ocr --export myapp.json

# Notepad-specific (used by several examples)
python gui_detector.py --title "Notepad" --ocr --export notepad.json
```