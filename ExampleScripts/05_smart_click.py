"""
05_smart_click.py
=================
Demonstrates smart_click — the automatic three-layer fallback that tries
every search method in priority order so you don't have to know which one
will work ahead of time.

Priority order
--------------
  1. Element tree  (automation_id → name)    most reliable
  2. OCR results   (visible text)            good for unlabelled controls
  3. Image results (pixel template)          last resort for icon-only buttons

If none of the layers finds the target, a warning is printed and the
function returns False — no crash.

Scenario: automate a multi-step workflow where some buttons are well-labelled,
          some are only visible via OCR, and one is an icon without text.

Prerequisites
-------------
1.  Export the target window with all three search modes:
        python gui_detector.py --title "MyApp" --ocr --image toolbar.png --export myapp.json
2.  Run this script:
        python 05_smart_click.py

Requirements
------------
    pip install pywinauto easyocr Pillow pyautogui opencv-python
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession

EXPORT = "myapp.json"   # ← your export filename

# ── Load session ──────────────────────────────────────────────────────────────

s = GUISession(EXPORT, click_delay=0.5)
s.print_summary()

# ── smart_click each target — no need to know which layer will match ──────────

targets = [
    "File",           # likely in element tree (MenuItem)
    "Save",           # likely in element tree or OCR
    "toolbar.png",    # likely in image results
    "Submit",         # OCR fallback for custom-rendered button
    "Nonexistent",    # will warn and return False — no crash
]

print("\nRunning smart_click for each target:\n")
for target in targets:
    print(f"  → smart_click({target!r})")
    success = s.smart_click(target)
    status  = "✓ clicked" if success else "✗ not found"
    print(f"    {status}\n")
    time.sleep(0.3)

# ── Graceful fallback pattern ─────────────────────────────────────────────────

# Use this when you want to try a specific method first with a defined fallback
print("Custom fallback chain for 'OK':")
if   s.click_by_name("OK", exact=True):    print("  → clicked by name")
elif s.click_ocr("OK", exact=True):        print("  → clicked by OCR")
elif s.click_image("ok_button.png"):       print("  → clicked by image")
else:                                       print("  → not found in any layer")
