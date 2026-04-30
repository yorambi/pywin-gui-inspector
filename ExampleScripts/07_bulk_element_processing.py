"""
07_bulk_element_processing.py
==============================
Demonstrates bulk traversal of the element tree using flatten_tree and
find_all — useful for form filling, auditing, scraping, or building
higher-level logic on top of the export.

Use cases shown
---------------
  - Fill every Edit field in a form from a data dict
  - Click every checkbox that matches a list of names
  - Print a full audit of all elements with their coordinates
  - Filter elements by any combination of properties

Prerequisites
-------------
1.  Export the target window:
        python gui_detector.py --title "MyForm" --export form.json
2.  Run this script:
        python 07_bulk_element_processing.py

Requirements
------------
    pip install pywinauto pyautogui
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import (
    GUISession,
    load_export,
    flatten_tree,
    find_all,
    element_center,
    element_rect,
    print_flat,
)

EXPORT = "form.json"   # ← your export filename

# ── Load raw data (no session needed for read-only work) ──────────────────────

data = load_export(EXPORT)
tree = data.get("element_tree", data)

# ── 1. Print full flat element list ──────────────────────────────────────────

print("=" * 60)
print("All elements (flat view):")
print("=" * 60)
print_flat(tree)

# ── 2. Collect all elements as a flat list ────────────────────────────────────

all_elements = flatten_tree(tree)
print(f"\nTotal elements: {len(all_elements)}")

# ── 3. Filter with find_all ───────────────────────────────────────────────────

buttons    = find_all(tree, control_type="Button")
edits      = find_all(tree, control_type="Edit")
checkboxes = find_all(tree, control_type="CheckBox")
combo_boxes = find_all(tree, control_type="ComboBox")

print(f"\nButtons    : {len(buttons)}")
print(f"Edit fields: {len(edits)}")
print(f"CheckBoxes : {len(checkboxes)}")
print(f"ComboBoxes : {len(combo_boxes)}")

# ── 4. Print all edit fields with coordinates ─────────────────────────────────

print("\n--- Edit fields ---")
for edit in edits:
    x, y = element_center(edit)
    l, t, r, b = element_rect(edit)
    name = edit.get("name") or "<no name>"
    aid  = edit.get("automation_id") or "—"
    print(f"  {name!r:30}  auto_id={aid!r:20}  center=({x},{y})  size={r-l}x{b-t}")

# ── 5. List comprehension filtering ───────────────────────────────────────────

# Elements with automation IDs (most reliable to interact with)
with_aid = [e for e in all_elements if e.get("automation_id")]
print(f"\nElements with automation_id: {len(with_aid)}")
for e in with_aid[:10]:  # show first 10
    print(f"  [{e['control_type']!r:12}] {e['name']!r:25} auto_id={e['automation_id']!r}")

# Disabled elements
disabled = [e for e in all_elements if not e.get("is_enabled", True)]
print(f"\nDisabled elements: {len(disabled)}")
for e in disabled:
    print(f"  [{e['control_type']!r:12}] {e['name']!r}")

# ── 6. Automated form filling (GUISession) ────────────────────────────────────

print("\n--- Auto-fill form fields ---")

# Map field names to values — customise for your form
FORM_DATA = {
    "First Name":   "Jane",
    "Last Name":    "Smith",
    "Email":        "jane@example.com",
    "Phone":        "555-1234",
    "Company":      "Acme Corp",
}

CHECKBOXES_TO_TICK = ["Newsletter", "Terms and Conditions"]

s = GUISession(EXPORT, click_delay=0.3)

for field_name, value in FORM_DATA.items():
    print(f"  Filling {field_name!r} → {value!r}")
    success = s.type_into(field_name, value)
    if not success:
        print(f"    [!] Field {field_name!r} not found — skipping")

for cb_name in CHECKBOXES_TO_TICK:
    print(f"  Ticking checkbox {cb_name!r}")
    s.smart_click(cb_name)

print("\n[+] Form filled.")
