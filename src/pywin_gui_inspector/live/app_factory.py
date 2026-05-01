from __future__ import annotations

import re
import subprocess
import time
from typing import TYPE_CHECKING

from pywinauto import Application, Desktop

if TYPE_CHECKING:
    from pywin_gui_inspector.live.session import LiveSession


class ApplicationFactory:
    """Factory methods that create LiveSession instances.

    Provides two entry points for obtaining a
    :class:`~pywin_gui_inspector.live.session.LiveSession`: connecting to an
    already-running process via :meth:`connect`, or launching a new executable
    and waiting for its window to appear via :meth:`start`.
    """

    @staticmethod
    def connect(pid=None, title=None, title_re=None) -> "LiveSession":
        """Connects to a running application and returns a LiveSession for it.

        Exactly one of *pid*, *title*, or *title_re* must be provided.
        When *title* is given it is wrapped in a ``.*...*`` regex for a
        flexible partial match.

        Args:
            pid: The OS process ID of the running application. Takes
                priority over *title* and *title_re* when provided.
            title: A plain-text substring of the window title to match.
                Converted internally to a regex via ``re.escape``.
            title_re: A regular expression string matched against the full
                window title.

        Returns:
            A :class:`~pywin_gui_inspector.live.session.LiveSession` wrapping
            the connected pywinauto ``Application``.

        Raises:
            ValueError: If none of *pid*, *title*, or *title_re* is provided.
        """
        from pywin_gui_inspector.live.session import LiveSession
        if pid:
            app = Application(backend="uia").connect(process=pid)
        elif title_re:
            app = Application(backend="uia").connect(title_re=title_re)
        elif title:
            app = Application(backend="uia").connect(title_re=f".*{re.escape(title)}.*")
        else:
            raise ValueError("Provide pid, title, or title_re.")
        return LiveSession(app)

    @staticmethod
    def start(executable: str, *args: str, timeout: float = 15.0) -> "LiveSession":
        """Launches an executable and waits for its first window to appear.

        Records all window handles present on the Desktop before launching,
        then polls until a new handle appears, indicating the application has
        opened a window.

        Args:
            executable: Full path or name of the executable to launch.
            *args: Additional command-line arguments forwarded to the process.
            timeout: Maximum seconds to wait for a new window to appear
                before raising. Defaults to 15.0.

        Returns:
            A :class:`~pywin_gui_inspector.live.session.LiveSession` wrapping
            the newly appeared window.

        Raises:
            TimeoutError: If no new window appears within *timeout* seconds
                after the process is launched.
        """
        from pywin_gui_inspector.live.session import LiveSession
        desktop = Desktop(backend="uia")
        before  = {w.handle for w in desktop.windows()}
        subprocess.Popen([executable, *args])

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            new = {w.handle for w in desktop.windows()} - before
            if new:
                return LiveSession(Application(backend="uia").connect(handle=next(iter(new))))

        raise TimeoutError(f"No window appeared within {timeout}s after launching {executable!r}")