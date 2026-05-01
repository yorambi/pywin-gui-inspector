from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from pywin_gui_inspector.helper.tree_search    import TreeSearch
from pywin_gui_inspector.helper.search_helpers import OCRSearch, ImageSearch

try:
    from pywinauto import Application
    _PYW = True
except ImportError:
    _PYW = False

try:
    import pyautogui
    _PYAG = True
except ImportError:
    _PYAG = False


class GUISession:
    """Automation session loaded from a gui_detector JSON export.

    Provides a unified interface for interacting with a previously captured
    GUI state, resolving element lookups through a priority chain:
    element tree first, then OCR results, then image template results.

    Attributes:
        path: Resolved path to the JSON export file.
        click_delay: Seconds to pause after each simulated click.
        move_duration: Duration in seconds for mouse-movement animation.
        tree: Root node of the captured element tree.
        ocr_results: List of OCR detection dictionaries from the export.
        image_results: List of image-template detection dictionaries from the export.
    """

    def __init__(
        self,
        export_path: str | Path,
        *,
        click_delay: float = 0.3,
        move_duration: float = 0.1,
    ) -> None:
        """Initializes the session by loading and parsing a JSON export file.

        Args:
            export_path: Path to the gui_detector JSON export file.
            click_delay: Seconds to sleep after every simulated mouse click.
                Defaults to 0.3.
            move_duration: Duration passed to pyautogui.moveTo() for smooth
                mouse movement. Defaults to 0.1.
        """
        self.path          = Path(export_path)
        self.click_delay   = click_delay
        self.move_duration = move_duration

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

        self._pid = self.tree.get("process_id")

    def _live_win(self):
        """Connects to the live application window using the stored process ID.

        Returns:
            The first window object found for the application process.

        Raises:
            RuntimeError: If pywinauto is not installed.
            RuntimeError: If no process_id is present in the export data.
            RuntimeError: If no windows are found for the stored process ID.
        """
        if not _PYW:
            raise RuntimeError("pywinauto is not installed.")
        if not self._pid:
            raise RuntimeError("No process_id in export.")
        wins = Application(backend="uia").connect(process=self._pid).windows()
        if not wins:
            raise RuntimeError(f"No windows found for PID {self._pid}.")
        return wins[0]

    def _click(self, x: int, y: int) -> None:
        """Moves the mouse to the given coordinates and performs a click.

        Args:
            x: Horizontal screen coordinate to click.
            y: Vertical screen coordinate to click.

        Raises:
            RuntimeError: If pyautogui is not installed.
        """
        if not _PYAG:
            raise RuntimeError("pyautogui is not installed.")
        pyautogui.moveTo(x, y, duration=self.move_duration)
        pyautogui.click()
        time.sleep(self.click_delay)

    # ── Tree ──────────────────────────────────────────────────────────────────

    def find(self, name: str, *, exact: bool = False) -> Optional[dict]:
        """Searches the element tree for a node matching the given name.

        Args:
            name: The element name (or substring) to search for.
            exact: If True, only exact case-insensitive name matches are
                returned. Defaults to False (substring match).

        Returns:
            The first matching element node dict, or None if not found.
        """
        return TreeSearch.by_name(self.tree, name, exact=exact)

    def find_auto_id(self, auto_id: str) -> Optional[dict]:
        """Searches the element tree for a node with the given automation ID.

        Args:
            auto_id: The UIA automation ID string to search for.

        Returns:
            The first matching element node dict, or None if not found.
        """
        return TreeSearch.by_auto_id(self.tree, auto_id)

    def click_by_name(self, name: str, *, live: bool = False) -> bool:
        """Clicks the first element whose name matches the given string.

        Args:
            name: The element name to locate and click.
            live: If True, delegates the click to pywinauto using a live
                connection to the running process instead of using stored
                screen coordinates. Defaults to False.

        Returns:
            True if the element was found and clicked, False otherwise.
        """
        node = TreeSearch.by_name(self.tree, name)
        if node is None:
            print(f"[GUISession] Not found by name: {name!r}")
            return False
        if live:
            self._live_win().child_window(
                title=node["name"], control_type=node.get("control_type")
            ).click_input()
        else:
            self._click(*TreeSearch.center(node))
        return True

    def click_by_auto_id(self, auto_id: str, *, live: bool = False) -> bool:
        """Clicks the element identified by the given UIA automation ID.

        Args:
            auto_id: The UIA automation ID of the element to click.
            live: If True, uses a live pywinauto connection to perform
                the click instead of stored coordinates. Defaults to False.

        Returns:
            True if the element was found and clicked, False otherwise.
        """
        node = TreeSearch.by_auto_id(self.tree, auto_id)
        if node is None:
            print(f"[GUISession] Not found by auto_id: {auto_id!r}")
            return False
        if live:
            self._live_win().child_window(auto_id=auto_id).click_input()
        else:
            self._click(*TreeSearch.center(node))
        return True

    def type_into(self, name: str, text: str, *, clear_first: bool = True) -> bool:
        """Locates an Edit control and types the given text into it.

        Searches first by element name, then falls back to the first Edit
        control in the tree. Optionally clears existing content before typing.

        Args:
            name: Name of the target element. If no exact match is found the
                first Edit control in the tree is used as a fallback.
            text: The string to type into the control.
            clear_first: If True, selects all text and deletes it before
                typing. Defaults to True.

        Returns:
            True if an Edit element was found and text was typed, False
            otherwise.

        Raises:
            RuntimeError: If pyautogui is not installed.
        """
        if not _PYAG:
            raise RuntimeError("pyautogui is not installed.")
        node = TreeSearch.by_name(self.tree, name)
        if node is None or node.get("control_type") != "Edit":
            node = TreeSearch.by_control_type(self.tree, "Edit")
        if node is None:
            print(f"[GUISession] Edit not found for: {name!r}")
            return False
        self._click(*TreeSearch.center(node))
        if clear_first:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
        pyautogui.typewrite(text, interval=0.05)
        return True

    def all_buttons(self) -> list[dict]:
        """Returns all Button elements found in the element tree.

        Returns:
            A list of element node dicts with control_type "Button".
        """
        return TreeSearch.find_all(self.tree, control_type="Button")

    def all_edits(self) -> list[dict]:
        """Returns all Edit elements found in the element tree.

        Returns:
            A list of element node dicts with control_type "Edit".
        """
        return TreeSearch.find_all(self.tree, control_type="Edit")

    def all_checkboxes(self) -> list[dict]:
        """Returns all CheckBox elements found in the element tree.

        Returns:
            A list of element node dicts with control_type "CheckBox".
        """
        return TreeSearch.find_all(self.tree, control_type="CheckBox")

    def all_of_type(self, ct: str) -> list[dict]:
        """Returns all elements of the specified control type from the tree.

        Args:
            ct: The UIA control type string to filter by (e.g. "Button",
                "Edit", "ComboBox").

        Returns:
            A list of element node dicts matching the specified control type.
        """
        return TreeSearch.find_all(self.tree, control_type=ct)

    # ── OCR ───────────────────────────────────────────────────────────────────

    def click_ocr(self, query: str, *, exact: bool = False) -> bool:
        """Clicks the screen region matched by an OCR result for the query text.

        Args:
            query: The text string to search for in the OCR results.
            exact: If True, requires an exact (case-insensitive) text match.
                Defaults to False (substring match).

        Returns:
            True if a matching OCR result was found and clicked, False
            otherwise.
        """
        result = OCRSearch.find(self.ocr_results, query, exact=exact)
        if result is None:
            print(f"[GUISession] OCR not found: {query!r}")
            return False
        self._click(*OCRSearch.center(result))
        return True

    def ocr_text_at(self, query: str) -> Optional[str]:
        """Returns the OCR-detected text string that matches the given query.

        Args:
            query: Substring to search for among OCR results.

        Returns:
            The full text of the first matching OCR result, or None if no
            match is found.
        """
        r = OCRSearch.find(self.ocr_results, query)
        return r["text"] if r else None

    def all_ocr_text(self) -> list[str]:
        """Returns all OCR-detected text strings from the export.

        Returns:
            A list of text strings, one per OCR detection result.
        """
        return [r["text"] for r in self.ocr_results]

    # ── Image ─────────────────────────────────────────────────────────────────

    def click_image(self, template: str = "") -> bool:
        """Clicks the screen region matched by an image template search result.

        Args:
            template: Template name or path used to locate the desired image
                result. An empty string returns the first available result.

        Returns:
            True if a matching image result was found and clicked, False
            otherwise.
        """
        result = ImageSearch.find(self.image_results, template)
        if result is None:
            print(f"[GUISession] Image not found: {template!r}")
            return False
        self._click(*ImageSearch.center(result))
        return True

    # ── Smart ─────────────────────────────────────────────────────────────────

    def smart_click(self, query: str) -> bool:
        """Attempts to click a target by trying tree, OCR, and image search in order.

        Tries element-tree name lookup first, then OCR text search, then
        image-template search, stopping at the first successful match.

        Args:
            query: The search string passed to each lookup strategy in turn.

        Returns:
            True if any strategy located and clicked the target, False if all
            strategies failed.
        """
        for check, action in [
            (lambda: TreeSearch.by_name(self.tree, query) is not None,    lambda: self.click_by_name(query)),
            (lambda: OCRSearch.find(self.ocr_results, query) is not None, lambda: self.click_ocr(query)),
            (lambda: ImageSearch.find(self.image_results, query) is not None, lambda: self.click_image(query)),
        ]:
            if check():
                return action()
        print(f"[GUISession] smart_click: {query!r} not found")
        return False

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Collects key statistics about the loaded session into a dictionary.

        Returns:
            A dict containing the export path, process ID, window name,
            total element count, OCR result count, image result count,
            button count, and edit-field count.
        """
        return {
            "export":         str(self.path),
            "process_id":     self._pid,
            "window_name":    self.tree.get("name"),
            "total_elements": TreeSearch.count(self.tree),
            "ocr_results":    len(self.ocr_results),
            "image_results":  len(self.image_results),
            "buttons":        len(self.all_buttons()),
            "edits":          len(self.all_edits()),
        }

    def print_summary(self) -> None:
        """Prints a formatted summary of the session to standard output."""
        s = self.summary()
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"  GUISession: {s['window_name']!r}  (PID {s['process_id']})")
        print(f"{sep}")
        for label, key in [("Export", "export"), ("Elements", "total_elements"),
                           ("Buttons", "buttons"), ("Edits", "edits"),
                           ("OCR", "ocr_results"), ("Images", "image_results")]:
            print(f"  {label:<12}: {s[key]}")
        print(f"{sep}\n")

    def __repr__(self) -> str:
        """Returns an unambiguous string representation of the session.

        Returns:
            A string showing the window name, PID, and total element count.
        """
        return (f"GUISession(window={self.tree.get('name')!r}, pid={self._pid}, "
                f"elements={TreeSearch.count(self.tree)})")