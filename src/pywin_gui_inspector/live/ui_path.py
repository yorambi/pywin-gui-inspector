from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pywin_gui_inspector.live.session import LiveSession


class UIPath:
    """Context manager that prepends a root path onto all LiveSession calls.

    When used as a ``with`` statement, pushes *prefix* onto the session's
    path stack so that every path resolved inside the block is automatically
    prefixed with *prefix*``->``.  The prefix is removed when the block exits,
    restoring the original stack state.

    Example::

        with session.path("My Window||Window") as s:
            s.click("OK||Button")   # resolved as "My Window||Window->OK||Button"
    """

    def __init__(self, session: "LiveSession", prefix: str) -> None:
        """Initializes the context manager with the session and path prefix.

        Args:
            session: The :class:`~pywin_gui_inspector.live.session.LiveSession`
                instance whose path stack will be modified.
            prefix: The path segment to prepend to all lookups performed
                inside the ``with`` block.
        """
        self._session = session
        self._prefix  = prefix

    def __enter__(self) -> "LiveSession":
        """Pushes the prefix onto the session's path stack and returns the session.

        Returns:
            The :class:`~pywin_gui_inspector.live.session.LiveSession` instance
            so it can be used directly via the ``as`` clause.
        """
        self._session._path_stack.append(self._prefix)
        return self._session

    def __exit__(self, *_) -> None:
        """Removes the prefix from the session's path stack on block exit.

        Args:
            *_: Exception type, value, and traceback (ignored).
        """
        if self._session._path_stack:
            self._session._path_stack.pop()