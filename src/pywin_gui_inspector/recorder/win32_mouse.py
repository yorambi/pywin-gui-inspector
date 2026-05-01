from __future__ import annotations

import ctypes
import ctypes.wintypes
import os


class Win32Mouse:
    """Low-level Windows cursor and mouse-button helpers.

    Wraps Win32 API calls to read the current cursor position and query
    the instantaneous state of mouse buttons without relying on a message
    loop.

    Attributes:
        VK_LBUTTON: Virtual-key code for the left mouse button (0x01).
        VK_RBUTTON: Virtual-key code for the right mouse button (0x02).
        _OWN_PID: Process ID of the current process, used to filter out
            clicks on the recorder's own windows.
    """

    VK_LBUTTON = 0x01
    VK_RBUTTON = 0x02
    _OWN_PID   = os.getpid()

    @staticmethod
    def cursor_pos() -> tuple[int, int]:
        """Returns the current screen coordinates of the mouse cursor.

        Calls the Win32 ``GetCursorPos`` API to obtain the cursor position
        in screen pixels.

        Returns:
            A ``(x, y)`` tuple of the cursor's horizontal and vertical
            screen coordinates.
        """
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def key_down(vk: int) -> bool:
        """Checks whether the given virtual-key is currently held down.

        Uses ``GetAsyncKeyState`` to sample the key state asynchronously,
        independent of the message queue.

        Args:
            vk: The virtual-key code to query (e.g. ``Win32Mouse.VK_LBUTTON``).

        Returns:
            True if the key is currently pressed, False otherwise.
        """
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)