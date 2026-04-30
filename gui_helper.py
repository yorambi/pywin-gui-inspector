"""
gui_helper.py
=============
Reusable helper module for driving Windows GUI automation from the JSON
exports produced by gui_detector.py.

Typical workflow
----------------
1. Run gui_detector.py to produce a JSON snapshot:
       python gui_detector.py --pid 1234 --ocr --export dump.json

2. Import this module in your automation script:
       from gui_helper import GUISession

3. Use the session to find and interact with elements:
       s = GUISession("dump.json")
       s.click_by_name("Save")
       s.type_into("File name:", "report.txt")
       s.click_ocr("Cancel")

Three search layers (tried in priority order)
---------------------------------------------
  Layer 1 – Pywinauto element tree   (automation_id / name / control_type)
  Layer 2 – OCR results              (visible text on buttons and labels)
  Layer 3 – Image template results   (pixel-matched icon screenshots)

Dependencies
------------
  pip install pywinauto pyautogui
"""

from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

# ── optional runtime deps (only needed for live Pywinauto actions) ────────────
try:
    from pywinauto import Application
    _PYW_AVAILABLE = True
except ImportError:
    _PYW_AVAILABLE = False

try:
    import pyautogui
    _PYAG_AVAILABLE = True
except ImportError:
    _PYAG_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Internal utilities
# ─────────────────────────────────────────────────────────────────────────────

def _parse_rect(rect_str: str) -> tuple[int, int, int, int]:
    """
    Parse a rectangle string from gui_detector output.
    Supports both '(L, T, R, B)' tuples and pywinauto RECT repr.
    Returns (left, top, right, bottom).
    """
    try:
        val = ast.literal_eval(str(rect_str))
        if isinstance(val, (tuple, list)) and len(val) == 4:
            return tuple(int(v) for v in val)
    except Exception:
        pass
    # pywinauto RECT(left=L, top=T, right=R, bottom=B)
    import re
    nums = re.findall(r"-?\d+", str(rect_str))
    if len(nums) >= 4:
        return tuple(int(n) for n in nums[:4])
    raise ValueError(f"Cannot parse rectangle: {rect_str!r}")


def _center(rect) -> tuple[int, int]:
    """Return the center (x, y) of a (left, top, right, bottom) rect."""
    l, t, r, b = rect
    return (l + r) // 2, (t + b) // 2


def _rect_from_dict(d: dict) -> tuple[int, int, int, int]:
    """Extract (left, top, right, bottom) from an OCR/image result dict."""
    r = d["rect"]
    return r["left"], r["top"], r["right"], r["bottom"]


# ─────────────────────────────────────────────────────────────────────────────
# Tree search helpers (work purely on the JSON dict — no live process needed)
# ─────────────────────────────────────────────────────────────────────────────

def find_by_name(
    node: dict,
    name: str,
    *,
    exact: bool = False,
    enabled_only: bool = True,
    visible_only: bool = True,
) -> Optional[dict]:
    """
    Depth-first search the element tree for the first node whose name
    matches *name*.

    Args:
        node         : root dict from element_tree
        name         : text to search for (case-insensitive substring by default)
        exact        : if True, require an exact case-insensitive match
        enabled_only : skip disabled elements
        visible_only : skip hidden elements
    """
    node_name = (node.get("name") or "").strip()
    match = (node_name.lower() == name.lower()) if exact \
            else (name.lower() in node_name.lower())

    if match:
        if enabled_only and not node.get("is_enabled", True):
            pass
        elif visible_only and not node.get("is_visible", True):
            pass
        else:
            return node

    for child in node.get("children", []):
        result = find_by_name(child, name, exact=exact,
                              enabled_only=enabled_only,
                              visible_only=visible_only)
        if result:
            return result
    return None


def find_by_automation_id(node: dict, auto_id: str) -> Optional[dict]:
    """Return the first element whose automation_id matches *auto_id* exactly."""
    if (node.get("automation_id") or "") == auto_id:
        return node
    for child in node.get("children", []):
        result = find_by_automation_id(child, auto_id)
        if result:
            return result
    return None


def find_by_control_type(node: dict, control_type: str) -> Optional[dict]:
    """Return the first element matching *control_type* (e.g. 'Button')."""
    if (node.get("control_type") or "").lower() == control_type.lower():
        return node
    for child in node.get("children", []):
        result = find_by_control_type(child, control_type)
        if result:
            return result
    return None


