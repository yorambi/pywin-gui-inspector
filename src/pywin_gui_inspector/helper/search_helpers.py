from __future__ import annotations

from pathlib import Path
from typing import Optional
from pywin_gui_inspector.helper.rect_helper import RectHelper


class OCRSearch:
    """Searches OCR result lists produced by ``OCRProcessor``."""

    @staticmethod
    def find(results: list[dict], query: str, *, exact: bool = False) -> Optional[dict]:
        """Return the first OCR result whose text contains or equals *query*.

        Iterates the list in order and returns on the first match, so when
        multiple results match, the one with the highest original confidence
        (which EasyOCR lists first) is returned.

        Args:
            results: List of OCR result dicts, each with a ``"text"`` key.
            query:   Search term (case-insensitive).
            exact:   When ``True``, the element's text must equal *query* exactly
                     (still case-insensitive).  When ``False`` (default), a
                     substring match is used.

        Returns:
            The first matching result dict, or ``None`` if no match is found.
        """
        for r in results:
            text  = (r.get("text") or "").strip()
            match = text.lower() == query.lower() if exact else query.lower() in text.lower()
            if match:
                return r
        return None

    @staticmethod
    def find_all(results: list[dict], query: str) -> list[dict]:
        """Return all OCR results whose text contains *query* as a substring.

        Args:
            results: List of OCR result dicts to filter.
            query:   Case-insensitive substring to search for.

        Returns:
            List of all matching result dicts in their original order.
            Returns an empty list when no results match.
        """
        return [r for r in results if query.lower() in (r.get("text") or "").lower()]

    @staticmethod
    def center(ocr_result: dict) -> tuple[int, int]:
        """Return the screen center pixel ``(x, y)`` of an OCR detection result.

        Extracts the ``rect`` sub-dict and delegates to ``RectHelper.center``.

        Args:
            ocr_result: A single OCR result dict with a ``"rect"`` key containing
                        ``left``, ``top``, ``right``, and ``bottom`` sub-keys.

        Returns:
            ``(x, y)`` integer coordinates of the center of the detected text region.
        """
        return RectHelper.center(RectHelper.from_dict(ocr_result))


class ImageSearch:
    """Searches image template match result lists produced by ``ImageMatcher``."""

    @staticmethod
    def find(results: list[dict], template: str = "") -> Optional[dict]:
        """Return the first image match, optionally filtered by template filename.

        When *template* is empty, the very first result is returned regardless
        of which template image it came from.  When *template* is supplied, only
        matches whose template filename (basename only, without directory path)
        equals the basename of *template* are considered.

        Args:
            results:  List of image match dicts from ``ImageMatcher.find``.
            template: Optional filename filter, e.g. ``"save_icon.png"``.  Path
                      components are stripped before comparison so absolute paths
                      work as well.

        Returns:
            The first matching result dict, or ``None`` if the list is empty or
            no entry matches the filter.
        """
        for r in results:
            if not template or Path(r.get("template", "")).name == Path(template).name:
                return r
        return None

    @staticmethod
    def center(image_result: dict) -> tuple[int, int]:
        """Return the pre-computed center ``(x, y)`` of an image match result.

        Image match results store the center coordinates explicitly in a
        ``"center": {"x": ..., "y": ...}`` sub-dict computed at match time by
        PyAutoGUI.  This helper unpacks that into a plain tuple.

        Args:
            image_result: A single image match dict with a ``"center"`` sub-dict.

        Returns:
            ``(x, y)`` integer pixel coordinates of the matched region's center.
        """
        c = image_result["center"]
        return c["x"], c["y"]