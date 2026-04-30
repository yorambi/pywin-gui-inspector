"""
06_script_writer.py
===================
Demonstrates ScriptWriter — give it plain-English instructions and it
produces a ready-to-run Python automation script tailored to the elements
it finds in your JSON export.

ScriptWriter resolves each step against the export:
  1. automation_id  → click_by_auto_id  (most reliable)
  2. element name   → click_by_name
  3. OCR text       → click_ocr
  4. image template → click_image
  5. not found      → smart_click + warning comment

Prerequisites
-------------
1.  Export the target window (with OCR if needed):
        python gui_detector.py --title "Notepad" --ocr --export notepad.json
2.  Run this script:
        python 06_script_writer.py

Requirements
------------
    pip install pywinauto easyocr Pillow pyautogui
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import ScriptWriter

EXPORT = "notepad.json"   # ← your export filename

sw = ScriptWriter(EXPORT)

# ── Example 1 — preview without saving ───────────────────────────────────────

print("=" * 60)
print("Example 1: Save As workflow (preview only)")
print("=" * 60)
sw.preview(
    "click File, "
    "click Save As, "
    "type my_report.txt into File name:, "
    "click Save"
)

# ── Example 2 — write to a .py file ──────────────────────────────────────────

print("\n" + "=" * 60)
print("Example 2: Write Save As script to file")
print("=" * 60)
sw.write(
    "click File, click Save As, type my_report.txt into File name:, click Save",
    output=Path(__file__).parent / "generated_save_as.py",
)

# ── Example 3 — multi-step form workflow ──────────────────────────────────────

print("\n" + "=" * 60)
print("Example 3: Multi-step form with waits and key presses")
print("=" * 60)
sw.preview(
    "click Username, "
    "type admin into Username, "
    "click Password, "
    "type secret123 into Password, "
    "wait 1 second, "
    "click Login, "
    "press Enter, "
    "screenshot as login_result.png"
)

# ── Example 4 — generate from a multiline string ─────────────────────────────

print("\n" + "=" * 60)
print("Example 4: Multiline instructions (newline-separated)")
print("=" * 60)
instructions = """
open the Edit menu
click Find
type hello into Find what:
press Enter
wait 2 seconds
close
"""
script = sw.generate(instructions)
print(script)

# ── Example 5 — write all generated scripts to the output directory ───────────

print("\n" + "=" * 60)
print("Example 5: Batch generate multiple scripts")
print("=" * 60)

workflows = {
    "generated_open_file.py":  "click File, click Open, type report.txt into File name:, press Enter",
    "generated_find_text.py":  "click Edit, click Find, type hello into Find what:, press Enter, close",
    "generated_print.py":      "hotkey ctrl+p, wait 1 second, click Print",
}

for filename, steps in workflows.items():
    out = Path(__file__).parent / filename
    sw.write(steps, output=out)

print("\n[+] All scripts generated.")
print("    Open the generated_*.py files to see the results.")
