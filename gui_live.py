"""
gui_live.py
===========
Live-mode GUI automation — queries the running UIA tree directly without a
JSON snapshot.  Complements gui_helper.py with new capabilities borrowed from
pywinauto_recorder.

New vs gui_helper.py
--------------------
  Path syntax       "Name||ControlType->Child||Type"  (hierarchy-aware)
  Wildcards/regex   * matches any node; "RegEx: pattern||Type"
  Grid addressing   #[row,col] suffix on paths
  UIPath context    with s.path("App||Window"): s.click("OK||Button")
  TTL element cache avoids re-querying UIA on every call
  wait_is_ready     polls enabled + visible + cursor before clicking
  OCRWrapper        EasyOCR results usable as drop-in UIA elements
  set_text          triple-click + Ctrl+A for reliable text entry
  set_combobox      handles dropdown animation delay automatically
  menu_click        "File->Save As->PDF" multi-level navigation
  App lifecycle     start, connect, focus, close

Path syntax quick-reference
----------------------------
  "OK||Button"                  name contains "OK", type is Button
  "||Edit"                      any Edit control
  "Toolbar||ToolBar->Save||Button"   Save button inside Toolbar
  "*->||Button"                 wildcard intermediate, then any Button
  "RegEx: .*Save.*||Button"     regex name match
  "||Button#[1,2]"              row 1, col 2 of matched Buttons
  "||Slider%(0.8,0)"            click 80% right of slider center

Requirements
------------
  pip install pywinauto pyautogui
  pip install easyocr Pillow          # OCR features only
"""

from __future__ import annotations

import re
import subprocess
import time
import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from pywinauto import Application, Desktop
    import pyautogui
except ImportError as _e:
    raise ImportError("pip install pywinauto pyautogui") from _e


# ─────────────────────────────────────────────────────────────────────────────
# Path parsing
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _Entry:
    name:     str
    ctrl:     str           # control_type; '' = any
    regex:    bool = False
    wildcard: bool = False  # True when the node token is bare '*'


def _parse(path_str: str) -> tuple[list[_Entry], tuple | None, tuple | None]:
    """
    Decompose a path string into (entries, grid_index, click_offset).

    Strips trailing %(dx,dy) and #[row,col] before splitting on '->'.
    """
    offset = None
    m = re.search(r'%\(\s*([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)\s*\)\s*$', path_str)
    if m:
        offset = (float(m.group(1)), float(m.group(2)))
        path_str = path_str[:m.start()].rstrip()

    grid = None
    m = re.search(r'#\[\s*(\d+)\s*,\s*(\d+)\s*\]\s*$', path_str)
    if m:
        grid = (int(m.group(1)), int(m.group(2)))
        path_str = path_str[:m.start()].rstrip()

    entries: list[_Entry] = []
    for node in path_str.split("->"):
        node = node.strip()
        if node == "*":
            entries.append(_Entry("", "", wildcard=True))
            continue
        name_part, _, ctrl_part = node.partition("||")
        name_part = name_part.strip()
        ctrl_part = ctrl_part.strip()
        is_regex  = name_part.lower().startswith("regex:")
        if is_regex:
            name_part = name_part[6:].strip()
        entries.append(_Entry(name=name_part, ctrl=ctrl_part, regex=is_regex))

    return entries, grid, offset


def _match(element, entry: _Entry) -> bool:
    """Return True if *element* satisfies *entry*'s name and control-type filter."""
    if entry.wildcard:
        return True
    if entry.name:
        text = (element.window_text() or "").strip()
        if entry.regex:
            if not re.search(entry.name, text):
                return False
        elif entry.name.lower() not in text.lower():
            return False
    if entry.ctrl:
        try:
            ct = element.element_info.control_type or ""
            if ct.lower() != entry.ctrl.lower():
                return False
        except Exception:
            pass
    return True


def _subtree_find(root, entry: _Entry, max_depth: int = 12) -> list:
    """Find all descendants of *root* (inclusive) matching *entry*."""
    results = []

    def _walk(node, depth):
        if depth > max_depth:
            return
        if _match(node, entry):
            results.append(node)
        try:
            for child in node.children():
                _walk(child, depth + 1)
        except Exception:
            pass

    _walk(root, 0)
    return results


