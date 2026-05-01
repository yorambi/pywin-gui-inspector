from __future__ import annotations

import ctypes
import ctypes.wintypes
import time


class ReadinessChecker:
    """Waits until a UI element is ready for interaction.

    Uses the Windows cursor state to detect when the system is busy
    (e.g. showing a wait cursor), and polls an element's enabled and
    visible properties until it becomes interactive or a timeout expires.
    """

    _IDC_WAIT        = 32514
    _IDC_APPSTARTING = 32650

    @staticmethod
    def is_system_busy() -> bool:
        """Checks whether the Windows system cursor indicates a busy state.

        Queries the current cursor handle via ``GetCursorInfo`` and compares
        it against the standard wait (hourglass) and app-starting cursors.

        Returns:
            True if the active cursor is the wait or app-starting cursor,
            False otherwise or if the query fails.
        """
        try:
            class _CI(ctypes.Structure):
                _fields_ = [
                    ("cbSize",      ctypes.wintypes.DWORD),
                    ("flags",       ctypes.wintypes.DWORD),
                    ("hCursor",     ctypes.wintypes.HANDLE),
                    ("ptScreenPos", ctypes.wintypes.POINT),
                ]
            ci = _CI()
            ci.cbSize = ctypes.sizeof(_CI)
            ctypes.windll.user32.GetCursorInfo(ctypes.byref(ci))
            u32 = ctypes.windll.user32
            return ci.hCursor in (
                u32.LoadCursorW(None, ReadinessChecker._IDC_WAIT),
                u32.LoadCursorW(None, ReadinessChecker._IDC_APPSTARTING),
            )
        except Exception:
            return False

    @staticmethod
    def wait(element, timeout: float = 8.0, poll: float = 0.1) -> bool:
        """Blocks until the element is enabled, visible, and the system is not busy.

        Polls the element's ``is_enabled()`` and ``is_visible()`` methods and
        checks :meth:`is_system_busy` on each iteration until all three
        conditions are satisfied or the timeout elapses.

        Args:
            element: The pywinauto element wrapper to wait for.
            timeout: Maximum number of seconds to wait before giving up.
                Defaults to 8.0.
            poll: Seconds to sleep between each readiness check.
                Defaults to 0.1.

        Returns:
            True if the element became ready within *timeout* seconds,
            False if the deadline was exceeded.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if (element.is_enabled() and element.is_visible()
                        and not ReadinessChecker.is_system_busy()):
                    return True
            except Exception:
                pass
            time.sleep(poll)
        return False