"""
01_inspect_and_export.py
========================
Step 1 of the typical workflow: run gui_detector.py to inspect any open
window and save the result to a JSON export.

This script shows the three most common ways to target a window, then
loads the resulting export to print a quick summary.

Run one of the shell commands below FIRST, then execute this script.

Shell commands
--------------
    # Interactive — lists all windows, you pick:
    python gui_detector.py --export dump.json

    # By partial window title:
    python gui_detector.py --title "Notepad" --export dump.json

    # By process ID (find PID in Task Manager):
    python gui_detector.py --pid 1234 --export dump.json

    # With OCR + image search all at once:
    python gui_detector.py --title "Notepad" --ocr --image save_icon.png --export dump.json

Requirements
------------
    pip install pywinauto
    pip install easyocr Pillow          # for --ocr / --find
    pip install pyautogui opencv-python  # for --image
"""

import json
import sys
from pathlib import Path

EXPORT = "dump.json"   # ← change to match your --export filename

# ── Load and inspect the export ───────────────────────────────────────────────

if not Path(EXPORT).exists():
    print(f"[!] Export file not found: {EXPORT!r}")
    print("    Run gui_detector.py first — see the shell commands at the top of this file.")
    sys.exit(1)

with open(EXPORT, encoding="utf-8") as f:
    data = json.load(f)

# The export is either a wrapped dict (with element_tree) or a bare tree
tree          = data.get("element_tree", data)
ocr_results   = data.get("ocr_results", [])
image_results = data.get("image_results", [])

print(f"\nWindow   : {tree.get('name')!r}")
print(f"PID      : {tree.get('process_id')}")
print(f"Framework: {tree.get('framework_id')}")
print(f"Rect     : {tree.get('rectangle')}")
print(f"OCR hits : {len(ocr_results)}")
print(f"Img hits : {len(image_results)}")

# ── Count elements by control type ───────────────────────────────────────────

def count_types(node: dict, counts: dict = None) -> dict:
    if counts is None:
        counts = {}
    ct = node.get("control_type") or "Unknown"
    counts[ct] = counts.get(ct, 0) + 1
    for child in node.get("children", []):
        count_types(child, counts)
    return counts

counts = count_types(tree)
print("\nElement types found:")
for ctype, n in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {ctype:<20} {n}")

# ── Print OCR results if present ──────────────────────────────────────────────

if ocr_results:
    print(f"\nOCR detected text ({len(ocr_results)} results):")
    for r in ocr_results:
        conf = int(r.get("confidence", 0) * 100)
        print(f"  [{conf:>3}%]  {r['text']!r}")

print(f"\n[+] Export loaded from: {EXPORT}")
print("    Pass this file to GUISession or ScriptWriter in the next examples.")