def _path_find(root, entries: list[_Entry]) -> list:
    """
    For each entry in sequence, search the subtree of every match from the
    previous entry.  Returns elements that satisfy the full entry sequence.
    """
    if not entries:
        return [root]
    candidates = [root]
    for entry in entries:
        next_candidates = []
        for node in candidates:
            next_candidates.extend(_subtree_find(node, entry))
        candidates = next_candidates
    return candidates


def _desktop_find(entries: list[_Entry]) -> list:
    """
    Search starting from all Desktop top-level windows.

    Used when the path begins with a Window/Dialog entry — the path was
    recorded from the Desktop level so we must resolve the window first
    rather than searching *within* the already-connected window.
    """
    desktop      = Desktop(backend="uia")
    first, *rest = entries
    win_matches  = [w for w in desktop.windows() if _match(w, first)]
    if not rest:
        return win_matches
    results = []
    for win in win_matches:
        results.extend(_path_find(win, rest))
    return results


_WINDOW_CTRL_TYPES = {"window", "dialog", "popup"}


# ─────────────────────────────────────────────────────────────────────────────
# TTL element cache
# ─────────────────────────────────────────────────────────────────────────────

class _TTLCache:
    def __init__(self, ttl: float = 2.0) -> None:
        self._store: dict = {}
        self.ttl = ttl

    def get(self, key):
        if key in self._store:
            val, ts = self._store[key]
            if time.time() - ts < self.ttl:
                return val, True
        return None, False

    def set(self, key, val) -> None:
        self._store[key] = (val, time.time())

    def clear(self) -> None:
        self._store.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Readiness check
# ─────────────────────────────────────────────────────────────────────────────

_IDC_WAIT        = 32514
_IDC_APPSTARTING = 32650


def _cursor_busy() -> bool:
    """True when the system cursor is the hourglass or app-starting spinner."""
    try:
        class _CURSORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize",      ctypes.wintypes.DWORD),
                ("flags",       ctypes.wintypes.DWORD),
                ("hCursor",     ctypes.wintypes.HANDLE),
                ("ptScreenPos", ctypes.wintypes.POINT),
            ]
        ci = _CURSORINFO()
        ci.cbSize = ctypes.sizeof(_CURSORINFO)
        ctypes.windll.user32.GetCursorInfo(ctypes.byref(ci))
        u32 = ctypes.windll.user32
        return ci.hCursor in (
            u32.LoadCursorW(None, _IDC_WAIT),
            u32.LoadCursorW(None, _IDC_APPSTARTING),
        )
    except Exception:
        return False


