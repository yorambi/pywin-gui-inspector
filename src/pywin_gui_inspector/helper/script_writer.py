from __future__ import annotations

import json
import re
from pathlib import Path

from pywin_gui_inspector.helper.tree_search    import TreeSearch
from pywin_gui_inspector.helper.search_helpers import OCRSearch, ImageSearch


class ScriptWriter:
    """Generates Python automation scripts from plain-English step instructions.

    Parses a gui_detector JSON export to resolve element references, then
    translates a human-readable instruction string into a complete, runnable
    Python script that drives a GUISession.

    Attributes:
        path: Resolved path to the JSON export file.
        tree: Root node of the captured element tree.
        ocr_results: List of OCR detection dicts from the export.
        image_results: List of image-template detection dicts from the export.
    """

    def __init__(self, export_path: str | Path) -> None:
        """Initializes the writer by loading the given JSON export.

        Args:
            export_path: Path to the gui_detector JSON export file used to
                resolve element names when generating click calls.
        """
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

    def _resolve_click(self, target: str) -> str:
        """Generates the most specific click call available for a target name.

        Checks the element tree, OCR results, and image results in order,
        preferring the most reliable lookup method.

        Args:
            target: The name or label of the element to click.

        Returns:
            A Python source code string representing the appropriate click
            call (e.g. ``s.click_by_auto_id(...)``, ``s.click_ocr(...)``,
            etc.).  Falls back to ``s.smart_click(...)`` with a warning
            comment if the target is not found in any dataset.
        """
        node = TreeSearch.by_name(self.tree, target)
        if node:
            aid = node.get("automation_id")
            return f"s.click_by_auto_id({aid!r})" if aid else f"s.click_by_name({target!r})"
        if OCRSearch.find(self.ocr_results, target) is not None:
            return f"s.click_ocr({target!r})"
        if ImageSearch.find(self.image_results, target) is not None:
            return f"s.click_image({target!r})"
        return f"s.smart_click({target!r})  # WARNING: not found in export"

    def _parse_steps(self, instructions: str) -> list[str]:
        """Splits a multi-step instruction string into individual step strings.

        Splits on newlines when present, otherwise on commas. Strips
        surrounding whitespace and trailing periods from each step.

        Args:
            instructions: A single string containing one or more steps
                separated by newlines or commas.

        Returns:
            A list of non-empty, trimmed step strings.
        """
        lines = instructions.strip().splitlines() if "\n" in instructions else instructions.split(",")
        return [s.strip().rstrip(".") for s in lines if s.strip()]

    def _step_to_code(self, step: str) -> str:
        """Translates a single plain-English step into a Python source line.

        Matches the step against a set of regular-expression patterns
        (wait, hotkey, press, screenshot, type…into, click, open) and
        returns the corresponding Python call.  Unrecognised steps produce
        a ``# TODO`` comment.

        Args:
            step: A single instruction step string (e.g. "click Submit",
                "type Hello into Search", "wait 2 seconds").

        Returns:
            A Python source code string for the step, or a ``# TODO``
            comment if no pattern matches.
        """
        patterns = [
            (r"wait\s+(\d+(?:\.\d+)?)\s+seconds?",         lambda m: f"time.sleep({m.group(1)})"),
            (r"hotkey\s+(\S+)",                             lambda m: f"pyautogui.hotkey({', '.join(repr(k) for k in m.group(1).lower().split('+'))})"),
            (r"press\s+(\S+)",                              lambda m: f"pyautogui.press({m.group(1).lower()!r})"),
            (r"screenshot\s+as\s+(\S+)",                    lambda m: f"pyautogui.screenshot({m.group(1)!r})"),
            (r"type\s+(.+?)\s+into\s+(.+)",                 lambda m: f"s.type_into({m.group(2).strip()!r}, {m.group(1).strip()!r})"),
            (r"click\s+(.+)",                               lambda m: self._resolve_click(m.group(1).strip())),
            (r"open\s+(?:the\s+)?(.+?)(?:\s+menu)?$",       lambda m: self._resolve_click(m.group(1).strip())),
        ]
        for pattern, handler in patterns:
            m = re.match(pattern, step, re.IGNORECASE)
            if m:
                return handler(m)
        if step.lower() == "close":
            return "pyautogui.hotkey('alt', 'f4')"
        return f"# TODO: {step!r}"

    def generate(self, instructions: str) -> str:
        """Generates a complete Python automation script from instruction text.

        Builds a script header with required imports and a GUISession
        constructor, then appends one code line per parsed instruction step.

        Args:
            instructions: Plain-English steps, separated by newlines or
                commas (e.g. "click OK, wait 1 second, close").

        Returns:
            A string containing the full, ready-to-run Python script.
        """
        steps = self._parse_steps(instructions)
        header = [
            "import time", "import sys", "from pathlib import Path", "",
            "import pyautogui", "",
            "sys.path.insert(0, str(Path(__file__).parent.parent))",
            "from gui_helper import GUISession", "",
            f"s = GUISession({str(self.path)!r}, click_delay=0.4, move_duration=0.15)", "",
        ]
        return "\n".join(header + [self._step_to_code(s) for s in steps] + [""])

    def preview(self, instructions: str) -> None:
        """Prints the generated script to standard output without saving it.

        Args:
            instructions: Plain-English steps to generate and preview.
        """
        print(self.generate(instructions))

    def write(self, instructions: str, output: str | Path = "generated_script.py") -> Path:
        """Generates the automation script and writes it to a file.

        Args:
            instructions: Plain-English steps to generate.
            output: Destination file path for the generated script.
                Defaults to ``"generated_script.py"`` in the current
                working directory.

        Returns:
            The resolved Path to the written script file.
        """
        out = Path(output)
        out.write_text(self.generate(instructions), encoding="utf-8")
        print(f"[ScriptWriter] Written → {out}")
        return out