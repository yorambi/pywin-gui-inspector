from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PathEntry:
    """Represents a single node segment parsed from a UIA path string.

    Attributes:
        name: The element name or regex pattern to match against window text.
        ctrl: The UIA control-type string to match (e.g. "Button", "Edit").
        regex: If True, ``name`` is treated as a regular expression.
        wildcard: If True, this segment matches any element unconditionally.
    """

    name:     str
    ctrl:     str
    regex:    bool = False
    wildcard: bool = False


class PathSyntax:
    """Parses and matches UIA path strings.

    Path strings are ``->``-separated segments of the form
    ``[name][||ctrl_type]``.  Special suffixes allow grid-cell addressing
    (``#[row,col]``) and fractional click offsets (``%(dx,dy)``).

    Attributes:
        WINDOW_TYPES: Control-type names that are treated as top-level windows
            when deciding whether a search should start from the Desktop.
    """

    WINDOW_TYPES: frozenset[str] = frozenset({"window", "dialog", "popup"})

    @staticmethod
    def parse(path_str: str) -> tuple[list[PathEntry], Optional[tuple], Optional[tuple]]:
        """Parses a path string into a list of PathEntry objects plus optional modifiers.

        Strips a trailing ``%(dx,dy)`` offset and/or ``#[row,col]`` grid
        specifier from the path string before splitting it on ``->``.

        Args:
            path_str: A UIA path string such as
                ``"My Window||Window->OK||Button"`` or
                ``"Table||DataGrid #[1,2]"``.

        Returns:
            A three-tuple ``(entries, grid, offset)`` where:

            - ``entries`` is a list of :class:`PathEntry` objects, one per
              ``->``-separated segment.
            - ``grid`` is a ``(row, col)`` int tuple extracted from a
              ``#[row,col]`` suffix, or ``None`` if absent.
            - ``offset`` is a ``(dx, dy)`` float tuple extracted from a
              ``%(dx,dy)`` suffix, or ``None`` if absent.
        """
        offset = None
        m = re.search(r'%\(\s*([+-]?\d*\.?\d+)\s*,\s*([+-]?\d*\.?\d+)\s*\)\s*$', path_str)
        if m:
            offset   = (float(m.group(1)), float(m.group(2)))
            path_str = path_str[:m.start()].rstrip()

        grid = None
        m = re.search(r'#\[\s*(\d+)\s*,\s*(\d+)\s*\]\s*$', path_str)
        if m:
            grid     = (int(m.group(1)), int(m.group(2)))
            path_str = path_str[:m.start()].rstrip()

        entries: list[PathEntry] = []
        for node in path_str.split("->"):
            node = node.strip()
            if node == "*":
                entries.append(PathEntry("", "", wildcard=True))
                continue
            name_part, _, ctrl_part = node.partition("||")
            name_part = name_part.strip()
            ctrl_part = ctrl_part.strip()
            is_regex  = name_part.lower().startswith("regex:")
            if is_regex:
                name_part = name_part[6:].strip()
            entries.append(PathEntry(name=name_part, ctrl=ctrl_part, regex=is_regex))

        return entries, grid, offset

    @staticmethod
    def match(element, entry: PathEntry) -> bool:
        """Tests whether a live UIA element satisfies the given PathEntry criteria.

        A wildcard entry always matches.  Otherwise, the element's window
        text must contain ``entry.name`` (or match it as a regex), and if
        ``entry.ctrl`` is specified, the element's control type must match
        it case-insensitively.

        Args:
            element: A pywinauto element wrapper to test.
            entry: The :class:`PathEntry` criteria to match against.

        Returns:
            True if the element satisfies all non-empty criteria in *entry*,
            False otherwise.
        """
        if entry.wildcard:
            return True
        if entry.name:
            text = (element.window_text() or "").strip()
            if entry.regex:
                if not re.search(entry.name, text):
                    return False
            elif entry.name.lower() not in text.lower():
                return False
        if entry.ctrl:
            try:
                ct = element.element_info.control_type or ""
                if ct.lower() != entry.ctrl.lower():
                    return False
            except Exception:
                pass
        return True