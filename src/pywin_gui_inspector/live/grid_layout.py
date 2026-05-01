from __future__ import annotations

from typing import Optional


class GridLayout:
    """Arranges elements into a 2-D grid by screen position for #[row,col] addressing.

    Groups elements into rows using a vertical-proximity tolerance, then
    sorts each row left-to-right so that individual cells can be addressed
    by zero-based (row, column) indices.
    """

    @staticmethod
    def sort(
        elements: list,
        min_width:  int = 0,
        min_height: int = 0,
        line_tolerance: Optional[int] = None,
    ) -> tuple[int, int, list[list]]:
        """Sorts elements into a 2-D grid ordered by screen position.

        Filters out elements whose bounding rectangle is smaller than
        *min_width* × *min_height*, then clusters the remaining elements
        into rows based on vertical proximity.  Within each row elements
        are ordered left-to-right.

        Args:
            elements: A list of pywinauto element wrappers to arrange.
            min_width: Minimum bounding-box width in pixels required for an
                element to be included. Defaults to 0 (no filtering).
            min_height: Minimum bounding-box height in pixels required for
                an element to be included. Defaults to 0 (no filtering).
            line_tolerance: Maximum vertical distance in pixels between an
                element's top edge and the representative top of a row for
                the element to be placed in that row.  When ``None``, the
                value is auto-computed as half the median element height,
                with a floor of 1. Defaults to ``None``.

        Returns:
            A three-tuple ``(nrows, ncols, grid)`` where:

            - ``nrows`` is the number of rows detected.
            - ``ncols`` is the maximum number of columns in any row.
            - ``grid`` is a list of lists of pywinauto element wrappers
              (or ``None`` for empty cells), shaped ``[nrows][ncols]``.
            Returns ``(0, 0, [])`` when no elements survive the size filter.
        """
        rects = []
        for el in elements:
            try:
                r = el.rectangle()
                if (r.right - r.left) >= min_width and (r.bottom - r.top) >= min_height:
                    rects.append((r.top, r.left, r.bottom, r.right, el))
            except Exception:
                pass

        if not rects:
            return 0, 0, []

        if line_tolerance is None:
            heights       = sorted(e[2] - e[0] for e in rects)
            line_tolerance = max(1, heights[len(heights) // 2] // 2)

        rects.sort()
        rows: list[list] = []
        for top, left, bot, right, el in rects:
            placed = any(
                abs(top - row[0][0]) <= line_tolerance and row.append((top, left, bot, right, el))
                for row in rows
            )
            if not placed:
                rows.append([(top, left, bot, right, el)])

        for row in rows:
            row.sort(key=lambda x: x[1])

        ncols = max(len(r) for r in rows)
        grid  = [
            [row[c][-1] if c < len(row) else None for c in range(ncols)]
            for row in rows
        ]
        return len(rows), ncols, grid