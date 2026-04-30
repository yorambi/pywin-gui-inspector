"""
GUI Object Detector using Pywinauto
====================================
Detects and inspects GUI elements in any running Windows application.

Usage:
    python gui_detector.py                      # Interactive mode
    python gui_detector.py --pid 1234           # Target by process ID
    python gui_detector.py --title "Notepad"    # Target by window title
    python gui_detector.py --dump               # Dump all open windows
    python gui_detector.py --export out.json    # Export results to JSON
"""

import argparse
import ctypes
import json
import os
import sys
import time
from typing import Optional


# ── Admin elevation ───────────────────────────────────────────────────────────

def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def elevate() -> bool:
    """
    Try to re-launch this script with UAC elevation.
    Returns True if elevation was successfully handed off (caller should exit).
    Returns False if the user declined or elevation is unavailable.
    """
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}',
            None,
            1,          # SW_NORMAL
        )
        if ret > 32:
            return True   # elevated child launched; caller exits
    except Exception:
        pass
    return False          # declined or failed — run normally


def require_admin() -> None:
    """
    Attempt to run as Administrator via UAC.
    If the user declines or elevation fails, continue running without admin rights.
    """
    if is_admin():
        return
    print("[*] Requesting administrator privileges…")
    if elevate():
        sys.exit(0)   # elevated child is running; this parent exits cleanly
    print("[!] Elevation declined or unavailable — continuing without admin rights.\n"
          "    Some protected processes may not be accessible.")


# ── Dependency check ──────────────────────────────────────────────────────────
try:
    from pywinauto import Desktop, Application
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.findwindows import ElementNotFoundError
except ImportError:
    sys.exit(
        "[ERROR] pywinauto is not installed.\n"
        "Install it with:  pip install pywinauto\n"
    )


# ── Optional OCR dependencies (lazy-loaded, EasyOCR) ─────────────────────────

# Module-level cache so the EasyOCR Reader is only initialised once per run
# (first load downloads model weights ~100 MB on first ever use).
_easyocr_reader = None


def _require_ocr_deps() -> None:
    """Check for easyocr and Pillow; print install hint and exit if missing."""
    missing = []
    try:
        import easyocr  # noqa: F401
    except ImportError:
        missing.append("easyocr")
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    if missing:
        sys.exit(
            f"[ERROR] OCR mode requires: {', '.join(missing)}\n"
            f"Install with:  pip install {' '.join(missing)}\n"
        )


