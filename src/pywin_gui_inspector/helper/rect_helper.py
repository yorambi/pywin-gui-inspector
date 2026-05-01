from __future__ import annotations

import ast
import re


class RectHelper:
    """Parses rectangle strings from gui_detector exports and computes derived values."""

    @staticmethod
    def parse(rect_str: str) -> tuple[int, int, int, int]:
        """Parse a rectangle string into a ``(left, top, right, bottom)`` int tuple.

        Handles two common formats produced by pywinauto:
        - Python tuple literal ``"(10, 20, 100, 200)"``
        - pywinauto RECT repr ``"RECT(left=10, top=20, right=100, bottom=200)"``

        Tries ``ast.literal_eval`` first for the tuple form.  Falls back to
        extracting all integers via regex for the RECT repr form.

        Args:
            rect_str: String representation of a bounding rectangle.

        Returns:
            A 4-tuple of ints ``(left, top, right, bottom)``.

        Raises:
            ValueError: When the string does not contain at least four integers.
        """
        try:
            val = ast.literal_eval(str(rect_str))
            if isinstance(val, (tuple, list)) and len(val) == 4:
                return tuple(int(v) for v in val)
        except Exception:
            pass
        nums = re.findall(r"-?\d+", str(rect_str))
        if len(nums) >= 4:
            return tuple(int(n) for n in nums[:4])
        raise ValueError(f"Cannot parse rectangle: {rect_str!r}")

    @staticmethod
    def center(rect: tuple) -> tuple[int, int]:
        """Return the pixel coordinates of the center of a bounding rectangle.

        Args:
            rect: A 4-tuple ``(left, top, right, bottom)`` in screen pixels.

        Returns:
            ``(x, y)`` integer coordinates of the geometric center, computed as
            ``((left+right)//2, (top+bottom)//2)``.
        """
        l, t, r, b = rect
        return (l + r) // 2, (t + b) // 2

    @staticmethod
    def from_dict(d: dict) -> tuple[int, int, int, int]:
        """Extract ``(left, top, right, bottom)`` from an OCR or image result dict.

        OCR and image result dicts store their bounding box under a nested ``rect``
        key with sub-keys ``left``, ``top``, ``right``, ``bottom``.  This helper
        unpacks that structure into a flat tuple for use with ``center`` and other
        coordinate utilities.

        Args:
            d: A detection result dict containing a ``"rect"`` sub-dict with
               the four edge keys.

        Returns:
            ``(left, top, right, bottom)`` as integers.
        """
        r = d["rect"]
        return r["left"], r["top"], r["right"], r["bottom"]