def find_all(
    node: dict,
    *,
    name: str = "",
    control_type: str = "",
    enabled_only: bool = True,
    visible_only: bool = True,
) -> list[dict]:
    """
    Collect every element in the tree that matches ALL supplied filters.
    Omit a filter to skip it.

    Examples:
        find_all(tree, control_type="Button")
        find_all(tree, control_type="Edit", enabled_only=True)
        find_all(tree, name="OK")
    """
    results: list[dict] = []

    def _walk(n: dict) -> None:
        ok = True
        if name and name.lower() not in (n.get("name") or "").lower():
            ok = False
        if control_type and (n.get("control_type") or "").lower() != control_type.lower():
            ok = False
        if enabled_only and not n.get("is_enabled", True):
            ok = False
        if visible_only and not n.get("is_visible", True):
            ok = False
        if ok:
            results.append(n)
        for child in n.get("children", []):
            _walk(child)

    _walk(node)
    return results


def element_rect(node: dict) -> tuple[int, int, int, int]:
    """Return the (left, top, right, bottom) screen rect of an element node."""
    return _parse_rect(node["rectangle"])


def element_center(node: dict) -> tuple[int, int]:
    """Return the screen center (x, y) of an element node."""
    return _center(element_rect(node))


# ─────────────────────────────────────────────────────────────────────────────
# OCR helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_ocr(results: list[dict], query: str, *, exact: bool = False) -> Optional[dict]:
    """
    Search OCR result list for the first entry containing *query*.

    Args:
        results : list from export["ocr_results"]
        query   : text to search for (case-insensitive)
        exact   : require an exact match instead of substring
    """
    for r in results:
        text = (r.get("text") or "").strip()
        match = text.lower() == query.lower() if exact else query.lower() in text.lower()
        if match:
            return r
    return None


def find_all_ocr(results: list[dict], query: str) -> list[dict]:
    """Return all OCR results containing *query*."""
    return [r for r in results if query.lower() in (r.get("text") or "").lower()]


def ocr_center(ocr_result: dict) -> tuple[int, int]:
    """Return the screen center (x, y) of an OCR result dict."""
    return _center(_rect_from_dict(ocr_result))


# ─────────────────────────────────────────────────────────────────────────────
# Image / template helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_image_result(image_results: list[dict], template: str = "") -> Optional[dict]:
    """
    Return the first image result, optionally filtered by template filename.
    """
    for r in image_results:
        if not template or Path(r.get("template", "")).name == Path(template).name:
            return r
    return None


def image_center(image_result: dict) -> tuple[int, int]:
    """Return the pre-computed center (x, y) from an image result dict."""
    c = image_result["center"]
    return c["x"], c["y"]


# ─────────────────────────────────────────────────────────────────────────────
# GUISession — the main high-level interface
# ─────────────────────────────────────────────────────────────────────────────

