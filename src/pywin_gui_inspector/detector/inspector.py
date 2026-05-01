from __future__ import annotations

import time
from typing import Optional

from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError


class WindowInspector:
    """Connects to running Windows applications and walks their UIA element trees.

    Args:
        max_depth: Maximum recursion depth when walking the element tree.
                   Deeper trees produce richer output but take longer to
                   traverse.  Defaults to 8.
    """

    def __init__(self, max_depth: int = 8) -> None:
        """Initialise the inspector with the given recursion limit.

        Args:
            max_depth: Cap on element-tree traversal depth.  Use a lower
                       value (e.g. 3) for Electron or browser windows that
                       expose a very deep DOM-like accessibility tree.
        """
        self.max_depth = max_depth

    @staticmethod
    def list_windows() -> list[dict]:
        """Return a snapshot of all currently visible top-level windows.

        Enumerates every top-level window registered with the UIA Desktop and
        collects the key properties into plain dicts.  Windows that raise
        exceptions during property extraction are silently skipped.

        Returns:
            List of dicts, each with keys ``title``, ``class_name``, ``handle``,
            ``pid``, ``rect``, ``is_visible``, and ``is_enabled``.
        """
        windows = []
        for win in Desktop(backend="uia").windows():
            try:
                windows.append({
                    "title":      win.window_text(),
                    "class_name": win.class_name(),
                    "handle":     win.handle,
                    "pid":        win.process_id(),
                    "rect":       str(win.rectangle()),
                    "is_visible": win.is_visible(),
                    "is_enabled": win.is_enabled(),
                })
            except Exception:
                continue
        return windows

    @staticmethod
    def get_element_info(element) -> dict:
        """Extract all available UIA properties from a single element into a dict.

        Attempts to read ten standard UIA properties.  Each extraction is wrapped
        in ``_safe`` so a failure on one property (e.g. an element whose handle
        is not available) does not prevent the others from being collected.

        Args:
            element: A pywinauto UIA wrapper object.

        Returns:
            Dict with keys ``name``, ``control_type``, ``class_name``,
            ``automation_id``, ``rectangle``, ``is_visible``, ``is_enabled``,
            ``handle``, ``process_id``, and ``framework_id``.  Any property
            that cannot be read is stored as ``None``.
        """
        extractors = {
            "name":          lambda e: e.window_text(),
            "control_type":  lambda e: e.element_info.control_type,
            "class_name":    lambda e: e.class_name(),
            "automation_id": lambda e: e.element_info.automation_id,
            "rectangle":     lambda e: str(e.rectangle()),
            "is_visible":    lambda e: e.is_visible(),
            "is_enabled":    lambda e: e.is_enabled(),
            "handle":        lambda e: getattr(e, "handle", None),
            "process_id":    lambda e: e.element_info.process_id,
            "framework_id":  lambda e: e.element_info.framework_id,
        }
        return {k: _safe(fn, element) for k, fn in extractors.items()}

    def walk(self, element, depth: int = 0) -> list[dict]:
        """Recursively walk the element tree rooted at *element*.

        Performs a depth-first traversal, collecting property dicts for every
        element up to ``self.max_depth`` levels deep.  Each node dict gains two
        extra keys: ``depth`` (its level in the tree) and ``children`` (a list
        of immediate child node dicts, so the return value is both a flat list
        and a nested tree simultaneously).

        Args:
            element: The root UIA element to start from (typically a window).
            depth:   Current recursion depth; callers should leave this at 0.

        Returns:
            A flat list where the first element is the root node dict (which
            contains the fully nested ``children`` tree), followed by all
            descendant dicts in depth-first order.  Returns an empty list when
            *depth* exceeds ``max_depth``.
        """
        if depth > self.max_depth:
            return []
        info = self.get_element_info(element)
        info.update({"depth": depth, "children": []})
        results = [info]
        for child in _children(element):
            sub = self.walk(child, depth + 1)
            if sub:
                info["children"].append(sub[0])
                results.extend(sub[1:])
        return results

    def inspect_pid(self, pid: int) -> Optional[dict]:
        """Connect to the process with *pid* and return its element tree.

        Attaches to the first window of the given process, walks its UIA tree
        up to ``max_depth``, and returns the root node dict.

        Args:
            pid: Windows process ID of the target application.

        Returns:
            The root element dict (with nested ``children``) on success,
            or ``None`` when the PID has no windows or an error occurs.
        """
        try:
            wins = Application(backend="uia").connect(process=pid).windows()
            if not wins:
                print(f"[!] No windows found for PID {pid}")
                return None
            print(f"\n[+] Inspecting: {wins[0].window_text()!r}  (PID {pid})\n")
            tree = self.walk(wins[0])
            return tree[0] if tree else None
        except Exception as exc:
            print(f"[ERROR] {exc}")
            return None

    def inspect_title(self, title: str) -> Optional[dict]:
        """Connect to the first window whose title contains *title* and return its tree.

        Uses a case-sensitive regex ``.*<title>.*`` to locate the window via
        pywinauto's ``connect`` method.

        Args:
            title: Partial window title to search for.

        Returns:
            The root element dict on success, or ``None`` when no matching window
            is found or an error occurs.
        """
        try:
            wins = Application(backend="uia").connect(title_re=f".*{title}.*").windows()
            if not wins:
                print(f"[!] No windows matching title={title!r}")
                return None
            print(f"\n[+] Inspecting: {wins[0].window_text()!r}\n")
            tree = self.walk(wins[0])
            return tree[0] if tree else None
        except ElementNotFoundError:
            print(f"[!] Window with title containing {title!r} not found.")
            return None
        except Exception as exc:
            print(f"[ERROR] {exc}")
            return None

    def interactive(self) -> Optional[dict]:
        """List all open windows and prompt the user to pick one for inspection.

        Prints a numbered window list, reads an integer choice from stdin, and
        delegates to ``inspect_pid`` for the selected window.

        Returns:
            The root element dict for the chosen window, or ``None`` if the user
            enters 0, makes an invalid choice, or no windows are available.
        """
        from pywin_gui_inspector.detector.renderer import Renderer
        windows = self.list_windows()
        if not windows:
            print("[!] No windows found.")
            return None
        Renderer.windows(windows)
        try:
            choice = int(input("  Enter window number to inspect (0 to quit): "))
        except (ValueError, EOFError):
            choice = 0
        if choice <= 0 or choice > len(windows):
            return None
        return self.inspect_pid(windows[choice - 1]["pid"])


