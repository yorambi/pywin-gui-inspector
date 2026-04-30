# 07 — Bulk element processing

**Script:** `ExampleScripts/07_bulk_element_processing.py`

Demonstrates bulk traversal of the element tree using `flatten_tree` and
`find_all` — useful for form filling, auditing, scraping, or building
higher-level logic on top of the export.

## Prerequisites

```bash
python gui_detector.py --title "MyForm" --export form.json
```

## Run

```bash
python ExampleScripts/07_bulk_element_processing.py
```

## What it demonstrates

### Count and list elements by type

```python
from gui_helper import load_export, find_all, flatten_tree, element_center

data = load_export("form.json")
tree = data["element_tree"]

buttons   = find_all(tree, control_type="Button")
edits     = find_all(tree, control_type="Edit")
checkboxes = find_all(tree, control_type="CheckBox")

for edit in edits:
    x, y = element_center(edit)
    print(f"  {edit['name']:30}  auto_id={edit['automation_id']}  center=({x},{y})")
```

### Filter with list comprehensions

```python
nodes = flatten_tree(tree)

# Elements with automation IDs
reliable = [n for n in nodes if n.get("automation_id")]

# Disabled elements
disabled = [n for n in nodes if not n.get("is_enabled", True)]
```

### Automated form filling

```python
from gui_helper import GUISession

s = GUISession("form.json", click_delay=0.3)

FORM_DATA = {
    "First Name": "Jane",
    "Last Name":  "Smith",
    "Email":      "jane@example.com",
}

for field, value in FORM_DATA.items():
    s.type_into(field, value)

for checkbox in ["Newsletter", "Terms and Conditions"]:
    s.smart_click(checkbox)
```