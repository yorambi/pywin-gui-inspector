"""
08_watch_mode.py
================
Demonstrates using gui_detector.py's --watch flag to monitor a window
for UI changes in real time, and how to react to those changes
programmatically using GUISession.

Two parts
---------
  Part A — shell command to start watching (prints diffs to console)
  Part B — Python polling loop using GUISession to take action when
            a specific element appears or disappears

Use cases
---------
  - Wait for a progress bar to complete, then click OK
  - Detect when an error dialog appears and dismiss it
  - React to a login form appearing after a page load
  - Monitor for new list items in a live dashboard

Prerequisites (Part A — shell watcher)
---------------------------------------
    python gui_detector.py --watch 1234 --interval 0.5

Prerequisites (Part B — Python polling)
-----------------------------------------
1.  Export the baseline window:
        python gui_detector.py --pid 1234 --export baseline.json
2.  Run this script:
        python 08_watch_mode.py

Requirements
------------
    pip install pywinauto pyautogui
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gui_helper import GUISession, find_by_name, flatten_tree

EXPORT      = "baseline.json"   # ← baseline export from gui_detector.py
TARGET_PID  = None              # ← set to your PID, or leave None to read from export
POLL_SEC    = 1.0               # how often to re-snapshot the window (seconds)
TIMEOUT_SEC = 60.0              # give up after this many seconds

# ── Load baseline ─────────────────────────────────────────────────────────────

s = GUISession(EXPORT)
s.print_summary()

pid = TARGET_PID or s._pid
if not pid:
    print("[!] No PID found. Set TARGET_PID or provide an export with a process_id.")
    sys.exit(1)

# ── Helper: take a live snapshot of element names ────────────────────────────

def live_snapshot(pid: int, max_depth: int = 6) -> set[str]:
    """Connect live to the process and return the current set of element names."""
    try:
        from pywinauto import Application
        app  = Application(backend="uia").connect(process=pid)
        wins = app.windows()
        if not wins:
            return set()

        def _walk(node) -> set:
            names = {node.window_text().strip()}
            for child in node.children():
                names |= _walk(child)
            return names

        return _walk(wins[0])
    except Exception as exc:
        print(f"[!] Snapshot error: {exc}")
        return set()

# ── Part B: poll for a specific element to appear ────────────────────────────

WAIT_FOR     = "OK"      # ← element name to wait for
CLICK_WHEN_FOUND = True  # ← automatically click it when found

print(f"\n[*] Polling PID {pid} every {POLL_SEC}s, waiting for {WAIT_FOR!r}...")
print("    Press Ctrl-C to stop.\n")

previous = live_snapshot(pid)
print(f"  [*] Baseline: {len(previous)} elements")

start = time.time()
found = False

try:
    while time.time() - start < TIMEOUT_SEC:
        time.sleep(POLL_SEC)
        current = live_snapshot(pid)

        added   = current - previous
        removed = previous - current

        if added:
            print(f"  [+] New:     {sorted(added)}")
        if removed:
            print(f"  [-] Removed: {sorted(removed)}")
        if not added and not removed:
            print("  [=] No change")

        # React when the target element appears
        if WAIT_FOR in added or WAIT_FOR in current:
            print(f"\n  [!] {WAIT_FOR!r} detected!")
            found = True
            if CLICK_WHEN_FOUND:
                print(f"  [*] Clicking {WAIT_FOR!r}...")
                s.smart_click(WAIT_FOR)
                print("  [+] Clicked.")
            break

        previous = current

except KeyboardInterrupt:
    print("\n[*] Stopped by user.")

if not found:
    print(f"\n[!] {WAIT_FOR!r} did not appear within {TIMEOUT_SEC}s.")
else:
    print(f"\n[+] Done — {WAIT_FOR!r} was found and handled.")
