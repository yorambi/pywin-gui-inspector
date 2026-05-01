from __future__ import annotations

import time
from typing import Optional

from pywinauto import Application, Desktop
import pyautogui

from pywin_gui_inspector.live.path_syntax    import PathSyntax
from pywin_gui_inspector.live.element_search import ElementSearch
from pywin_gui_inspector.live.cache          import TTLCache
from pywin_gui_inspector.live.readiness      import ReadinessChecker
from pywin_gui_inspector.live.grid_layout    import GridLayout
from pywin_gui_inspector.live.ocr_wrapper    import OCRWrapper, OCREngine
from pywin_gui_inspector.live.ui_path        import UIPath


class LiveSession:
    """Live GUI automation — queries the running UIA tree directly.

    Instantiate via connect_application() or start_application().

    Provides a high-level API for clicking, typing, dragging, and reading
    UI elements by path strings.  Element lookups are cached with a
    short TTL to avoid redundant UIA tree traversals.

    Attributes:
        _app: The connected pywinauto ``Application`` instance.
        _click_delay: Optional pause in seconds inserted after each click.
        _path_stack: Stack of path prefixes accumulated by nested
            :class:`~pywin_gui_inspector.live.ui_path.UIPath` context
            managers.
        _cache: Short-lived result cache keyed by resolved path strings.
    """

    def __init__(self, app: Application, click_delay: float = 0.0) -> None:
        """Initializes the live session with a connected pywinauto Application.

        Args:
            app: A pywinauto ``Application`` object already connected to the
                target process.
            click_delay: Seconds to sleep after every click action.
                Defaults to 0.0 (no delay).
        """
        self._app         = app
        self._click_delay = click_delay
        self._path_stack: list[str] = []
        self._cache       = TTLCache(ttl=2.0)

    def _full(self, path: str) -> str:
        """Prepends the accumulated path-stack prefix to a relative path string.

        Args:
            path: The relative path string to expand.

        Returns:
            The fully qualified path string with any stacked prefixes
            prepended and separated by ``->``.
        """
        prefix = "->".join(self._path_stack)
        return f"{prefix}->{path}" if prefix else path

    def _win(self):
        """Returns the first window of the connected application.

        Returns:
            The first pywinauto window wrapper for the application.

        Raises:
            RuntimeError: If the application has no open windows.
        """
        wins = self._app.windows()
        if not wins:
            raise RuntimeError("No windows found for this application.")
        return wins[0]

    def _search(self, path: str, timeout: float = 5.0) -> list:
        """Resolves a path string to a list of matching live elements.

        Checks the TTL cache first; on a cache miss, parses the full path,
        determines whether to start from the Desktop or the application
        window, and polls until elements are found or the deadline expires.
        Grid-cell filtering is applied when a ``#[row,col]`` suffix is
        present.

        Args:
            path: A relative or absolute UIA path string.
            timeout: Maximum seconds to retry the search before returning an
                empty list. Defaults to 5.0.

        Returns:
            A list of matching pywinauto element wrappers, or an empty list
            if nothing is found within *timeout* seconds.
        """
        full = self._full(path)
        cached, hit = self._cache.get(full)
        if hit:
            return cached

        entries, grid, _offset = PathSyntax.parse(full)
        if not entries:
            return []

        starts_at_desktop = (
            entries[0].ctrl.lower() in PathSyntax.WINDOW_TYPES
            or (not entries[0].ctrl and entries[0].name)
        )

        deadline = time.time() + timeout
        while time.time() <= deadline:
            results = (ElementSearch.from_desktop(entries)
                       if starts_at_desktop
                       else ElementSearch.by_path(self._win(), entries))
            if results:
                if grid is not None:
                    _, _, g = GridLayout.sort(results)
                    row, col = grid
                    results = ([g[row][col]]
                               if row < len(g) and col < len(g[row]) and g[row][col]
                               else [])
                self._cache.set(full, results)
                return results
            time.sleep(0.2)
        return []

    def _do_click(self, element, offset: Optional[tuple] = None) -> None:
        """Waits for element readiness and performs a mouse click on it.

        Computes the element's center, optionally adjusting by a fractional
        *offset*, then moves the mouse and clicks.  Falls back to
        ``element.click_input()`` if pyautogui fails.

        Args:
            element: The pywinauto element wrapper to click.
            offset: Optional ``(dx, dy)`` fractional offset where each
                component is a fraction of the element's half-width and
                half-height (range -1.0 to 1.0). Defaults to ``None``
                (center click).
        """
        ReadinessChecker.wait(element)
        try:
            r  = element.rectangle()
            hw = (r.right  - r.left) / 2
            hh = (r.bottom - r.top)  / 2
            cx = int(r.left + hw + (offset[0] * hw if offset else 0))
            cy = int(r.top  + hh + (offset[1] * hh if offset else 0))
            pyautogui.moveTo(cx, cy, duration=0.1)
            pyautogui.click()
        except Exception:
            element.click_input()
        if self._click_delay:
            time.sleep(self._click_delay)

    def find(self, path: str, timeout: float = 5.0):
        """Returns the first element matching the given path, or None.

        Args:
            path: UIA path string identifying the target element.
            timeout: Maximum seconds to wait for the element to appear.
                Defaults to 5.0.

        Returns:
            The first matching pywinauto element wrapper, or ``None`` if
            nothing is found within *timeout* seconds.
        """
        results = self._search(path, timeout)
        return results[0] if results else None

    def find_all(self, path: str, timeout: float = 5.0) -> list:
        """Returns all elements matching the given path.

        Args:
            path: UIA path string identifying the target elements.
            timeout: Maximum seconds to wait for at least one match.
                Defaults to 5.0.

        Returns:
            A list of all matching pywinauto element wrappers, or an empty
            list if nothing is found within *timeout* seconds.
        """
        return self._search(path, timeout)

    def click(self, path: str, timeout: float = 5.0) -> bool:
        """Clicks the first element that matches the given path.

        Args:
            path: UIA path string identifying the element to click.
            timeout: Maximum seconds to wait for the element. Defaults to 5.0.

        Returns:
            True if the element was found and clicked, False otherwise.
        """
        full = self._full(path)
        _, _, offset = PathSyntax.parse(full)
        results = self._search(path, timeout)
        if not results:
            print(f"[LiveSession] click: not found — {path!r}")
            return False
        self._do_click(results[0], offset)
        self._cache.clear()
        return True

    def double_click(self, path: str, timeout: float = 5.0) -> bool:
        """Double-clicks the first element matching the given path.

        Args:
            path: UIA path string identifying the element to double-click.
            timeout: Maximum seconds to wait for the element. Defaults to 5.0.

        Returns:
            True if the element was found and double-clicked, False otherwise.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] double_click: not found — {path!r}")
            return False
        ReadinessChecker.wait(el)
        try:
            el.double_click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.doubleClick((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        self._cache.clear()
        return True

    def right_click(self, path: str, timeout: float = 5.0) -> bool:
        """Right-clicks the first element matching the given path.

        Args:
            path: UIA path string identifying the element to right-click.
            timeout: Maximum seconds to wait for the element. Defaults to 5.0.

        Returns:
            True if the element was found and right-clicked, False otherwise.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] right_click: not found — {path!r}")
            return False
        ReadinessChecker.wait(el)
        try:
            el.right_click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.rightClick((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        self._cache.clear()
        return True

    def set_text(self, path: str, text: str, timeout: float = 5.0) -> bool:
        """Clears an input field and types the given text into it.

        Locates the element, clicks it to focus, selects all existing text,
        and types the replacement text using pyautogui.

        Args:
            path: UIA path string identifying the target input element.
            text: The string to type into the field.
            timeout: Maximum seconds to wait for the element. Defaults to 5.0.

        Returns:
            True if the element was found and text was entered, False
            otherwise.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] set_text: not found — {path!r}")
            return False
        ReadinessChecker.wait(el)
        try:
            el.click_input()
        except Exception:
            r = el.rectangle()
            pyautogui.click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        time.sleep(0.1)
        pyautogui.click(clicks=3, interval=0.06)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.typewrite(text, interval=0.04)
        self._cache.clear()
        return True

    def set_combobox(self, path: str, text: str, timeout: float = 5.0) -> bool:
        """Opens a ComboBox, types a value, and confirms with Enter.

        Args:
            path: UIA path string identifying the ComboBox element.
            text: The value to type into the ComboBox.
            timeout: Maximum seconds to wait for the element. Defaults to 5.0.

        Returns:
            True if the element was found and the value was entered, False
            otherwise.
        """
        el = self.find(path, timeout)
        if el is None:
            print(f"[LiveSession] set_combobox: not found — {path!r}")
            return False
        ReadinessChecker.wait(el)
        self._do_click(el)
        time.sleep(0.9)
        pyautogui.typewrite(text, interval=0.05)
        pyautogui.press("enter")
        self._cache.clear()
        return True

    def menu_click(self, menu_path: str, delay: float = 0.35, timeout: float = 5.0) -> bool:
        """Navigates a menu hierarchy by clicking each ``->``-separated item in turn.

        Args:
            menu_path: A ``->``-separated string of menu item names to click
                in sequence (e.g. ``"File->Save As"``).
            delay: Seconds to pause between each menu-item click to allow
                sub-menus to open. Defaults to 0.35.
            timeout: Maximum seconds to wait for each individual item.
                Defaults to 5.0.

        Returns:
            True if every menu item was found and clicked successfully,
            False if any item was not found.
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

    def send_keys(self, text: str) -> None:
        """Types a string of characters using pyautogui typewrite.

        Args:
            text: The string to type at the current keyboard focus.
        """
        pyautogui.typewrite(text, interval=0.04)

    def hotkey(self, *keys: str) -> None:
        """Sends a keyboard hotkey combination via pyautogui.

        Args:
            *keys: One or more key name strings to press simultaneously
                (e.g. ``"ctrl"``, ``"c"``).
        """
        pyautogui.hotkey(*keys)

    def press(self, key: str) -> None:
        """Presses and releases a single keyboard key via pyautogui.

        Args:
            key: The name of the key to press (e.g. ``"enter"``, ``"tab"``).
        """
        pyautogui.press(key)

    def drag_and_drop(self, source: str, target: str, timeout: float = 5.0) -> bool:
        """Drags the element at *source* and drops it onto the element at *target*.

        Args:
            source: UIA path string for the element to drag from.
            target: UIA path string for the element to drop onto.
            timeout: Maximum seconds to wait for each element. Defaults to 5.0.

        Returns:
            True if both elements were found and the drag completed, False
            if either element could not be located.
        """
        src, tgt = self.find(source, timeout), self.find(target, timeout)
        if src is None or tgt is None:
            print("[LiveSession] drag_and_drop: source or target not found")
            return False
        sr, tr = src.rectangle(), tgt.rectangle()
        pyautogui.moveTo((sr.left + sr.right) // 2, (sr.top + sr.bottom) // 2, duration=0.15)
        pyautogui.dragTo((tr.left + tr.right) // 2, (tr.top + tr.bottom) // 2, duration=0.3, button="left")
        self._cache.clear()
        return True

    def ocr_find(self, query: str, exact: bool = False, timeout: float = 5.0) -> Optional[OCRWrapper]:
        """Searches the window for visible text matching *query* using OCR.

        Polls the window's content repeatedly until a match is found or the
        timeout expires.

        Args:
            query: The text string to search for in the OCR results.
            exact: If True, only results whose text exactly matches *query*
                (case-insensitive) are returned. Defaults to False (substring
                match).
            timeout: Maximum seconds to keep retrying before returning None.
                Defaults to 5.0.

        Returns:
            The first :class:`~pywin_gui_inspector.live.ocr_wrapper.OCRWrapper`
            matching *query*, or ``None`` if not found within *timeout*
            seconds.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            results = OCREngine.scan(self._win(), query)
            if exact:
                results = [r for r in results if r.window_text().lower() == query.lower()]
            if results:
                return results[0]
            time.sleep(0.5)
        return None

    def ocr_find_all(self, query: str = "") -> list[OCRWrapper]:
        """Returns all OCR-detected text regions in the window matching *query*.

        Args:
            query: Optional substring filter for OCR results. Pass an empty
                string to return every detected text region.

        Returns:
            A list of :class:`~pywin_gui_inspector.live.ocr_wrapper.OCRWrapper`
            instances for all matching detections.
        """
        return OCREngine.scan(self._win(), query)

    def ocr_click(self, query: str, exact: bool = False, timeout: float = 5.0) -> bool:
        """Finds text via OCR and clicks the center of the detected region.

        Args:
            query: The text to locate on screen using OCR.
            exact: If True, requires an exact (case-insensitive) text match.
                Defaults to False.
            timeout: Maximum seconds to wait for the text to appear.
                Defaults to 5.0.

        Returns:
            True if the text was found and clicked, False otherwise.
        """
        result = self.ocr_find(query, exact=exact, timeout=timeout)
        if result is None:
            print(f"[LiveSession] ocr_click: {query!r} not found")
            return False
        self._do_click(result)
        return True

    def smart_click(self, query: str, timeout: float = 5.0) -> bool:
        """Attempts a UIA path click, falling back to OCR if the element is not found.

        Args:
            query: The target name or path string; tried first as a UIA path
                then as an OCR text query.
            timeout: Maximum seconds to wait during each lookup attempt.
                Defaults to 5.0.

        Returns:
            True if either the UIA or OCR click succeeded, False if both
            strategies failed.
        """
        if self.click(query, timeout=timeout):
            return True
        print(f"[LiveSession] smart_click: UIA miss — trying OCR for {query!r}")
        return self.ocr_click(query, timeout=timeout)

    def focus(self) -> None:
        """Brings the application window to the foreground.

        Attempts to set the window as topmost and then calls
        ``SetForegroundWindow``; falls back to pywinauto's ``set_focus()``
        if the Win32 approach fails.
        """
        try:
            import win32gui, win32con
            h = self._win().handle
            for topmost in (win32con.HWND_TOPMOST, win32con.HWND_NOTOPMOST):
                win32gui.SetWindowPos(h, topmost, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(h)
        except Exception:
            try: self._win().set_focus()
            except Exception: pass

    def close(self) -> None:
        """Closes the application by calling app.kill(), or Alt+F4 as a fallback."""
        try:   self._app.kill()
        except Exception: pyautogui.hotkey("alt", "f4")

    def path(self, prefix: str) -> UIPath:
        """Returns a UIPath context manager that scopes all lookups under *prefix*.

        Args:
            prefix: The path prefix to prepend inside the returned context
                manager's block.

        Returns:
            A :class:`~pywin_gui_inspector.live.ui_path.UIPath` context manager
            bound to this session and the given prefix.
        """
        return UIPath(self, prefix)

    def invalidate_cache(self) -> None:
        """Clears all cached element-search results immediately."""
        self._cache.clear()

    def summary(self) -> None:
        """Prints a formatted summary of the live session to standard output."""
        try:
            win, r = self._win(), self._win().rectangle()
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
        """Returns an unambiguous string representation of the live session.

        Returns:
            A string showing the current window title, or a disconnected
            indicator if the window cannot be reached.
        """
        try:   return f"LiveSession(window={self._win().window_text()!r})"
        except Exception: return "LiveSession(<disconnected>)"


class DesktopSession(LiveSession):
    """Automation session that searches all visible Desktop windows.

    No application connection required — paths resolved at runtime against
    all top-level windows on the Desktop.  Generated by gui_recorder.py.

    Unlike :class:`LiveSession`, this class requires no prior
    ``Application.connect()`` call; instead, every search is issued
    directly against ``Desktop(backend="uia")``.
    """

    def __init__(self, click_delay: float = 0.0) -> None:
        """Initializes a Desktop-scoped session with no application binding.

        Args:
            click_delay: Seconds to sleep after every click action.
                Defaults to 0.0 (no delay).
        """
        self._app:        None      = None   # type: ignore[assignment]
        self._click_delay           = click_delay
        self._path_stack: list[str] = []
        self._cache                 = TTLCache(ttl=2.0)

    def _win(self):
        """Returns the first window currently visible on the Desktop.

        Returns:
            The first pywinauto window wrapper from the Desktop enumeration.

        Raises:
            RuntimeError: If no windows are found on the Desktop.
        """
        wins = Desktop(backend="uia").windows()
        if not wins:
            raise RuntimeError("No windows found on Desktop.")
        return wins[0]

    def _search(self, path: str, timeout: float = 5.0) -> list:
        """Resolves a path against all Desktop windows, with TTL caching.

        Identical to :meth:`LiveSession._search` but always calls
        :meth:`~pywin_gui_inspector.live.element_search.ElementSearch.from_desktop`
        regardless of the first entry's control type.

        Args:
            path: A UIA path string to resolve against the Desktop.
            timeout: Maximum seconds to retry before returning an empty list.
                Defaults to 5.0.

        Returns:
            A list of matching pywinauto element wrappers, or an empty list
            if nothing is found within *timeout* seconds.
        """
        full = self._full(path)
        cached, hit = self._cache.get(full)
        if hit:
            return cached
        entries, grid, _offset = PathSyntax.parse(full)
        if not entries:
            return []
        deadline = time.time() + timeout
        while time.time() <= deadline:
            results = ElementSearch.from_desktop(entries)
            if results:
                if grid is not None:
                    _, _, g = GridLayout.sort(results)
                    row, col = grid
                    results = ([g[row][col]]
                               if row < len(g) and col < len(g[row]) and g[row][col]
                               else [])
                self._cache.set(full, results)
                return results
            time.sleep(0.2)
        return []

    def focus(self) -> None:
        """No-op: DesktopSession has no single application window to focus."""
        pass

    def close(self) -> None:
        """No-op: DesktopSession has no application process to close."""
        pass

    def __repr__(self) -> str:
        """Returns an unambiguous string representation of the desktop session.

        Returns:
            The fixed string ``"DesktopSession()"``.
        """
        return "DesktopSession()"