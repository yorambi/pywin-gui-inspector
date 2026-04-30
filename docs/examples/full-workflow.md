# 09 — Full workflow

**Script:** `ExampleScripts/09_full_workflow.py`

A complete end-to-end example that uses all three search layers together in a
realistic automation scenario: **Save As + Find and Replace** in Notepad.

## Prerequisites

```bash
# Open Notepad with some text, then:
python gui_detector.py --title "Notepad" --ocr --export notepad.json
```

## Run

```bash
python ExampleScripts/09_full_workflow.py
```

## Workflow steps

```
Step 1  Open File menu via element tree
Step 2  Click Save As via OCR fallback
Step 3  Type filename into the dialog
Step 4  Confirm with keyboard Enter
Step 5  Open Find & Replace via smart_click
Step 6  Handle missing element gracefully
Step 7  Screenshot the final state
```

## Key patterns shown

### Layer 1 with OCR fallback

```python
ok = s.click_by_name("File")
if not ok:
    ok = s.click_ocr("File")
```

### Layer 2 (OCR) with element tree fallback

```python
ok = s.click_ocr("Save As", exact=True)
if not ok:
    ok = s.click_by_name("Save As")
```

### Fallback to first available Edit field

```python
ok = s.type_into("File name:", FILENAME)
if not ok:
    edits = s.all_edits()
    if edits:
        x, y = element_center(edits[0])
        pyautogui.click(x, y)
        pyautogui.typewrite(FILENAME, interval=0.05)
```

### Graceful handling of missing elements

```python
ok = s.smart_click("Replace All")
if not ok:
    print("Not found — dialog may not be open yet. Add a retry loop here.")
```

### Screenshot

```python
import pyautogui
pyautogui.screenshot("workflow_result.png")
```

## Layers used

| Layer | Used for |
|---|---|
| Element tree | `File` menu, `Save` button |
| OCR | `Save As` (no automation ID in this build) |
| `smart_click` | `Edit` menu, `Find`, `Replace All` |
| Keyboard | `Enter` to confirm the dialog |
| Edit fallback | Typing when label match fails |