class GUISession:
    """
    High-level automation session loaded from a gui_detector JSON export.

    Priority order for all find/click operations:
      1. Pywinauto element tree  (automation_id → name → control_type)
      2. OCR results             (visible text)
      3. Image template results  (pixel match)

    Parameters
    ----------
    export_path : str | Path
        Path to the JSON file produced by gui_detector.py --export.
    click_delay : float
        Seconds to pause after every click (default 0.3).
    move_duration : float
        Mouse move duration in seconds passed to PyAutoGUI (default 0.1).

    Examples
    --------
    >>> s = GUISession("dump.json")
    >>> s.click_by_name("Save")
    >>> s.click_by_auto_id("btn_ok")
    >>> s.click_ocr("Cancel")
    >>> s.type_into("File name:", "report.txt")
    >>> buttons = s.all_buttons()
    """

    def __init__(
        self,
        export_path: str | Path,
        *,
        click_delay: float = 0.3,
        move_duration: float = 0.1,
    ) -> None:
        self.path          = Path(export_path)
        self.click_delay   = click_delay
        self.move_duration = move_duration

        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)

        # Support both bare element trees and wrapped exports
        if "element_tree" in data:
            self.tree          = data["element_tree"]
            self.ocr_results   = data.get("ocr_results", [])
            self.image_results = data.get("image_results", [])
        else:
            # Bare tree (exported without OCR/image)
            self.tree          = data
            self.ocr_results   = []
            self.image_results = []

        self._pid = self.tree.get("process_id")

    # ── Live Pywinauto handle ─────────────────────────────────────────────────

    def _live_win(self):
        """Connect to the live window via Pywinauto (requires process still running)."""
        if not _PYW_AVAILABLE:
            raise RuntimeError("pywinauto is not installed.")
        if not self._pid:
            raise RuntimeError("No process_id in export — cannot connect live.")
        app  = Application(backend="uia").connect(process=self._pid)
        wins = app.windows()
        if not wins:
            raise RuntimeError(f"No windows found for PID {self._pid}.")
        return wins[0]

    # ── Internal click helper ─────────────────────────────────────────────────

    def _click(self, x: int, y: int) -> None:
        if not _PYAG_AVAILABLE:
            raise RuntimeError("pyautogui is not installed — cannot click.")
        pyautogui.moveTo(x, y, duration=self.move_duration)
        pyautogui.click()
        time.sleep(self.click_delay)

    # ── Tree-based actions ────────────────────────────────────────────────────

    def find(self, name: str, *, exact: bool = False) -> Optional[dict]:
        """Find an element by name in the tree. Returns the node dict or None."""
        return find_by_name(self.tree, name, exact=exact)

    def find_auto_id(self, auto_id: str) -> Optional[dict]:
        """Find an element by automation_id."""
        return find_by_automation_id(self.tree, auto_id)

    def click_by_name(self, name: str, *, live: bool = False) -> bool:
        """
        Click the first element whose name contains *name*.

        Args:
            name : element name to search for (case-insensitive substring)
            live : if True, use Pywinauto click_input() instead of pixel click
                   (more reliable for keyboard-focus-sensitive controls)

        Returns True on success, False if element not found.
        """
        node = find_by_name(self.tree, name)
        if node is None:
            print(f"[gui_helper] Element not found by name: {name!r}")
            return False
        if live:
            win = self._live_win()
            win.child_window(title=node["name"],
                             control_type=node.get("control_type")).click_input()
        else:
            x, y = element_center(node)
            self._click(x, y)
        return True

    def click_by_auto_id(self, auto_id: str, *, live: bool = False) -> bool:
        """
        Click the element with the given automation_id.

        Args:
            auto_id : exact automation_id string
            live    : use Pywinauto click_input() if True
        """
        node = find_by_automation_id(self.tree, auto_id)
        if node is None:
            print(f"[gui_helper] Element not found by auto_id: {auto_id!r}")
            return False
        if live:
            win = self._live_win()
            win.child_window(auto_id=auto_id).click_input()
        else:
            x, y = element_center(node)
            self._click(x, y)
        return True

    def type_into(self, name: str, text: str, *, clear_first: bool = True) -> bool:
        """
        Click the Edit control matching *name* and type *text* into it.

        Args:
            name        : element name (e.g. 'File name:')
            text        : string to type
            clear_first : select-all + delete before typing (default True)
        """
        if not _PYAG_AVAILABLE:
            raise RuntimeError("pyautogui is not installed.")
        node = find_by_name(self.tree, name)
        # If not found by name, fall back to the nearest Edit after that label
        if node is None or node.get("control_type") != "Edit":
            node = find_by_control_type(self.tree, "Edit")
        if node is None:
            print(f"[gui_helper] Edit control not found for: {name!r}")
            return False
        x, y = element_center(node)
        self._click(x, y)
        if clear_first:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
        pyautogui.typewrite(text, interval=0.05)
        return True

    def all_buttons(self) -> list[dict]:
        """Return all enabled, visible Button elements from the tree."""
        return find_all(self.tree, control_type="Button")

    def all_edits(self) -> list[dict]:
        """Return all enabled, visible Edit (text input) elements."""
        return find_all(self.tree, control_type="Edit")

    def all_checkboxes(self) -> list[dict]:
        """Return all CheckBox elements."""
        return find_all(self.tree, control_type="CheckBox")

    def all_of_type(self, control_type: str) -> list[dict]:
        """Return all elements of a given control type."""
        return find_all(self.tree, control_type=control_type)

    # ── OCR-based actions ─────────────────────────────────────────────────────

    def click_ocr(self, query: str, *, exact: bool = False) -> bool:
        """
        Click the screen position of the first OCR result matching *query*.

        Useful for buttons/labels that Pywinauto can't identify by automation ID.

        Args:
            query : text to search for (case-insensitive substring)
            exact : require an exact match
        """
        result = find_ocr(self.ocr_results, query, exact=exact)
        if result is None:
            print(f"[gui_helper] OCR result not found for: {query!r}")
            return False
        x, y = ocr_center(result)
        self._click(x, y)
        return True

    def ocr_text_at(self, query: str) -> Optional[str]:
        """Return the exact OCR text of the first result matching *query*."""
        result = find_ocr(self.ocr_results, query)
        return result["text"] if result else None

    def all_ocr_text(self) -> list[str]:
        """Return a flat list of all OCR-detected strings in the window."""
        return [r["text"] for r in self.ocr_results]

    # ── Image-based actions ───────────────────────────────────────────────────

    def click_image(self, template: str = "") -> bool:
        """
        Click the center of the first image template match.

        Args:
            template : optional filename filter (e.g. 'save_icon.png')
        """
        result = find_image_result(self.image_results, template)
        if result is None:
            print(f"[gui_helper] Image result not found for template: {template!r}")
            return False
        x, y = image_center(result)
        self._click(x, y)
        return True

    # ── Smart click — tries all three layers in priority order ────────────────

    def smart_click(self, query: str) -> bool:
        """
        Try to click *query* using all three layers in order:
          1. Element tree (name match)
          2. OCR results  (text match)
          3. Image results (template filename match)

        Returns True as soon as one layer succeeds.
        """
        if find_by_name(self.tree, query) is not None:
            print(f"[gui_helper] smart_click: found {query!r} in element tree")
            return self.click_by_name(query)

        if find_ocr(self.ocr_results, query) is not None:
            print(f"[gui_helper] smart_click: found {query!r} in OCR results")
            return self.click_ocr(query)

        if find_image_result(self.image_results, query) is not None:
            print(f"[gui_helper] smart_click: found {query!r} in image results")
            return self.click_image(query)

        print(f"[gui_helper] smart_click: {query!r} not found in any layer")
        return False

    # ── Convenience / introspection ───────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of what this session contains."""
        return {
            "export":        str(self.path),
            "process_id":    self._pid,
            "window_name":   self.tree.get("name"),
            "total_elements": _count_nodes(self.tree),
            "ocr_results":   len(self.ocr_results),
            "image_results": len(self.image_results),
            "buttons":       len(self.all_buttons()),
            "edits":         len(self.all_edits()),
        }

    def print_summary(self) -> None:
        """Print a human-readable summary of the session."""
        s = self.summary()
        print(f"\n{'─'*60}")
        print(f"  GUISession: {s['window_name']!r}  (PID {s['process_id']})")
        print(f"{'─'*60}")
        print(f"  Export file    : {s['export']}")
        print(f"  Total elements : {s['total_elements']}")
        print(f"  Buttons        : {s['buttons']}")
        print(f"  Edit fields    : {s['edits']}")
        print(f"  OCR results    : {s['ocr_results']}")
        print(f"  Image matches  : {s['image_results']}")
        print(f"{'─'*60}\n")

    def __repr__(self) -> str:
        return (f"GUISession(window={self.tree.get('name')!r}, "
                f"pid={self._pid}, "
                f"elements={_count_nodes(self.tree)}, "
                f"ocr={len(self.ocr_results)}, "
                f"images={len(self.image_results)})")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions (no session object required)
