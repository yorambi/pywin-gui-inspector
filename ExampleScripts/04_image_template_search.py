"""
04_image_template_search.py
===========================
Demonstrates PyAutoGUI template matching to find and click buttons or
controls that have no text and no automation ID — icon-only toolbar
buttons, custom-drawn widgets, game UI elements, etc.

How to capture a template image
--------------------------------
1.  Take a screenshot of the target button (Windows: Win+Shift+S).
2.  Crop it tightly to just the icon — save as a .png file.
3.  Pass it to --image when running gui_detector.py.

Scenario: find a toolbar icon (e.g. the Save icon in a text editor)
          and click it.

Prerequisites
-------------
1.  Open an application with a toolbar icon you want to click.
2.  Capture a .png screenshot of that icon (cropped tightly).
3.  Run the inspector with image search:
        python gui_detector.py --title "MyApp" --image save_icon.png --export myapp.json
4.  Run this script:
        python 04_image_template_search.py

Requirements
------------
    pip install pywinauto pyautogui opencv-python
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession, find_image_result, image_center

EXPORT   = "myapp.json"      # ← your export filename
TEMPLATE = "save_icon.png"   # ← the template image you passed to --image

# ── Load session ──────────────────────────────────────────────────────────────

s = GUISession(EXPORT)
s.print_summary()

if not s.image_results:
    print("[!] No image results in export.")
    print("    Re-run gui_detector.py with --image <file.png> to capture them.")
    sys.exit(1)

# ── Print all image matches ───────────────────────────────────────────────────

print(f"\nAll image template matches ({len(s.image_results)} results):")
for r in s.image_results:
    rect   = r["rect"]
    center = r["center"]
    tmpl   = Path(r.get("template", "?")).name
    coords = f"({rect['left']},{rect['top']})→({rect['right']},{rect['bottom']})"
    print(f"  template={tmpl!r:20}  center=({center['x']},{center['y']})  rect={coords}")

# ── Click by template filename ────────────────────────────────────────────────

result = find_image_result(s.image_results, TEMPLATE)
if result:
    x, y = image_center(result)
    print(f"\n[*] Found {TEMPLATE!r} at center=({x},{y})")
    print("[*] Clicking...")
    s.click_image(TEMPLATE)
    print("[+] Clicked.")
else:
    print(f"\n[!] Template {TEMPLATE!r} not found in image results.")
    print("    Check that the template filename matches and re-run the inspector.")

# ── Click first available match regardless of template name ──────────────────

print("\n[*] Clicking first available image match (any template)...")
s.click_image()   # no filter — clicks whatever was found

# ── Tips for better template matching ─────────────────────────────────────────

print("""
Tips for reliable image matching
---------------------------------
- Capture the template at 100% zoom — scaling breaks the match.
- Use .png, not .jpg (JPEG compression changes pixels slightly).
- Crop tightly — extra whitespace reduces confidence.
- If confidence=0.9 misses, try 0.8: pass --confidence 0.8 to gui_detector.py.
- If the icon changes state (hover, pressed), capture each state separately.
""")
