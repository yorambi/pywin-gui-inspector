from __future__ import annotations

from typing import Optional
from pywin_gui_inspector.helper.rect_helper import RectHelper


class TreeSearch:
    """Depth-first search and traversal helpers for element-tree dicts.

    All methods operate purely on the nested ``dict`` structure produced by
    ``WindowInspector.walk`` — no live process or pywinauto connection is needed.
    """

    @staticmethod
    def by_name(
        node: dict,
        name: str,
        *,
        exact: bool = False,
        enabled_only: bool = True,
        visible_only: bool = True,
    ) -> Optional[dict]:
        """Search the tree depth-first for the first element whose name matches *name*.

        By default performs a case-insensitive substring match and skips disabled
        or hidden elements.  An exact match mode is available for cases where a
        substring like ``"Save"`` would otherwise also match ``"Save As"``.

        Args:
            node:         Root node dict of the element tree to search.
            name:         Text to search for in element names.
            exact:        When ``True``, requires the full element name to equal
                          *name* (case-insensitive).  When ``False`` (default),
                          any element whose name *contains* *name* matches.
            enabled_only: Skip elements whose ``is_enabled`` flag is ``False``.
                          Defaults to ``True``.
            visible_only: Skip elements whose ``is_visible`` flag is ``False``.
                          Defaults to ``True``.

        Returns:
            The first matching element dict, or ``None`` if no match is found.
        """
        node_name = (node.get("name") or "").strip()
        matched = (node_name.lower() == name.lower()) if exact else (name.lower() in node_name.lower())
        if matched:
            skip = ((enabled_only and not node.get("is_enabled", True))
                    or (visible_only and not node.get("is_visible", True)))
            if not skip:
                return node
        for child in node.get("children", []):
            result = TreeSearch.by_name(child, name, exact=exact,
                                        enabled_only=enabled_only, visible_only=visible_only)
            if result:
                return result
        return None

    @staticmethod
    def by_auto_id(node: dict, auto_id: str) -> Optional[dict]:
        """Search the tree depth-first for the first element with the given automation ID.

        Automation IDs are the most stable element identifier — they are set by
        the application developer and survive UI state changes.  The comparison
        is an exact string match.

        Args:
            node:     Root node dict of the element tree to search.
            auto_id:  The exact ``automation_id`` string to look for.

        Returns:
            The first element dict whose ``automation_id`` equals *auto_id*,
            or ``None`` if no match is found.
        """
        if (node.get("automation_id") or "") == auto_id:
            return node
        for child in node.get("children", []):
            result = TreeSearch.by_auto_id(child, auto_id)
            if result:
                return result
        return None

    @staticmethod
    def by_control_type(node: dict, control_type: str) -> Optional[dict]:
        """Search the tree depth-first for the first element of the given control type.

        The comparison is case-insensitive, so ``"button"`` and ``"Button"`` both
        match an element whose ``control_type`` is ``"Button"``.

        Args:
            node:         Root node dict to search.
            control_type: UIA control type string to find (e.g. ``"Button"``,
                          ``"Edit"``, ``"MenuItem"``).

        Returns:
            The first matching element dict, or ``None`` if none is found.
        """
        if (node.get("control_type") or "").lower() == control_type.lower():
            return node
        for child in node.get("children", []):
            result = TreeSearch.by_control_type(child, control_type)
            if result:
                return result
        return None

    @staticmethod
    def find_all(
        node: dict,
        *,
        name: str = "",
        control_type: str = "",
        enabled_only: bool = True,
        visible_only: bool = True,
    ) -> list[dict]:
        """Collect every element in the tree that satisfies all supplied filters.

        All filters are ANDed together.  Omit a filter (or leave it as the empty
        string) to skip that criterion entirely.  The walk is depth-first and
        includes the root node itself.

        Args:
            node:         Root node dict to traverse.
            name:         Case-insensitive substring that must appear in the
                          element's name.  Empty string means any name.
            control_type: Exact (case-insensitive) control type to match.
                          Empty string means any type.
            enabled_only: Exclude elements whose ``is_enabled`` is ``False``.
            visible_only: Exclude elements whose ``is_visible`` is ``False``.

        Returns:
            List of all matching element dicts in depth-first order.  May be empty.
        """
        results: list[dict] = []

        def _walk(n: dict) -> None:
            ok = (
                (not name         or name.lower() in (n.get("name") or "").lower())
                and (not control_type or (n.get("control_type") or "").lower() == control_type.lower())
                and (not enabled_only or n.get("is_enabled", True))
                and (not visible_only or n.get("is_visible", True))
            )
            if ok:
                results.append(n)
            for child in n.get("children", []):
                _walk(child)

        _walk(node)
        return results

    @staticmethod
    def flatten(node: dict) -> list[dict]:
        """Return a flat depth-first list of every node in the tree.

        Unlike ``find_all``, no filters are applied — every node including
        hidden and disabled elements is included.  Useful for bulk processing
        with list comprehensions or ``len``/``count`` operations.

        Args:
            node: Root node dict to traverse.

        Returns:
            Flat list of all element dicts, starting with *node* itself.
        """
        result = [node]
        for child in node.get("children", []):
            result.extend(TreeSearch.flatten(child))
        return result

    @staticmethod
    def count(node: dict) -> int:
        """Return the total number of nodes in the tree rooted at *node*.

        Counts the node itself plus all descendants recursively.

        Args:
            node: Root node dict.

        Returns:
            Integer count of all nodes.
        """
        return 1 + sum(TreeSearch.count(c) for c in node.get("children", []))

    @staticmethod
    def rect(node: dict) -> tuple[int, int, int, int]:
        """Return the ``(left, top, right, bottom)`` screen rectangle of an element node.

        Delegates to ``RectHelper.parse`` which handles both the tuple-literal and
        pywinauto RECT repr formats stored in the ``"rectangle"`` field.

        Args:
            node: Element dict with a ``"rectangle"`` string field.

        Returns:
            ``(left, top, right, bottom)`` in absolute screen pixels.

        Raises:
            ValueError: When the ``"rectangle"`` field cannot be parsed.
        """
        return RectHelper.parse(node["rectangle"])

    @staticmethod
    def center(node: dict) -> tuple[int, int]:
        """Return the screen center pixel ``(x, y)`` of an element node.

        Combines ``rect`` and ``RectHelper.center`` so callers don't need to
        perform the two-step calculation themselves.

        Args:
            node: Element dict with a ``"rectangle"`` string field.

        Returns:
            ``(x, y)`` integer coordinates of the element's screen center.
        """
        return RectHelper.center(TreeSearch.rect(node))

    @staticmethod
    def print_flat(node: dict, *, enabled_only: bool = False) -> None:
        """Print a flat, human-readable listing of all elements with their properties.

        Each line shows ``[ControlType] 'Name'  [auto_id]  (rectangle)``.  Useful
        for quick inspection of what a JSON export contains without building a
        full tree view.

        Args:
            node:         Root node dict to traverse.
            enabled_only: When ``True``, only enabled elements are printed.
        """
        for el in TreeSearch.flatten(node):
            if enabled_only and not el.get("is_enabled"):
                continue
            name  = (el.get("name") or "").strip() or "<no name>"
            ctype = el.get("control_type") or "?"
            aid   = el.get("automation_id") or ""
            print(f"  [{ctype}] {name!r}{'  [' + aid + ']' if aid else ''}  {el.get('rectangle','')}")