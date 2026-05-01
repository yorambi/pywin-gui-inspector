from __future__ import annotations

from pywinauto import Desktop
from pywin_gui_inspector.live.path_syntax import PathEntry, PathSyntax


class ElementSearch:
    """Searches the live UIA element tree for elements matching path entries."""

    @staticmethod
    def subtree(root, entry: PathEntry, max_depth: int = 12) -> list:
        """Performs a depth-first search of the subtree rooted at *root*.

        Walks every descendant of *root* up to *max_depth* levels deep,
        collecting all elements that satisfy the given PathEntry criteria.

        Args:
            root: The pywinauto element wrapper to use as the search root.
            entry: The :class:`~pywin_gui_inspector.live.path_syntax.PathEntry`
                criteria that each candidate element must satisfy.
            max_depth: Maximum recursion depth below *root*. Defaults to 12.

        Returns:
            A list of pywinauto element wrappers that match *entry*, in
            depth-first order.
        """
        results = []

        def _walk(node, depth: int) -> None:
            if depth > max_depth:
                return
            if PathSyntax.match(node, entry):
                results.append(node)
            try:
                for child in node.children():
                    _walk(child, depth + 1)
            except Exception:
                pass

        _walk(root, 0)
        return results

    @staticmethod
    def by_path(root, entries: list[PathEntry]) -> list:
        """Resolves a sequence of PathEntry segments against a subtree root.

        Applies each entry in turn, using the previous step's results as
        the search roots for the next step, effectively walking down the
        path hierarchy.

        Args:
            root: The pywinauto element wrapper to start searching from.
            entries: Ordered list of
                :class:`~pywin_gui_inspector.live.path_syntax.PathEntry`
                objects representing each step of the path.

        Returns:
            A list of pywinauto element wrappers that satisfy the full path.
            Returns ``[root]`` when *entries* is empty.
        """
        if not entries:
            return [root]
        candidates = [root]
        for entry in entries:
            next_candidates: list = []
            for node in candidates:
                next_candidates.extend(ElementSearch.subtree(node, entry))
            candidates = next_candidates
        return candidates

    @staticmethod
    def from_desktop(entries: list[PathEntry]) -> list:
        """Searches all visible Desktop windows for elements matching *entries*.

        Uses the first PathEntry to filter top-level windows and then calls
        :meth:`by_path` on each matching window for the remaining entries.

        Args:
            entries: Ordered list of
                :class:`~pywin_gui_inspector.live.path_syntax.PathEntry`
                objects.  The first entry is matched against top-level
                Desktop windows; subsequent entries are resolved within
                each matched window.

        Returns:
            A flat list of all pywinauto element wrappers that satisfy the
            complete path across all Desktop windows.
        """
        first, *rest = entries
        wins = [w for w in Desktop(backend="uia").windows() if PathSyntax.match(w, first)]
        if not rest:
            return wins
        results: list = []
        for win in wins:
            results.extend(ElementSearch.by_path(win, rest))
        return results