def _get_ocr_reader():
    """Return a cached EasyOCR Reader (English). Initialised on first call."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        print("[*] Initialising EasyOCR (first run may download model weights)…")
        _easyocr_reader = easyocr.Reader(["en"], verbose=False)
    return _easyocr_reader


def capture_window(pid: int):
    """
    Screenshot the first window belonging to *pid*.
    Returns (PIL.Image, (left, top)) so callers can map pixel coords back to
    screen coordinates.
    """
    from PIL import ImageGrab
    app  = Application(backend="uia").connect(process=pid)
    wins = app.windows()
    if not wins:
        return None, (0, 0)
    rect = wins[0].rectangle()
    img  = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    return img, (rect.left, rect.top)


def _easyocr_results_to_dicts(raw: list, win_left: int, win_top: int) -> list[dict]:
    """
    Convert EasyOCR output to the same dict format used throughout the script.

    EasyOCR returns: [ ([[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text, confidence), … ]
    The four corners are in clockwise order starting top-left.
    """
    results = []
    for bbox, text, conf in raw:
        text = (text or "").strip()
        if not text:
            continue
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        results.append({
            "text":       text,
            "confidence": round(conf * 100, 1),   # normalise 0-1 → 0-100
            "rect": {
                "left":   win_left + int(min(xs)),
                "top":    win_top  + int(min(ys)),
                "right":  win_left + int(max(xs)),
                "bottom": win_top  + int(max(ys)),
            },
        })
    return results


def ocr_find_text(pid: int, query: str) -> list[dict]:
    """
    Screenshot the window, run EasyOCR, and return all detections whose
    text contains *query* (case-insensitive).

    Each result dict has:
      text       — the matched string
      rect       — absolute screen rectangle {left, top, right, bottom}
      confidence — EasyOCR score scaled to 0-100
    """
    import numpy as np

    img, (win_left, win_top) = capture_window(pid)
    if img is None:
        print(f"[!] Could not capture window for PID {pid}")
        return []

    reader = _get_ocr_reader()
    raw    = reader.readtext(np.array(img))
    all_results = _easyocr_results_to_dicts(raw, win_left, win_top)
    return [r for r in all_results if query.lower() in r["text"].lower()]


def ocr_scan_all(pid: int) -> list[dict]:
    """
    Screenshot the window and return every text region EasyOCR detects,
    with bounding box and confidence score.
    """
    import numpy as np

    img, (win_left, win_top) = capture_window(pid)
    if img is None:
        return []

    reader = _get_ocr_reader()
    raw    = reader.readtext(np.array(img))
    return _easyocr_results_to_dicts(raw, win_left, win_top)


def print_ocr_results(results: list[dict], query: str = "") -> None:
    label = f"matching {query!r}" if query else "found"
    sep = "─" * 70
    print(f"\n{sep}")
    print(f"  OCR — {len(results)} result(s) {label}")
    print(sep)
    for r in results:
        rect   = r["rect"]
        coords = f"({rect['left']},{rect['top']})→({rect['right']},{rect['bottom']})"
        print(f"  [{r['confidence']:>5.1f}%]  {r['text']!r:<30}  {coords}")
    print(f"{sep}\n")



# ── Optional image-search dependencies (lazy-loaded) ─────────────────────────

def _require_image_deps() -> None:
    """Check for pyautogui and opencv-python; print install hint if missing."""
    missing = []
    try:
        import pyautogui  # noqa: F401
    except ImportError:
        missing.append("pyautogui")
    try:
        import cv2  # noqa: F401
    except ImportError:
        missing.append("opencv-python")
    if missing:
        sys.exit(
            f"[ERROR] Image search mode requires: {', '.join(missing)}\n"
            f"Install with:  pip install {' '.join(missing)}\n"
        )


def image_find(template_path: str, confidence: float = 0.9) -> list[dict]:
    """
    Use PyAutoGUI template matching to find all occurrences of a reference
    image on the current screen.

    Args:
        template_path : path to a .png screenshot of the element to find
        confidence    : match threshold 0.0–1.0 (requires opencv-python)

    Returns a list of dicts, each with:
        rect      — absolute screen bounding box (left, top, right, bottom)
        center    — (x, y) pixel at the center of the match
        confidence — the threshold used
    """
    import pyautogui

    if not os.path.isfile(template_path):
        print(f"[!] Template image not found: {template_path!r}")
        return []

    try:
        locations = list(pyautogui.locateAllOnScreen(template_path, confidence=confidence))
    except pyautogui.ImageNotFoundException:
        return []
    except Exception as exc:
        print(f"[!] Image search error: {exc}")
        return []

    results = []
    for box in locations:
        cx, cy = pyautogui.center(box)
        results.append({
            "template":   template_path,
            "confidence": confidence,
            "center":     {"x": cx, "y": cy},
            "rect": {
                "left":   box.left,
                "top":    box.top,
                "right":  box.left + box.width,
                "bottom": box.top  + box.height,
            },
        })
    return results


def print_image_results(results: list[dict], template_path: str) -> None:
    sep = "─" * 70
    print(f"\n{sep}")
    print(f"  Image search — {len(results)} match(es) for {template_path!r}")
    print(sep)
    if not results:
        print("  (no matches found)")
    for i, r in enumerate(results, 1):
        rect   = r["rect"]
        center = r["center"]
        coords = f"({rect['left']},{rect['top']})→({rect['right']},{rect['bottom']})"
        print(f"  [{i}]  center=({center['x']},{center['y']})  rect={coords}")
    print(f"{sep}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────────────────────

def list_all_windows() -> list[dict]:
    """Return a list of all visible top-level windows."""
    desktop = Desktop(backend="uia")
    windows = []
    for win in desktop.windows():
        try:
            info = {
                "title": win.window_text(),
                "class_name": win.class_name(),
                "handle": win.handle,
                "pid": win.process_id(),
                "rect": str(win.rectangle()),
                "is_visible": win.is_visible(),
                "is_enabled": win.is_enabled(),
            }
            windows.append(info)
        except Exception:
            continue
    return windows


def get_element_info(element) -> dict:
    """Extract all available properties from a UI element."""
    info = {}
    extractors = {
        "name":            lambda e: e.window_text(),
        "control_type":    lambda e: e.element_info.control_type,
        "class_name":      lambda e: e.class_name(),
        "automation_id":   lambda e: e.element_info.automation_id,
        "rectangle":       lambda e: str(e.rectangle()),
        "is_visible":      lambda e: e.is_visible(),
        "is_enabled":      lambda e: e.is_enabled(),
        "handle":          lambda e: getattr(e, "handle", None),
        "process_id":      lambda e: e.element_info.process_id,
        "framework_id":    lambda e: e.element_info.framework_id,
    }
    for key, fn in extractors.items():
        try:
            info[key] = fn(element)
        except Exception:
            info[key] = None
    return info


def walk_elements(element, depth: int = 0, max_depth: int = 8) -> list[dict]:
    """Recursively walk all child elements and collect their info."""
    results = []
    if depth > max_depth:
        return results

    info = get_element_info(element)
    info["depth"] = depth
    info["children"] = []
    results.append(info)

    try:
        children = element.children()
    except Exception:
        children = []

    for child in children:
        child_results = walk_elements(child, depth + 1, max_depth)
        if child_results:
            info["children"].append(child_results[0])   # first = parent node
            results.extend(child_results[1:])            # rest  = flat list
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Pretty printers
# ─────────────────────────────────────────────────────────────────────────────

INDENT = "  "

def _elem_line(info: dict) -> str:
    name  = (info.get("name") or "").strip() or "<no name>"
    ctype = info.get("control_type") or "?"
    aid   = info.get("automation_id") or ""
    cls   = info.get("class_name") or ""
    rect  = info.get("rectangle") or ""
    parts = [f"[{ctype}] {name!r}"]
    if aid:
        parts.append(f"  auto_id={aid!r}")
    if cls:
        parts.append(f"  class={cls!r}")
    parts.append(f"  rect={rect}")
    return "  ".join(parts)


def print_tree(node: dict, indent: int = 0) -> None:
    prefix = INDENT * indent
    line   = _elem_line(node)
    vis    = "" if node.get("is_visible") else " [HIDDEN]"
    ena    = "" if node.get("is_enabled") else " [DISABLED]"
    print(f"{prefix}{line}{vis}{ena}")
    for child in node.get("children", []):
        print_tree(child, indent + 1)


def print_windows(windows: list[dict]) -> None:
    print(f"\n{'─'*70}")
    print(f"  Found {len(windows)} open window(s)")
    print(f"{'─'*70}")
    for i, w in enumerate(windows, 1):
        print(f"  [{i:>3}] PID={w['pid']:<6}  handle={w['handle']:<8}  "
              f"title={w['title']!r}")
    print(f"{'─'*70}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Inspection entry-points
# ─────────────────────────────────────────────────────────────────────────────

def inspect_by_pid(pid: int, max_depth: int = 8) -> Optional[dict]:
    try:
        app  = Application(backend="uia").connect(process=pid)
        wins = app.windows()
        if not wins:
            print(f"[!] No windows found for PID {pid}")
            return None
        win  = wins[0]
        print(f"\n[+] Inspecting: {win.window_text()!r}  (PID {pid})\n")
        tree = walk_elements(win, max_depth=max_depth)
        return tree[0] if tree else None
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return None


def inspect_by_title(title: str, max_depth: int = 8) -> Optional[dict]:
    try:
        app  = Application(backend="uia").connect(title_re=f".*{title}.*")
        wins = app.windows()
        if not wins:
            print(f"[!] No windows matching title={title!r}")
            return None
        win  = wins[0]
        print(f"\n[+] Inspecting: {win.window_text()!r}\n")
        tree = walk_elements(win, max_depth=max_depth)
        return tree[0] if tree else None
    except ElementNotFoundError:
        print(f"[!] Window with title containing {title!r} not found.")
        return None
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return None


def interactive_mode(max_depth: int = 8) -> Optional[dict]:
    """Let the user pick a window from the list."""
    windows = list_all_windows()
    if not windows:
        print("[!] No windows found.")
        return None

    print_windows(windows)

    try:
        choice = int(input("  Enter window number to inspect (0 to quit): "))
    except (ValueError, EOFError):
        choice = 0

    if choice <= 0 or choice > len(windows):
        print("Exiting.")
        return None

    w = windows[choice - 1]
    return inspect_by_pid(w["pid"], max_depth=max_depth)


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot / watch helpers
# ─────────────────────────────────────────────────────────────────────────────

def snapshot(root: dict) -> set[str]:
    """Flatten element names into a set for change detection."""
    names = set()
    def _walk(node):
        names.add(node.get("name") or "")
        for child in node.get("children", []):
            _walk(child)
    _walk(root)
    return names


def watch_window(pid: int, interval: float = 1.0, max_depth: int = 4) -> None:
    """Watch a window for GUI changes and print diffs."""
    print(f"[*] Watching PID {pid} every {interval}s  (Ctrl-C to stop)\n")
    previous: Optional[set] = None
    try:
        while True:
            root = inspect_by_pid(pid, max_depth=max_depth)
            if root is None:
                print("[!] Window gone. Stopping.")
                break
            current = snapshot(root)
            if previous is not None:
                added   = current - previous
                removed = previous - current
                if added:
                    print(f"  [+] New elements:     {sorted(added)}")
                if removed:
                    print(f"  [-] Removed elements: {sorted(removed)}")
                if not added and not removed:
                    print("  [=] No change")
            else:
                print(f"  [*] Baseline: {len(current)} element(s)")
            previous = current
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Detect & inspect GUI objects in any app using Pywinauto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--pid",   type=int,   help="Connect by process ID")
    group.add_argument("--title", type=str,   help="Connect by window title (partial match)")
    group.add_argument("--dump",  action="store_true", help="Dump all open windows")
    group.add_argument("--watch", type=int,   metavar="PID",
                       help="Watch a PID for GUI changes")

    p.add_argument("--depth",    type=int, default=8, help="Max recursion depth (default 8)")
    p.add_argument("--export",   type=str, metavar="FILE.json",
                   help="Export element tree to a JSON file")
    p.add_argument("--interval", type=float, default=1.0,
                   help="Polling interval for --watch (default 1.0 s)")

    # OCR options
    p.add_argument("--ocr",  action="store_true",
                   help="After Pywinauto inspection, also run OCR on the window screenshot")
    p.add_argument("--find", type=str, metavar="TEXT",
                   help="OCR-search the window for a specific text string (implies --ocr)")

    # Image / template-matching options (PyAutoGUI)
    p.add_argument("--image", type=str, metavar="FILE.png",
                   help="Search the screen for a reference image using PyAutoGUI template matching")
    p.add_argument("--confidence", type=float, default=0.9,
                   help="Match confidence for --image (0.0-1.0, default 0.9; requires opencv-python)")
    return p


def main() -> None:
    require_admin()   # ← elevate via UAC if not already running as Administrator

    parser = build_parser()
    args   = parser.parse_args()

    # ── Dump all windows ──────────────────────────────────────────────────
    if args.dump:
        windows = list_all_windows()
        print_windows(windows)
        if args.export:
            with open(args.export, "w", encoding="utf-8") as f:
                json.dump(windows, f, indent=2, default=str)
            print(f"[+] Exported to {args.export}")
        return

    # ── Watch mode ────────────────────────────────────────────────────────
    if args.watch:
        watch_window(args.watch, interval=args.interval, max_depth=args.depth)
        return

    # ── Inspect a specific window ─────────────────────────────────────────
    root: Optional[dict] = None

    if args.pid:
        root = inspect_by_pid(args.pid, max_depth=args.depth)
    elif args.title:
        root = inspect_by_title(args.title, max_depth=args.depth)
    else:
        root = interactive_mode(max_depth=args.depth)

    if root is None:
        sys.exit(1)

    # Print tree
    print_tree(root)

    # ── OCR search ────────────────────────────────────────────────────────
    target_pid = args.pid or (
        # recover PID from the inspected root when --title was used
        root.get("process_id")
    )

    if (args.ocr or args.find) and target_pid:
        _require_ocr_deps()
        if args.find:
            print(f"\n[*] OCR search for {args.find!r} in window (PID {target_pid})…")
            ocr_results = ocr_find_text(target_pid, args.find)
            print_ocr_results(ocr_results, query=args.find)
        else:
            print(f"\n[*] OCR full scan of window (PID {target_pid})…")
            ocr_results = ocr_scan_all(target_pid)
            print_ocr_results(ocr_results)
    elif args.ocr or args.find:
        print("[!] Could not determine PID for OCR — skipping.")
        ocr_results = []
    else:
        ocr_results = []

    # ── Image / template search ──────────────────────────────────────────────
    image_results = []
    if args.image:
        _require_image_deps()
        print(f"\n[*] Image search for template {args.image!r}  (confidence={args.confidence})…")
        image_results = image_find(args.image, confidence=args.confidence)
        print_image_results(image_results, args.image)

    # Export
    if args.export:
        export_data = {"element_tree": root}
        if ocr_results:
            export_data["ocr_results"] = ocr_results
        if image_results:
            export_data["image_results"] = image_results
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)
        print(f"\n[+] Exported element tree → {args.export}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