# ─────────────────────────────────────────────────────────────────────────────

def load_export(path: str | Path) -> dict:
    """Load a gui_detector JSON export and return the raw dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten_tree(node: dict) -> list[dict]:
    """
    Return a flat list of every element in the tree (depth-first).
    Useful for bulk processing or filtering with list comprehensions.
    """
    results = [node]
    for child in node.get("children", []):
        results.extend(flatten_tree(child))
    return results


def _count_nodes(node: dict) -> int:
    return 1 + sum(_count_nodes(c) for c in node.get("children", []))


def print_flat(node: dict, *, enabled_only: bool = False) -> None:
    """Print a flat, readable list of all elements with name + type + rect."""
    for el in flatten_tree(node):
        if enabled_only and not el.get("is_enabled"):
            continue
        name  = (el.get("name") or "").strip() or "<no name>"
        ctype = el.get("control_type") or "?"
        rect  = el.get("rectangle") or ""
        aid   = el.get("automation_id") or ""
        aid_s = f"  [{aid}]" if aid else ""
        print(f"  [{ctype}] {name!r}{aid_s}  {rect}")


# ─────────────────────────────────────────────────────────────────────────────
# ScriptWriter — generate automation scripts from plain-English instructions
# ─────────────────────────────────────────────────────────────────────────────

class ScriptWriter:
    """
    Generates ready-to-run Python automation scripts from plain-English steps.

    Resolution priority for 'click' steps:
      1. automation_id  → s.click_by_auto_id(...)   most reliable
      2. element name   → s.click_by_name(...)
      3. OCR text       → s.click_ocr(...)
      4. image template → s.click_image(...)
      5. unresolved     → s.smart_click(...)  + warning comment

    Supported instruction syntax (comma- or newline-separated):
      click <target>
      type <text> into <field>
      press <key>
      hotkey <key1+key2+...>
      wait <n> second(s)
      screenshot as <filename>
      open [the] <menu> [menu]
      close
    """

    def __init__(self, export_path: str | Path) -> None:
        self.path = Path(export_path)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        if "element_tree" in data:
            self.tree          = data["element_tree"]
            self.ocr_results   = data.get("ocr_results", [])
            self.image_results = data.get("image_results", [])
        else:
            self.tree          = data
            self.ocr_results   = []
            self.image_results = []

    # ── Resolution ────────────────────────────────────────────────────────────

    def _resolve_click(self, target: str) -> str:
        """Return the best GUISession call string to click *target*."""
        node = find_by_name(self.tree, target)
        if node:
            aid = node.get("automation_id")
            if aid:
                return f"s.click_by_auto_id({aid!r})"
            return f"s.click_by_name({target!r})"

        if find_ocr(self.ocr_results, target) is not None:
            return f"s.click_ocr({target!r})"

        if find_image_result(self.image_results, target) is not None:
            return f"s.click_image({target!r})"

        return f"s.smart_click({target!r})  # WARNING: '{target}' not found in export"

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse_steps(self, instructions: str) -> list[str]:
        """Split instructions into individual step strings."""
        if "\n" in instructions:
            steps = instructions.strip().splitlines()
        else:
            steps = instructions.split(",")
        return [s.strip().rstrip(".") for s in steps if s.strip()]

    def _step_to_code(self, step: str) -> str:
        """Translate one plain-English step into a Python code line."""
        # wait N second(s)
        m = re.match(r"wait\s+(\d+(?:\.\d+)?)\s+seconds?", step, re.IGNORECASE)
        if m:
            return f"time.sleep({m.group(1)})"

        # hotkey <key1+key2> — must come before 'press' to avoid false match
        m = re.match(r"hotkey\s+(\S+)", step, re.IGNORECASE)
        if m:
            keys = m.group(1).lower().split("+")
            return f"pyautogui.hotkey({', '.join(repr(k) for k in keys)})"

        # press <key>
        m = re.match(r"press\s+(\S+)", step, re.IGNORECASE)
        if m:
            return f"pyautogui.press({m.group(1).lower()!r})"

        # screenshot as <filename>
        m = re.match(r"screenshot\s+as\s+(\S+)", step, re.IGNORECASE)
        if m:
            return f"pyautogui.screenshot({m.group(1)!r})"

        # type <text> into <field>
        m = re.match(r"type\s+(.+?)\s+into\s+(.+)", step, re.IGNORECASE)
        if m:
            text  = m.group(1).strip()
            field = m.group(2).strip()
            return f"s.type_into({field!r}, {text!r})"

        # click <target>
        m = re.match(r"click\s+(.+)", step, re.IGNORECASE)
        if m:
            return self._resolve_click(m.group(1).strip())

        # open [the] <X> [menu]
        m = re.match(r"open\s+(?:the\s+)?(.+?)(?:\s+menu)?$", step, re.IGNORECASE)
        if m:
            return self._resolve_click(m.group(1).strip())

        # close
        if step.lower() == "close":
            return "pyautogui.hotkey('alt', 'f4')"

        return f"# TODO: {step!r}"

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, instructions: str) -> str:
        """Return a complete, ready-to-run Python script as a string."""
        steps = self._parse_steps(instructions)
        lines = [
            "import time",
            "import sys",
            "from pathlib import Path",
            "",
            "import pyautogui",
            "",
            "sys.path.insert(0, str(Path(__file__).parent.parent))",
            "from gui_helper import GUISession",
            "",
            f"s = GUISession({str(self.path)!r}, click_delay=0.4, move_duration=0.15)",
            "",
        ]
        for step in steps:
            lines.append(self._step_to_code(step))
        lines.append("")
        return "\n".join(lines)

    def preview(self, instructions: str) -> None:
        """Print the generated script to stdout."""
        print(self.generate(instructions))

    def write(self, instructions: str, output: str | Path = "generated_script.py") -> Path:
        """Write the generated script to *output* and return its path."""
        out = Path(output)
        out.write_text(self.generate(instructions), encoding="utf-8")
        print(f"[ScriptWriter] Written → {out}")
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Quick demo — run this file directly to test against a dump
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gui_helper.py <export.json>")
        sys.exit(1)

    session = GUISession(sys.argv[1])
    session.print_summary()

    print("All buttons found in tree:")
    for btn in session.all_buttons():
        x, y = element_center(btn)
        print(f"  {btn['name']!r:30}  center=({x},{y})")

    if session.ocr_results:
        print("\nAll OCR text detected:")
        for t in session.all_ocr_text():
            print(f"  {t!r}")
