from __future__ import annotations

import os
import sys


class ImageMatcher:
    """Locates a reference image on the live screen using PyAutoGUI template matching.

    Useful for finding icon-only toolbar buttons or any custom-drawn control that
    has no accessibility name or automation ID, but can be identified visually.
    Requires ``pyautogui`` and ``opencv-python`` (for confidence-threshold matching).
    """

    @staticmethod
    def require_deps() -> None:
        """Verify that ``pyautogui`` and ``opencv-python`` are installed.

        Uses ``importlib`` for a fast, import-free check.  Exits the process with
        a ``pip install`` hint when either dependency is missing so the error
        surfaces clearly rather than as a buried ``ImportError``.
        """
        missing = [
            pkg for pkg, mod in [("pyautogui", "pyautogui"), ("opencv-python", "cv2")]
            if not __import__("importlib").util.find_spec(mod)
        ]
        if missing:
            sys.exit(f"[ERROR] pip install {' '.join(missing)}\n")

    @staticmethod
    def find(template_path: str, confidence: float = 0.9) -> list[dict]:
        """Search the entire screen for every occurrence of *template_path*.

        Uses ``pyautogui.locateAllOnScreen`` which internally applies OpenCV
        normalised cross-correlation.  The match quality is controlled by
        *confidence*: lower values tolerate more visual variation but risk
        false positives.

        Args:
            template_path: Absolute or relative path to the reference ``.png``
                           screenshot.  The image should be captured at 100 % zoom
                           on the same screen DPI as the automation target.
            confidence:    Match threshold in the range 0.0–1.0.  Defaults to 0.9.
                           Requires ``opencv-python``; without it PyAutoGUI ignores
                           the threshold and performs an exact match.

        Returns:
            List of match dicts, each containing:
            - ``template``   – path to the reference image used.
            - ``confidence`` – the threshold that was applied.
            - ``center``     – ``{"x": int, "y": int}`` of the matched region center.
            - ``rect``       – ``{"left", "top", "right", "bottom"}`` bounding box
                               in absolute screen pixels.
            Returns an empty list when the template file is not found, no matches
            exist, or an error occurs during the search.
        """
        import pyautogui
        if not os.path.isfile(template_path):
            print(f"[!] Template not found: {template_path!r}")
            return []
        try:
            locations = list(pyautogui.locateAllOnScreen(template_path, confidence=confidence))
        except pyautogui.ImageNotFoundException:
            return []
        except Exception as exc:
            print(f"[!] Image search error: {exc}")
            return []
        results = []
        for box in locations:
            cx, cy = pyautogui.center(box)
            results.append({
                "template":   template_path,
                "confidence": confidence,
                "center":     {"x": cx, "y": cy},
                "rect": {
                    "left":   box.left,
                    "top":    box.top,
                    "right":  box.left + box.width,
                    "bottom": box.top  + box.height,
                },
            })
        return results