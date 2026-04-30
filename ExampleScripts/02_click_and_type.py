"""
02_click_and_type.py
====================
Demonstrates clicking and typing using the Pywinauto element tree — the
most reliable automation layer because it uses stable automation IDs and
control types rather than pixel coordinates.

Scenario: open Notepad's File → Save As dialog and save a file.

Prerequisites
-------------
1.  Open Notepad with some text.
2.  Run the inspector to export its UI:
        python gui_detector.py --title "Notepad" --export notepad.json
3.  Run this script:
        python 02_click_and_type.py

Requirements
------------
    pip install pywinauto pyautogui
"""

import sys
from pathlib import Path

# Make sure gui_helper.py is on the path (one directory up from ExampleScripts)
sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession, find_all, element_center

EXPORT = "notepad.json"  # ← produced by gui_detector.py

# ── Load session ──────────────────────────────────────────────────────────────

s = GUISession(EXPORT, click_delay=0.4, move_duration=0.15)
s.print_summary()

# ── Layer 1: click by element name ───────────────────────────────────────────

print("\n[1] Opening File menu...")
s.click_by_name("File")                 # clicks the File menu item

print("[2] Clicking Save As...")
s.click_by_name("Save As")              # clicks the Save As menu entry

# ── Layer 1: click by automation ID (most robust) ────────────────────────────

# After clicking Save As a dialog opens. Re-export it or use smart_click:
print("[3] Typing filename...")
s.type_into("File name:", "my_document.txt")   # finds the Edit field and types

print("[4] Clicking Save button...")
s.click_by_name("Save", exact=True)     # exact=True avoids matching "Save As" again

# ── Bulk element inspection ───────────────────────────────────────────────────

print("\n--- All Button elements in this window ---")
for btn in s.all_buttons():
    x, y = element_center(btn)
    aid  = btn.get("automation_id") or "—"
    print(f"  [{btn['name']!r:25}]  auto_id={aid!r:20}  center=({x},{y})")

print("\n--- All Edit fields ---")
for edit in s.all_edits():
    x, y = element_center(edit)
    print(f"  [{edit['name']!r:25}]  auto_id={edit.get('automation_id')!r}  center=({x},{y})")

print("\n[+] Done.")
