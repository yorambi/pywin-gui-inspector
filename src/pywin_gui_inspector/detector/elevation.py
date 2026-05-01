from __future__ import annotations

import ctypes
import os
import sys


class ElevationManager:
    """Manages Windows UAC privilege elevation for the current process."""

    @staticmethod
    def is_admin() -> bool:
        """Check whether the current process is running with Administrator rights.

        Calls the Win32 ``IsUserAnAdmin`` shell API.  Returns ``False`` on any
        error rather than raising, so callers can use it as a safe guard.

        Returns:
            True if the process has Administrator privileges, False otherwise.
        """
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    @staticmethod
    def elevate() -> bool:
        """Re-launch the current script with UAC elevation via ``ShellExecuteW``.

        Reconstructs the original command line and invokes it again under the
        ``runas`` verb, which triggers the UAC prompt.  The new elevated process
        receives the same arguments as the current one.

        Returns:
            True if the elevated child process was successfully handed off
            (the caller should ``sys.exit(0)`` after this).
            False if the user declined the UAC prompt or elevation is unavailable.
        """
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{script}" {params}', None, 1,
            )
            return ret > 32
        except Exception:
            return False

    @classmethod
    def require(cls) -> None:
        """Attempt to gain Administrator privileges, continuing gracefully if denied.

        If the process is already elevated, returns immediately with no action.
        Otherwise requests UAC elevation and exits this process once the elevated
        child is running.  If the user declines or elevation fails, prints a
        warning and continues execution without admin rights so that non-protected
        applications can still be inspected.
        """
        if cls.is_admin():
            return
        print("[*] Requesting administrator privileges…")
        if cls.elevate():
            sys.exit(0)
        print("[!] Elevation declined — continuing without admin rights.\n"
              "    Some protected processes may not be accessible.")