from __future__ import annotations

import sys

from pywinauto import Application


class OCRProcessor:
    """Detects visible text in window screenshots using EasyOCR.

    The EasyOCR ``Reader`` instance is created lazily on first use and cached
    at the class level so model weights (~100 MB) are only downloaded and loaded
    once per interpreter session.
    """

    _reader = None

    @staticmethod
    def require_deps() -> None:
        """Verify that ``easyocr`` and ``Pillow`` are installed.

        Checks both packages via ``importlib`` without importing them so the
        check is fast.  If either is missing the process exits with a clear
        ``pip install`` hint rather than raising an ``ImportError`` deep in the
        call stack.
        """
        missing = [
            pkg for pkg, mod in [("easyocr", "easyocr"), ("Pillow", "PIL")]
            if not __import__("importlib").util.find_spec(mod)
        ]
        if missing:
            sys.exit(f"[ERROR] pip install {' '.join(missing)}\n")

    @classmethod
    def get_reader(cls):
        """Return the shared EasyOCR English reader, initialising it on first call.

        The reader is stored as a class-level attribute so subsequent calls return
        the cached instance without reloading the neural network weights.

        Returns:
            An ``easyocr.Reader`` configured for English (``["en"]``).
        """
        if cls._reader is None:
            import easyocr
            print("[*] Initialising EasyOCR…")
            cls._reader = easyocr.Reader(["en"], verbose=False)
        return cls._reader

    @staticmethod
    def capture_window(pid: int):
        """Take a screenshot of the first window owned by the given process.

        Connects to the process via pywinauto, retrieves the window rectangle,
        and uses ``PIL.ImageGrab`` to capture exactly that region of the screen.

        Args:
            pid: Windows process ID of the target application.

        Returns:
            A 2-tuple ``(image, origin)`` where *image* is a ``PIL.Image``
            of the window contents and *origin* is ``(left, top)`` in screen
            pixel coordinates.  Returns ``(None, (0, 0))`` when no window is
            found for the given PID.
        """
        from PIL import ImageGrab
        wins = Application(backend="uia").connect(process=pid).windows()
        if not wins:
            return None, (0, 0)
        r = wins[0].rectangle()
        return ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom)), (r.left, r.top)

    @staticmethod
    def results_to_dicts(raw: list, win_left: int, win_top: int) -> list[dict]:
        """Convert raw EasyOCR output to the project's standard result-dict format.

        EasyOCR returns detections as ``(quad_bbox, text, confidence)`` tuples
        where *quad_bbox* is a list of four ``[x, y]`` corner points in clockwise
        order.  This method converts those to ``{left, top, right, bottom}`` rects
        in absolute screen coordinates by adding the window origin offset.

        Args:
            raw:      List of EasyOCR detection tuples.
            win_left: X pixel offset of the captured window's left edge on screen.
            win_top:  Y pixel offset of the captured window's top edge on screen.

        Returns:
            List of dicts, each with keys ``text``, ``confidence`` (0–100 float),
            and ``rect`` (a nested dict with ``left``, ``top``, ``right``, ``bottom``
            in absolute screen pixels).  Empty detections are silently skipped.
        """
        out = []
        for bbox, text, conf in raw:
            text = (text or "").strip()
            if not text:
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            out.append({
                "text":       text,
                "confidence": round(conf * 100, 1),
                "rect": {
                    "left":   win_left + int(min(xs)),
                    "top":    win_top  + int(min(ys)),
                    "right":  win_left + int(max(xs)),
                    "bottom": win_top  + int(max(ys)),
                },
            })
        return out

    @classmethod
    def find_text(cls, pid: int, query: str) -> list[dict]:
        """Screenshot the window and return all OCR detections containing *query*.

        Captures the window, runs the full EasyOCR scan, then filters the results
        to those whose detected text contains *query* as a case-insensitive substring.

        Args:
            pid:   PID of the target application window.
            query: Text fragment to search for (case-insensitive substring match).

        Returns:
            List of matching detection dicts (same format as ``results_to_dicts``).
            Returns an empty list when the window cannot be captured.
        """
        import numpy as np
        img, (wl, wt) = cls.capture_window(pid)
        if img is None:
            return []
        raw = cls.get_reader().readtext(np.array(img))
        return [r for r in cls.results_to_dicts(raw, wl, wt)
                if query.lower() in r["text"].lower()]

    @classmethod
    def scan_all(cls, pid: int) -> list[dict]:
        """Screenshot the window and return every text region EasyOCR detects.

        Unlike ``find_text``, no query filter is applied — all non-empty text
        detections are returned with their bounding boxes and confidence scores.

        Args:
            pid: PID of the target application window.

        Returns:
            List of all detection dicts.  Returns an empty list when the window
            cannot be captured.
        """
        import numpy as np
        img, (wl, wt) = cls.capture_window(pid)
        if img is None:
            return []
        return cls.results_to_dicts(cls.get_reader().readtext(np.array(img)), wl, wt)