"""
09_full_workflow.py
===================
A complete end-to-end example showing all three search layers working
together in a realistic automation workflow.

Scenario: automate a "Save As" + "Find and Replace" workflow in Notepad
using every available method to demonstrate how the layers fall back on
each other.

Workflow
--------
  Step 1  Export the window (run gui_detector.py first)
  Step 2  Open File menu via element tree
  Step 3  Click Save As via OCR fallback
  Step 4  Type filename and confirm via keyboard
  Step 5  Use smart_click for a mixed-layer search
  Step 6  Demonstrate error handling when an element is missing
  Step 7  Screenshot the final result

Prerequisites
-------------
1.  Open Notepad, type some text.
2.  Export the window:
        python gui_detector.py --title "Notepad" --ocr --export notepad.json
3.  Run this script:
        python 09_full_workflow.py

Requirements
------------
    pip install pywinauto easyocr Pillow pyautogui
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession, find_all, element_center

EXPORT   = "notepad.json"
FILENAME = "automated_output.txt"

# ── Setup ─────────────────────────────────────────────────────────────────────

s = GUISession(EXPORT, click_delay=0.4, move_duration=0.2)
s.print_summary()

print("\n" + "=" * 60)
print("Starting full automation workflow")
print("=" * 60)

# ── Step 1: Layer 1 — element tree ────────────────────────────────────────────

print("\n[Step 1] Opening File menu via element tree...")
ok = s.click_by_name("File")
if not ok:
    print("  [!] 'File' not in element tree, trying OCR...")
    ok = s.click_ocr("File")
print(f"  {'[+] Opened' if ok else '[!] Failed'}")
time.sleep(0.3)

# ── Step 2: Layer 2 — OCR fallback ───────────────────────────────────────────

print("\n[Step 2] Clicking 'Save As' (OCR)...")
ok = s.click_ocr("Save As", exact=True)
if not ok:
    print("  [!] Not in OCR, trying element tree...")
    ok = s.click_by_name("Save As")
print(f"  {'[+] Clicked' if ok else '[!] Failed'}")
time.sleep(0.5)

# ── Step 3: Type filename into dialog ─────────────────────────────────────────

print(f"\n[Step 3] Typing filename: {FILENAME!r}")
ok = s.type_into("File name:", FILENAME)
if not ok:
    # Dialog might have changed — try clicking the first visible Edit field
    print("  [!] 'File name:' not found, clicking first Edit field...")
    edits = s.all_edits()
    if edits:
        import pyautogui
        x, y = element_center(edits[0])
        pyautogui.click(x, y)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.typewrite(FILENAME, interval=0.05)
        ok = True
print(f"  {'[+] Typed' if ok else '[!] Failed'}")
time.sleep(0.2)

# ── Step 4: Confirm with keyboard ─────────────────────────────────────────────

print("\n[Step 4] Pressing Enter to confirm...")
import pyautogui
pyautogui.press("enter")
time.sleep(0.5)

# ── Step 5: Layer 3 — smart_click (auto-resolves) ────────────────────────────

print("\n[Step 5] Opening Find & Replace via smart_click...")
s.smart_click("Edit")
time.sleep(0.3)
s.smart_click("Find")
time.sleep(0.4)

# ── Step 6: Error handling ────────────────────────────────────────────────────

print("\n[Step 6] Attempting to click a button that may not exist...")
ok = s.smart_click("Replace All")
if not ok:
    print("  [!] 'Replace All' not found — dialog may not be open yet.")
    print("       In a real script, handle this with a retry or a wait loop.")

# ── Step 7: Screenshot ────────────────────────────────────────────────────────

print("\n[Step 7] Taking screenshot of final state...")
screenshot_path = Path(__file__).parent / "workflow_result.png"
pyautogui.screenshot(str(screenshot_path))
print(f"  [+] Screenshot saved: {screenshot_path}")

# ── Summary ───────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Workflow complete.")
print(f"  File saved as : {FILENAME}")
print(f"  Screenshot    : workflow_result.png")
print("""
Layers used
-----------
  ✓ Element tree  — File menu, Save button
  ✓ OCR           — Save As (no automation_id in this build)
  ✓ smart_click   — Edit menu, Find, Replace All (auto-resolved)
  ✓ Keyboard      — Enter to confirm dialog
  ✓ Fallback      — first Edit field when label not matched
""")
