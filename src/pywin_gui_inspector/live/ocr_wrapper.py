from __future__ import annotations

from typing import Optional
import pyautogui


class OCRWrapper:
    """Duck-typed UIA element backed by an EasyOCR detection.

    Exposes the same interface used by pywinauto element wrappers so that
    OCR results can be passed to the same code paths that handle real UIA
    elements.

    Attributes:
        confidence: Detection confidence percentage (0–100) reported by
            EasyOCR.
    """

    def __init__(self, text: str, rect: tuple[int, int, int, int], confidence: float) -> None:
        """Initializes the wrapper with OCR detection data.

        Args:
            text: The text string recognised by EasyOCR.
            rect: Bounding box of the detection in screen coordinates as a
                ``(left, top, right, bottom)`` tuple.
            confidence: EasyOCR confidence score converted to a percentage
                (0.0 – 100.0).
        """
        self._text      = text
        self._rect      = rect
        self.confidence = confidence

    def window_text(self) -> str:
        """Returns the OCR-detected text for this element.

        Returns:
            The text string recognised by EasyOCR.
        """
        return self._text

    def is_enabled(self) -> bool:
        """Indicates whether the element is enabled for interaction.

        Returns:
            Always True, as OCR detections are assumed to be interactable.
        """
        return True

    def is_visible(self) -> bool:
        """Indicates whether the element is currently visible on screen.

        Returns:
            Always True, as OCR detections are inherently visible.
        """
        return True

    def rectangle(self):
        """Returns the bounding rectangle of the detected text region.

        Returns:
            A pywinauto ``RECT`` structure initialised from the stored
            ``(left, top, right, bottom)`` screen coordinates.
        """
        from pywinauto.win32structures import RECT
        return RECT(*self._rect)

    def center(self) -> tuple[int, int]:
        """Calculates the center point of the OCR detection bounding box.

        Returns:
            A ``(x, y)`` tuple of the horizontal and vertical center
            coordinates in screen space.
        """
        l, t, r, b = self._rect
        return (l + r) // 2, (t + b) // 2

    def click_input(self) -> None:
        """Moves the mouse to the center of this element and performs a click."""
        x, y = self.center()
        pyautogui.moveTo(x, y, duration=0.08)
        pyautogui.click()

    click = click_input

    def __repr__(self) -> str:
        """Returns a developer-friendly string representation.

        Returns:
            A string showing the detected text and confidence percentage.
        """
        return f"OCRWrapper({self._text!r}, conf={self.confidence:.1f}%)"


class OCREngine:
    """Runs EasyOCR on a window region.

    Grabs a screenshot of the element's bounding rectangle and passes it
    to EasyOCR, returning the results as a list of :class:`OCRWrapper`
    objects.
    """

    @staticmethod
    def scan(element, query: str = "", lang: Optional[list[str]] = None) -> list[OCRWrapper]:
        """Captures the element's screen region and runs EasyOCR on it.

        Takes a screenshot of the element's bounding rectangle, runs the
        EasyOCR reader over it, and returns detected text regions filtered
        by *query*.

        Args:
            element: A pywinauto element wrapper (or any object with a
                ``rectangle()`` method) whose screen region will be scanned.
            query: Optional substring filter; only detections whose text
                contains this string (case-insensitive) are returned.
                Pass an empty string to return all detections.
            lang: List of language codes passed to the EasyOCR ``Reader``
                (e.g. ``["en", "de"]``). Defaults to ``["en"]`` when
                ``None``.

        Returns:
            A list of :class:`OCRWrapper` instances for each text detection
            that satisfies the *query* filter, with coordinates translated
            to absolute screen space.

        Raises:
            ImportError: If ``easyocr``, ``Pillow``, or ``numpy`` are not
                installed.
        """
        try:
            import easyocr
            import numpy as np
            from PIL import ImageGrab
        except ImportError as exc:
            raise ImportError("pip install easyocr Pillow") from exc

        r   = element.rectangle()
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        raw = easyocr.Reader(lang or ["en"], verbose=False).readtext(np.array(img))

        results: list[OCRWrapper] = []
        for bbox, text, conf in raw:
            text = (text or "").strip()
            if not text or (query and query.lower() not in text.lower()):
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            results.append(OCRWrapper(
                text,
                (r.left + int(min(xs)), r.top + int(min(ys)),
                 r.left + int(max(xs)), r.top + int(max(ys))),
                round(conf * 100, 1),
            ))
        return results