class ChangeMonitor:
    """Watches a window's element tree over time and reports element changes."""

    @staticmethod
    def snapshot(root: dict) -> set[str]:
        """Flatten all element names in the tree into a set for diff comparison.

        Walks the nested ``children`` structure depth-first and collects every
        ``name`` value, including empty strings, so that appearing or disappearing
        unnamed elements are also detected.

        Args:
            root: Root element dict from a previous ``WindowInspector.walk`` call.

        Returns:
            A ``set[str]`` of all element name strings present in the tree.
        """
        names: set[str] = set()
        def _walk(n: dict) -> None:
            names.add(n.get("name") or "")
            for c in n.get("children", []):
                _walk(c)
        _walk(root)
        return names

    @staticmethod
    def watch(pid: int, interval: float = 1.0, max_depth: int = 4) -> None:
        """Poll a window repeatedly and print a diff of added/removed elements.

        Re-inspects the window on every tick, computes the symmetric difference
        between the current and previous element name sets, and prints changes.
        Runs indefinitely until the window disappears or the user presses Ctrl-C.

        Args:
            pid:       PID of the window to watch.
            interval:  Seconds to sleep between polls.  Defaults to 1.0.
            max_depth: Tree traversal depth cap passed to ``WindowInspector``.
                       Lower values reduce noise in complex UIs.  Defaults to 4.
        """
        inspector = WindowInspector(max_depth=max_depth)
        print(f"[*] Watching PID {pid} every {interval}s  (Ctrl-C to stop)\n")
        previous: Optional[set] = None
        try:
            while True:
                root = inspector.inspect_pid(pid)
                if root is None:
                    print("[!] Window gone. Stopping.")
                    break
                current = ChangeMonitor.snapshot(root)
                if previous is not None:
                    added, removed = current - previous, previous - current
                    if added:   print(f"  [+] New:     {sorted(added)}")
                    if removed: print(f"  [-] Removed: {sorted(removed)}")
                    if not added and not removed: print("  [=] No change")
                else:
                    print(f"  [*] Baseline: {len(current)} element(s)")
                previous = current
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Stopped.")


def _safe(fn, element):
    """Call *fn(element)* and return ``None`` instead of raising on any exception.

    Used internally by ``get_element_info`` so that a single inaccessible
    property does not abort the entire info-extraction pass.

    Args:
        fn:      A callable that takes a pywinauto element and returns a value.
        element: The UIA element to pass to *fn*.

    Returns:
        The return value of ``fn(element)``, or ``None`` on any exception.
    """
    try:
        return fn(element)
    except Exception:
        return None


def _children(element) -> list:
    """Return the direct children of *element*, or an empty list on failure.

    Wraps ``element.children()`` so that elements that do not support child
    enumeration (e.g. leaf controls) are handled gracefully without raising.

    Args:
        element: A pywinauto UIA wrapper whose children should be retrieved.

    Returns:
        List of child UIA wrapper objects, or ``[]`` on any exception.
    """
    try:
        return element.children()
    except Exception:
        return []