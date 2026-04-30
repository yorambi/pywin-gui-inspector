"""
03_ocr_text_search.py
=====================
Demonstrates using EasyOCR results to find and click elements by their
visible text — useful for controls that Pywinauto can't identify by
automation ID (e.g. custom-rendered buttons, Electron apps, games).

Scenario: find every visible button by text on screen, then click a
specific one by its label.

Prerequisites
-------------
1.  Open any application (e.g. a browser, Electron app).
2.  Run the inspector with OCR enabled:
        python gui_detector.py --title "MyApp" --ocr --export myapp.json
3.  Run this script:
        python 03_ocr_text_search.py

Requirements
------------
    pip install pywinauto easyocr Pillow pyautogui
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession, find_all_ocr, ocr_center

EXPORT     = "myapp.json"   # ← change to your export filename
CLICK_TEXT = "Submit"       # ← the button text you want to click

# ── Load session ──────────────────────────────────────────────────────────────

s = GUISession(EXPORT)
s.print_summary()

if not s.ocr_results:
    print("[!] No OCR results in export.")
    print("    Re-run gui_detector.py with --ocr or --find to capture them.")
    sys.exit(1)

# ── Print all OCR-detected text ───────────────────────────────────────────────

print(f"\nAll OCR-detected text ({len(s.ocr_results)} results):")
for r in s.ocr_results:
    conf   = int(r.get("confidence", 0) * 100)
    rect   = r["rect"]
    coords = f"({rect['left']},{rect['top']})→({rect['right']},{rect['bottom']})"
    print(f"  [{conf:>3}%]  {r['text']!r:<30}  {coords}")

# ── Find all results matching a keyword ──────────────────────────────────────

matches = find_all_ocr(s.ocr_results, CLICK_TEXT)
print(f"\nOCR results matching {CLICK_TEXT!r}: {len(matches)}")
for m in matches:
    x, y = ocr_center(m)
    print(f"  {m['text']!r}  conf={int(m['confidence']*100)}%  center=({x},{y})")

# ── Click the first match ─────────────────────────────────────────────────────

if matches:
    print(f"\n[*] Clicking first OCR match for {CLICK_TEXT!r}...")
    s.click_ocr(CLICK_TEXT)
    print("[+] Clicked.")
else:
    print(f"\n[!] {CLICK_TEXT!r} not found in OCR results.")
    print("    Check the text above and update CLICK_TEXT.")

# ── Exact match example ───────────────────────────────────────────────────────

# Use exact=True to avoid "Save As" matching when you only want "Save"
print("\n[*] Trying exact OCR match for 'OK'...")
result = s.click_ocr("OK", exact=True)
if not result:
    print("    'OK' not found exactly — falling back to smart_click...")
    s.smart_click("OK")