def wait_is_ready(element, timeout: float = 8.0, poll: float = 0.1) -> bool:
    """
    Wait until *element* is enabled, visible, and the cursor is not the
    hourglass.  Returns True when ready, False on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if element.is_enabled() and element.is_visible() and not _cursor_busy():
                return True
        except Exception:
            pass
        time.sleep(poll)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Grid layout helper
# ─────────────────────────────────────────────────────────────────────────────

def get_sorted_region(
    elements: list,
    min_width:  int = 0,
    min_height: int = 0,
    line_tolerance: int | None = None,
) -> tuple[int, int, list[list]]:
    """
    Sort *elements* by screen position and arrange into a 2-D grid.

    Returns ``(nrows, ncols, grid)`` where ``grid[r][c]`` is the element at
    row *r*, column *c*, or ``None`` when a cell is empty.

    Use with the ``#[row,col]`` path suffix::

        _, _, grid = get_sorted_region(buttons)
        second_row_first_col = grid[1][0]
    """
    rects = []
    for el in elements:
        try:
            r = el.rectangle()
            w, h = r.right - r.left, r.bottom - r.top
            if w >= min_width and h >= min_height:
                rects.append((r.top, r.left, r.bottom, r.right, el))
        except Exception:
            pass

    if not rects:
        return 0, 0, []

    if line_tolerance is None:
        heights = sorted(e[2] - e[0] for e in rects)
        line_tolerance = max(1, heights[len(heights) // 2] // 2)

    rects.sort()                    # sort by (top, left, …)

    rows: list[list] = []
    for top, left, bot, right, el in rects:
        placed = False
        for row in rows:
            if abs(top - row[0][0]) <= line_tolerance:
                row.append((top, left, bot, right, el))
                placed = True
                break
        if not placed:
            rows.append([(top, left, bot, right, el)])

    for row in rows:
        row.sort(key=lambda x: x[1])     # left → right within each row

    ncols = max(len(r) for r in rows)
    grid  = [
        [row[c][-1] if c < len(row) else None for c in range(ncols)]
        for row in rows
    ]
    return len(rows), ncols, grid


# ─────────────────────────────────────────────────────────────────────────────
# OCRWrapper — duck-typed UIA element backed by EasyOCR
# ─────────────────────────────────────────────────────────────────────────────

class OCRWrapper:
    """
    Wraps an EasyOCR detection so it can be used anywhere a pywinauto UIA
    element is expected.

    Exposes ``.window_text()``, ``.rectangle()``, ``.is_enabled()``,
    ``.is_visible()``, ``.click_input()``, and ``.click()``.
    """

    def __init__(self, text: str, rect: tuple[int, int, int, int], confidence: float) -> None:
        self._text = text
        self._rect = rect          # (left, top, right, bottom) in screen pixels
        self.confidence = confidence

    def window_text(self)  -> str:  return self._text
    def is_enabled(self)   -> bool: return True
    def is_visible(self)   -> bool: return True

    def rectangle(self):
        from pywinauto.win32structures import RECT
        return RECT(*self._rect)

    def center(self) -> tuple[int, int]:
        l, t, r, b = self._rect
        return (l + r) // 2, (t + b) // 2

    def click_input(self) -> None:
        x, y = self.center()
        pyautogui.moveTo(x, y, duration=0.08)
        pyautogui.click()

    click = click_input

    def __repr__(self) -> str:
        return f"OCRWrapper({self._text!r}, conf={self.confidence:.1f}%, rect={self._rect})"


def _ocr_scan(element, query: str = "", lang: list[str] | None = None) -> list[OCRWrapper]:
    """Screenshot *element*'s bounding rect and return OCR detections as OCRWrapper objects."""
    try:
        import easyocr
        import numpy as np
        from PIL import ImageGrab
    except ImportError as exc:
        raise ImportError("pip install easyocr Pillow") from exc

    r   = element.rectangle()
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    raw = easyocr.Reader(lang or ["en"], verbose=False).readtext(np.array(img))

    results = []
    for bbox, text, conf in raw:
        text = (text or "").strip()
        if not text or (query and query.lower() not in text.lower()):
            continue
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        screen_rect = (
            r.left + int(min(xs)), r.top + int(min(ys)),
            r.left + int(max(xs)), r.top + int(max(ys)),
        )
        results.append(OCRWrapper(text, screen_rect, round(conf * 100, 1)))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# UIPath — composable path context manager
# ─────────────────────────────────────────────────────────────────────────────

class UIPath:
    """
    Prepends a root path onto every ``LiveSession`` call inside the block.
    Nesting is supported.

    Usage::

        with s.path("My App||Window"):
            s.click("File||MenuItem")       # resolved as "My App||Window->File||MenuItem"

        with s.path("My App||Window"):
            with s.path("Toolbar||ToolBar"):
                s.click("Save||Button")     # "My App||Window->Toolbar||ToolBar->Save||Button"
    """

    def __init__(self, session: "LiveSession", prefix: str) -> None:
        self._session = session
        self._prefix  = prefix

    def __enter__(self) -> "LiveSession":
        self._session._path_stack.append(self._prefix)
        return self._session

    def __exit__(self, *_) -> None:
        if self._session._path_stack:
            self._session._path_stack.pop()


# ─────────────────────────────────────────────────────────────────────────────
# Application lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────────

def start_application(executable: str, *args: str, timeout: float = 15.0) -> "LiveSession":
    """
    Launch *executable*, wait for its window to appear, and return a
    connected ``LiveSession``.

    Uses a before/after window-handle diff to identify the new window
    reliably even when other windows are already open.
    """
    desktop = Desktop(backend="uia")
    before  = {w.handle for w in desktop.windows()}
    subprocess.Popen([executable, *args])

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.25)
        new = {w.handle for w in desktop.windows()} - before
        if new:
            app = Application(backend="uia").connect(handle=next(iter(new)))
            return LiveSession(app)

    raise TimeoutError(f"No window appeared within {timeout}s after launching {executable!r}")


