from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from pywin_gui_inspector.recorder.events         import State
from pywin_gui_inspector.recorder.overlay        import TkOverlay
from pywin_gui_inspector.recorder.capture        import Recorder
from pywin_gui_inspector.recorder.script_exporter import ScriptExporter
from pywin_gui_inspector.recorder.tray_icon      import TrayIconFactory
from pywin_gui_inspector.recorder.hotkey_manager import HotkeyManager

try:
    import pystray
    _TRAY = True
except ImportError:
    _TRAY = False
    print("[recorder] pip install pystray — tray icon unavailable, using CLI mode\n")


class TrayApp:
    """System-tray recorder application.

    Manages a simple two-state machine: IDLE (green icon) and RECORDING
    (red icon).  Exposes start, stop, and cancel actions through both a
    pystray tray icon menu and configurable global hotkeys.  When recording
    stops, the captured events are exported to a Python script file.

    Attributes:
        output: Path where the generated replay script will be written.
        start_hotkey: Lower-cased key name that starts recording.
        stop_hotkey: Lower-cased key name that stops and saves recording.
        exit_hotkey: Lower-cased key name that exits the application.
    """

    def __init__(
        self,
        output:       str = "recorded.py",
        start_hotkey: str = "f7",
        stop_hotkey:  str = "f9",
        exit_hotkey:  str = "f10",
    ) -> None:
        """Initialises the tray application with output path and hotkey configuration.

        Creates the overlay, recorder, and hotkey manager but does not
        start any threads or register hotkeys yet; call :meth:`run` for that.

        Args:
            output: File path for the generated Python replay script.
                Defaults to ``"recorded.py"``.
            start_hotkey: Global hotkey string that triggers recording to
                start. Defaults to ``"f7"``.
            stop_hotkey: Global hotkey string that triggers recording to
                stop and save. Defaults to ``"f9"``.
            exit_hotkey: Global hotkey string that exits the application.
                Defaults to ``"f10"``.
        """
        self.output       = Path(output)
        self.start_hotkey = start_hotkey.lower()
        self.stop_hotkey  = stop_hotkey.lower()
        self.exit_hotkey  = exit_hotkey.lower()

        self._state    = State.IDLE
        self._icon     = None
        self._last_out: Optional[Path] = None

        self._overlay  = TkOverlay()
        self._recorder = Recorder(
            self._overlay,
            ignore_keys={start_hotkey, stop_hotkey, exit_hotkey, "escape"},
        )
        self._hotkeys  = HotkeyManager({
            self.start_hotkey: self._start_recording,
            self.stop_hotkey:  self._stop_recording,
            self.exit_hotkey:  self._on_exit,
            "escape":          lambda: self._stop_recording(cancel=True),
        })

    # ── State transitions ─────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        """Transitions from IDLE to RECORDING and activates the recorder.

        No-ops if already recording.  Updates the tray icon to the red
        recording state and refreshes the tray menu.
        """
        if self._state is State.RECORDING:
            return
        self._state = State.RECORDING
        self._recorder.begin()
        if self._icon:
            self._icon.icon  = TrayIconFactory.make(recording=True)
            self._icon.title = "GUI Recorder  [● RECORDING]"
            self._update_menu()
        print(f"[recorder] ● Started  (press {self.stop_hotkey.upper()} to stop)")

    def _stop_recording(self, *, cancel: bool = False) -> None:
        """Transitions from RECORDING to IDLE and optionally saves the script.

        No-ops if already idle.  When *cancel* is False, retrieves the
        captured events, generates a Python script, writes it to
        :attr:`output`, and optionally shows a tray notification.  When
        *cancel* is True, discards all events without writing a file.

        Args:
            cancel: If True, discards all recorded events without saving.
                Defaults to False (save the script).
        """
        if self._state is State.IDLE:
            return
        self._state = State.IDLE

        if cancel:
            self._recorder.cancel()
            print("\n[recorder] Cancelled — no file written.")
        else:
            events = self._recorder.end()
            print(f"\n[recorder] ■ Stopped.  {len(events)} event(s).")
            if events:
                script = ScriptExporter.generate(events)
                self.output.write_text(script, encoding="utf-8")
                print(f"[recorder] Script → {self.output}")
                self._last_out = self.output
                if self._icon:
                    self._icon.notify(f"Saved → {self.output.name}  ({len(events)} events)",
                                      "GUI Recorder")
            else:
                print("[recorder] Nothing recorded.")

        if self._icon:
            self._icon.icon  = TrayIconFactory.make(recording=False)
            self._icon.title = "GUI Recorder  [idle]"
            self._update_menu()

    # ── Tray callbacks ────────────────────────────────────────────────────────

    def _on_start(self, *_) -> None:
        """Tray menu callback that starts recording.

        Args:
            *_: Unused arguments passed by pystray.
        """
        self._start_recording()

    def _on_stop(self, *_) -> None:
        """Tray menu callback that stops recording and saves the script.

        Args:
            *_: Unused arguments passed by pystray.
        """
        self._stop_recording()

    def _on_cancel(self, *_) -> None:
        """Tray menu callback that stops recording and discards captured events.

        Args:
            *_: Unused arguments passed by pystray.
        """
        self._stop_recording(cancel=True)

    def _on_open_script(self, *_) -> None:
        """Tray menu callback that opens the last saved script in Notepad.

        Opens the most recently written output file (or the configured
        default path) in Notepad.  Shows a notification if no file exists.

        Args:
            *_: Unused arguments passed by pystray.
        """
        path = self._last_out or self.output
        if path.exists():
            subprocess.Popen(["notepad.exe", str(path)])
        elif self._icon:
            self._icon.notify("No script saved yet.", "GUI Recorder")

    def _on_exit(self, *_) -> None:
        """Tray menu callback that stops recording (if active) and exits the app.

        Args:
            *_: Unused arguments passed by pystray.
        """
        if self._state is State.RECORDING:
            self._stop_recording()
        self._overlay.stop()
        if self._icon:
            self._icon.stop()

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> "pystray.Menu":
        """Builds and returns the tray icon context menu for the current state.

        Enables/disables Start, Stop, and Cancel items based on whether the
        recorder is currently active.

        Returns:
            A ``pystray.Menu`` instance configured for the current
            :class:`~pywin_gui_inspector.recorder.events.State`.
        """
        rec = self._state is State.RECORDING
        return pystray.Menu(
            pystray.MenuItem(f"▶  Start  ({self.start_hotkey.upper()})", self._on_start, enabled=not rec, default=not rec),
            pystray.MenuItem(f"■  Stop   ({self.stop_hotkey.upper()})",  self._on_stop,  enabled=rec,     default=rec),
            pystray.MenuItem("✕  Cancel (discard)", self._on_cancel, enabled=rec),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📄  Open last script", self._on_open_script),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Exit  ({self.exit_hotkey.upper()})", self._on_exit),
        )

    def _update_menu(self) -> None:
        """Rebuilds and applies the tray icon menu for the current recorder state."""
        if self._icon:
            self._icon.menu = self._build_menu()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Starts the overlay, registers hotkeys, and enters the tray icon event loop.

        When pystray is available, creates a system tray icon and blocks in
        its event loop.  When pystray is not installed, falls back to a
        simple ``time.sleep`` loop that can be interrupted with Ctrl-C.
        """
        self._overlay.start()
        self._overlay.wait_ready()
        self._hotkeys.register()
        print(f"[recorder] Hotkeys: {self._hotkeys.describe()}")

        if _TRAY:
            self._icon = pystray.Icon(
                "gui_recorder",
                TrayIconFactory.make(recording=False),
                "GUI Recorder  [idle]",
                self._build_menu(),
            )
            print(f"[recorder] Tray active.  Press {self.start_hotkey.upper()} to begin.\n")
            self._icon.run()
        else:
            print(f"[recorder] Press {self.start_hotkey.upper()} to start.\n")
            try:
                while True: time.sleep(0.5)
            except KeyboardInterrupt:
                self._stop_recording()