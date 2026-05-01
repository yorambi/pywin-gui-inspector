from __future__ import annotations


class PathBuilder:
    """Walks the UIA tree upward from an element to build a recorder path string.

    Traverses the element's ancestor chain, collecting name and control-type
    tokens, and joins them with ``->`` separators to produce a path that
    :class:`~pywin_gui_inspector.live.session.LiveSession` can later resolve.

    Attributes:
        SKIP_UNNAMED: Set of control-type names that are silently skipped
            when they carry no window text, to keep paths concise.
    """

    SKIP_UNNAMED: frozenset[str] = frozenset(
        {"Pane", "Group", "Custom", "Thumb", "ScrollBar", "TitleBar", "Header"}
    )

    @staticmethod
    def build(element) -> tuple[str, str]:
        """Builds a UIA path string by walking from *element* up to its window root.

        Ascends the element hierarchy up to 20 levels, collecting
        ``name||ctrl`` tokens at each level (skipping unnamed structural
        containers).  Stops at a named Window or Dialog boundary.  The
        collected tokens are reversed so the path reads top-down.

        Args:
            element: The pywinauto element wrapper to build a path for.

        Returns:
            A two-tuple ``(full_path, short_label)`` where:

            - ``full_path`` is the complete ``->``-joined path string from
              the top-level window down to *element*.
            - ``short_label`` is the last (leaf) token of the path, suitable
              for display in a tooltip or log message.
        """
        parts: list[str] = []
        current = element

        for _ in range(20):
            try:
                name = (current.window_text() or "").strip()
                ctrl = (current.element_info.control_type or "").strip()
            except Exception:
                break
            if not name and ctrl in PathBuilder.SKIP_UNNAMED:
                try:
                    current = current.parent()
                    continue
                except Exception:
                    break
            if name or ctrl:
                parts.append(f"{name}||{ctrl}" if (name and ctrl) else (name or f"||{ctrl}"))
            if ctrl in ("Window", "Dialog") and name:
                break
            try:
                parent = current.parent()
                if parent is None or parent is current:
                    break
                current = parent
            except Exception:
                break

        parts.reverse()
        return "->".join(parts), (parts[-1] if parts else "")