def connect_application(
    pid:      int | None = None,
    title:    str | None = None,
    title_re: str | None = None,
) -> "LiveSession":
    """Connect to an already-running app and return a ``LiveSession``."""
    if pid:
        app = Application(backend="uia").connect(process=pid)
    elif title_re:
        app = Application(backend="uia").connect(title_re=title_re)
    elif title:
        app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
    else:
        raise ValueError("Provide pid, title, or title_re.")
    return LiveSession(app)


# ─────────────────────────────────────────────────────────────────────────────
# LiveSession
# ─────────────────────────────────────────────────────────────────────────────

class LiveSession:
    """
    Live GUI automation session — no JSON snapshot needed.

    Instantiate via the module helpers::

        s = connect_application(title="Notepad")
        s = start_application("notepad.exe")

    Or wrap an existing ``pywinauto.Application``::

        from pywinauto import Application
        s = LiveSession(Application(backend="uia").connect(process=1234))

    Examples::

        s.click("File||MenuItem")
        s.menu_click("File->Save As")
        s.set_text("File name:||Edit", "report.txt")
        s.click("Save||Button")

        with s.path("Untitled - Notepad||Window"):
            s.click("File||MenuItem")

        s.smart_click("Submit")     # UIA tree → OCR fallback
    """

    def __init__(self, app: Application, click_delay: float = 0.0) -> None:
        self._app         = app
        self._click_delay = click_delay
        self._path_stack: list[str] = []
        self._cache       = _TTLCache(ttl=2.0)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _full(self, path: str) -> str:
        if self._path_stack:
            return "->".join(self._path_stack) + "->" + path
        return path

    def _win(self):
        wins = self._app.windows()
        if not wins:
            raise RuntimeError("No windows found for this application.")
        return wins[0]

    def _search(self, path: str, timeout: float = 5.0) -> list:
        """Find elements matching *path*, with TTL cache + timeout retry."""
        full = self._full(path)
        cached, hit = self._cache.get(full)
        if hit:
            return cached

        entries, grid, _offset = _parse(full)
        if not entries:
            return []

        # Paths that start at window/dialog level must be resolved from the
        # Desktop — they were recorded relative to the whole screen, not from
        # within a single already-connected window.
        starts_at_desktop = bool(entries[0].ctrl.lower() in _WINDOW_CTRL_TYPES
                                 or (not entries[0].ctrl and entries[0].name))

        deadline = time.time() + timeout
        while time.time() <= deadline:
            results = (_desktop_find(entries) if starts_at_desktop
                       else _path_find(self._win(), entries))
            if results:
                if grid is not None:
                    _, _, g = get_sorted_region(results)
                    row, col = grid
                    results = [g[row][col]] if (
                        row < len(g) and col < len(g[row]) and g[row][col]
                    ) else []
                self._cache.set(full, results)
                return results
            time.sleep(0.2)

        return []

    def _do_click(self, element, offset: tuple | None = None) -> None:
        wait_is_ready(element)
        try:
            r  = element.rectangle()
            hw = (r.right  - r.left) / 2
            hh = (r.bottom - r.top)  / 2
            if offset:
                dx, dy = offset
                cx = int(r.left + hw + dx * hw)
                cy = int(r.top  + hh + dy * hh)
            else:
                cx, cy = int(r.left + hw), int(r.top + hh)
            pyautogui.moveTo(cx, cy, duration=0.1)
            pyautogui.click()
        except Exception:
            element.click_input()
        if self._click_delay:
            time.sleep(self._click_delay)

    # ── Finding ───────────────────────────────────────────────────────────────

    def find(self, path: str, timeout: float = 5.0):
        """Return the first element matching *path*, or ``None``."""
        results = self._search(path, timeout)
        return results[0] if results else None

    def find_all(self, path: str, timeout: float = 5.0) -> list:
        """Return all elements matching *path*."""
        return self._search(path, timeout)

    # ── Clicking ──────────────────────────────────────────────────────────────

    def click(self, path: str, timeout: float = 5.0) -> bool:
        """Click the first element matching *path*. Returns True on success."""
        full = self._full(path)
        _, _, offset = _parse(full)
        results = self._search(path, timeout)
        if not results:
            print(f"[LiveSession] click: not found — {path!r}")
            return False
        self._do_click(results[0], offset)
        self._cache.clear()
        return True

    def double_click(self, path: str, timeout: float = 5.0) -> bool:
        """Double-click the first element matching *path*."""
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] double_click: not found — {path!r}")
            return False
        wait_is_ready(el)
        try:
            el.double_click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.doubleClick((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        self._cache.clear()
        return True

    def right_click(self, path: str, timeout: float = 5.0) -> bool:
        """Right-click the first element matching *path*."""
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] right_click: not found — {path!r}")
            return False
        wait_is_ready(el)
        try:
            el.right_click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.rightClick((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        self._cache.clear()
        return True

    # ── Text input ────────────────────────────────────────────────────────────

    def set_text(self, path: str, text: str, timeout: float = 5.0) -> bool:
        """
        Click an Edit field and reliably replace its content with *text*.

        Uses triple-click + Ctrl+A before typing so all existing text is
        always selected first — more robust than a single Ctrl+A.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] set_text: not found — {path!r}")
            return False
        wait_is_ready(el)
        try:
            el.click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        time.sleep(0.1)
        pyautogui.click(clicks=3, interval=0.06)    # triple-click → select all
        pyautogui.hotkey("ctrl", "a")               # belt-and-suspenders
        pyautogui.typewrite(text, interval=0.04)
        self._cache.clear()
        return True

    def set_combobox(self, path: str, text: str, timeout: float = 5.0) -> bool:
        """
        Open a ComboBox and select *text* from it (or type and confirm).

        Waits 0.9 s after clicking to let the dropdown animation complete
        before sending keystrokes.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] set_combobox: not found — {path!r}")
            return False
        wait_is_ready(el)
        self._do_click(el)
        time.sleep(0.9)                             # dropdown animation
        pyautogui.typewrite(text, interval=0.05)
        pyautogui.press("enter")
        self._cache.clear()
        return True

    # ── Menu navigation ───────────────────────────────────────────────────────

    def menu_click(self, menu_path: str, delay: float = 0.35, timeout: float = 5.0) -> bool:
        """
        Navigate and click a multi-level menu.

        Args:
            menu_path : ``"->"``-separated item labels, e.g. ``"File->Save As->PDF"``
            delay     : seconds to wait after each click for the next level to open

        Example::

            s.menu_click("Edit->Find->Find Next")
        """
        for item in (i.strip() for i in menu_path.split("->")):
            el = self.find(item, timeout=timeout)
            if el is None:
                print(f"[LiveSession] menu_click: '{item}' not found")
                return False
            self._do_click(el)
            time.sleep(delay)
            self._cache.clear()
        return True

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def send_keys(self, text: str) -> None:
        """Type *text* character by character via pyautogui."""
        pyautogui.typewrite(text, interval=0.04)

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut, e.g. ``s.hotkey("ctrl", "s")``."""
        pyautogui.hotkey(*keys)

    def press(self, key: str) -> None:
        """Press a single key, e.g. ``s.press("enter")``."""
        pyautogui.press(key)

    # ── Drag and drop ─────────────────────────────────────────────────────────

    def drag_and_drop(self, source: str, target: str, timeout: float = 5.0) -> bool:
        """Drag from the center of *source* path to the center of *target* path."""
        src = self.find(source, timeout)
        tgt = self.find(target, timeout)
        if src is None or tgt is None:
            print("[LiveSession] drag_and_drop: source or target not found")
            return False
        sr, tr = src.rectangle(), tgt.rectangle()
        pyautogui.moveTo((sr.left + sr.right) // 2, (sr.top + sr.bottom) // 2, duration=0.15)
        pyautogui.dragTo((tr.left + tr.right) // 2, (tr.top + tr.bottom) // 2, duration=0.3, button="left")
        self._cache.clear()
        return True

    # ── OCR ───────────────────────────────────────────────────────────────────

    def ocr_find(self, query: str, exact: bool = False, timeout: float = 5.0) -> Optional[OCRWrapper]:
        """
        Screenshot the active window and return the first OCR match for *query*.
        Retries until *timeout* expires.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            results = _ocr_scan(self._win(), query)
            if exact:
                results = [r for r in results if r.window_text().lower() == query.lower()]
            if results:
                return results[0]
            time.sleep(0.5)
        return None

    def ocr_find_all(self, query: str = "") -> list[OCRWrapper]:
        """Return all OCR detections in the current window, optionally filtered by *query*."""
        return _ocr_scan(self._win(), query)

    def ocr_click(self, query: str, exact: bool = False, timeout: float = 5.0) -> bool:
        """Click the first OCR match for *query*."""
        result = self.ocr_find(query, exact=exact, timeout=timeout)
        if result is None:
            print(f"[LiveSession] ocr_click: {query!r} not found")
            return False
        self._do_click(result)
        return True

    # ── Smart click ───────────────────────────────────────────────────────────

    def smart_click(self, query: str, timeout: float = 5.0) -> bool:
        """
        Try clicking *query* via UIA element tree first, then OCR fallback.
        Returns True on the first successful hit.
        """
        if self.click(query, timeout=timeout):
            return True
        print(f"[LiveSession] smart_click: UIA miss — trying OCR for {query!r}")
        return self.ocr_click(query, timeout=timeout)

    # ── Application lifecycle ─────────────────────────────────────────────────

    def focus(self) -> None:
        """Bring the application window to the foreground."""
        try:
            import win32gui, win32con
            h = self._win().handle
            win32gui.SetWindowPos(h, win32con.HWND_TOPMOST,   0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetWindowPos(h, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(h)
        except Exception:
            try:
                self._win().set_focus()
            except Exception:
                pass

    def close(self) -> None:
        """Close the application."""
        try:
            self._app.kill()
        except Exception:
            pyautogui.hotkey("alt", "f4")

    # ── UIPath context ────────────────────────────────────────────────────────

    def path(self, prefix: str) -> UIPath:
        """
        Return a context manager that prepends *prefix* to all calls in the block.

        Example::

            with s.path("Untitled - Notepad||Window"):
                s.click("File||MenuItem")
        """
        return UIPath(self, prefix)

    # ── Cache control ─────────────────────────────────────────────────────────

    def invalidate_cache(self) -> None:
        """Force the next search to bypass the TTL cache."""
        self._cache.clear()

    # ── Introspection ─────────────────────────────────────────────────────────

    def summary(self) -> None:
        """Print a brief summary of the connected window."""
        try:
            win = self._win()
            r   = win.rectangle()
            print(f"\n{'─'*60}")
            print(f"  LiveSession : {win.window_text()!r}")
            print(f"  PID         : {win.element_info.process_id}")
            print(f"  Handle      : {win.handle:#010x}")
            print(f"  Rect        : ({r.left},{r.top}) → ({r.right},{r.bottom})")
            print(f"  Path stack  : {self._path_stack or '(none)'}")
            print(f"{'─'*60}\n")
        except Exception as exc:
            print(f"[LiveSession] summary error: {exc}")

    def __repr__(self) -> str:
        try:
            return f"LiveSession(window={self._win().window_text()!r})"
        except Exception:
            return "LiveSession(<disconnected>)"


# ─────────────────────────────────────────────────────────────────────────────
# Quick demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("gui_live.py — connect to a running window")
    print("Usage: python gui_live.py [--pid PID] [--title TEXT]")

    pid   = None
    title = None
    args  = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--pid"   and i + 1 < len(args): pid   = int(args[i + 1])
        if a == "--title" and i + 1 < len(args): title = args[i + 1]

    if not pid and not title:
        from gui_detector import list_all_windows, print_windows
        wins = list_all_windows()
        print_windows(wins)
        try:
            choice = int(input("  Pick a window number (0 to quit): "))
        except (ValueError, EOFError):
            sys.exit(0)
        if 0 < choice <= len(wins):
            pid = wins[choice - 1]["pid"]

    if pid:
        s = connect_application(pid=pid)
    elif title:
        s = connect_application(title=title)
    else:
        sys.exit(0)

    s.summary()

    print("All buttons (live UIA):")
    for btn in s.find_all("||Button"):
        try:
            r = btn.rectangle()
            cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
            print(f"  {btn.window_text()!r:30}  center=({cx},{cy})")
        except Exception:
            pass