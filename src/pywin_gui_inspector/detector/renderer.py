from __future__ import annotations


class Renderer:
    """Formats and prints element trees, window lists, and search results to stdout."""

    INDENT = "  "

    @classmethod
    def tree(cls, node: dict, indent: int = 0) -> None:
        """Recursively print an element tree node and all its descendants.

        Formats each node as ``[ControlType] 'Name'  auto_id='...'  rect=...``
        and appends ``[HIDDEN]`` or ``[DISABLED]`` flags when applicable.
        Recurses into ``node["children"]`` with increasing indentation.

        Args:
            node:   Element dict produced by ``WindowInspector.walk``.
            indent: Current indentation level; callers should leave this at 0.
        """
        name  = (node.get("name") or "").strip() or "<no name>"
        ctype = node.get("control_type") or "?"
        aid   = node.get("automation_id") or ""
        rect  = node.get("rectangle") or ""
        vis   = "" if node.get("is_visible") else " [HIDDEN]"
        ena   = "" if node.get("is_enabled") else " [DISABLED]"
        parts = [f"[{ctype}] {name!r}"]
        if aid:  parts.append(f"  auto_id={aid!r}")
        parts.append(f"  rect={rect}")
        print(f"{cls.INDENT * indent}{'  '.join(parts)}{vis}{ena}")
        for child in node.get("children", []):
            cls.tree(child, indent + 1)

    @staticmethod
    def windows(windows: list[dict]) -> None:
        """Print a numbered list of top-level windows with PID, handle, and title.

        Args:
            windows: List of window dicts as returned by ``WindowInspector.list_windows``.
        """
        sep = "─" * 70
        print(f"\n{sep}\n  Found {len(windows)} open window(s)\n{sep}")
        for i, w in enumerate(windows, 1):
            print(f"  [{i:>3}] PID={w['pid']:<6}  handle={w['handle']:<8}  title={w['title']!r}")
        print(f"{sep}\n")

    @staticmethod
    def ocr_results(results: list[dict], query: str = "") -> None:
        """Print a table of OCR detection results with confidence scores and coordinates.

        Args:
            results: List of OCR result dicts from ``OCRProcessor.find_text`` or
                     ``scan_all``, each with ``text``, ``confidence``, and ``rect``.
            query:   The search term that produced these results.  When supplied,
                     the header reads ``matching '<query>'``; otherwise ``found``.
        """
        label = f"matching {query!r}" if query else "found"
        sep   = "─" * 70
        print(f"\n{sep}\n  OCR — {len(results)} result(s) {label}\n{sep}")
        for r in results:
            rc = r["rect"]
            print(f"  [{r['confidence']:>5.1f}%]  {r['text']!r:<30}  "
                  f"({rc['left']},{rc['top']})→({rc['right']},{rc['bottom']})")
        print(f"{sep}\n")

    @staticmethod
    def image_results(results: list[dict], template_path: str) -> None:
        """Print a table of image template match results with positions and bounding boxes.

        Args:
            results:       List of match dicts from ``ImageMatcher.find``, each with
                           ``center``, ``confidence``, and ``rect``.
            template_path: Path of the reference template image, shown in the header.
        """
        sep = "─" * 70
        print(f"\n{sep}\n  Image search — {len(results)} match(es) for {template_path!r}\n{sep}")
        if not results:
            print("  (no matches found)")
        for i, r in enumerate(results, 1):
            rc = r["rect"]
            c  = r["center"]
            print(f"  [{i}]  center=({c['x']},{c['y']})  "
                  f"({rc['left']},{rc['top']})→({rc['right']},{rc['bottom']})")
        print(f"{sep}\n")