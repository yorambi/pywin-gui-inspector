from __future__ import annotations

import threading
import time

from pywinauto import Desktop
from pywin_gui_inspector.recorder.events      import ClickEvent, TypeEvent, HotkeyEvent
from pywin_gui_inspector.recorder.path_builder import PathBuilder
from pywin_gui_inspector.recorder.overlay     import TkOverlay
from pywin_gui_inspector.recorder.win32_mouse import Win32Mouse

try:
    import keyboard as _kb
    _KB = True
except ImportError:
    _KB = False


class Recorder:
    """Captures mouse clicks and keyboard input while highlighting the current element.

    Runs two background daemon threads: one to track the cursor and update
    the overlay highlight, and one to detect mouse-button press edges.
    Keyboard events are captured via a ``keyboard`` library hook.  All
    recorded events are appended to an internal thread-safe list.

    Attributes:
        _MODS: Set of key names that are treated as modifier keys and never
            stored as standalone events.
    """

    _MODS: frozenset[str] = frozenset({"ctrl", "shift", "alt", "win"})

    def __init__(self, overlay: TkOverlay, ignore_keys: set[str] | None = None) -> None:
        """Initialises the recorder with an overlay and an optional key ignore list.

        Args:
            overlay: The :class:`~pywin_gui_inspector.recorder.overlay.TkOverlay`
                instance used to highlight the hovered element and show path
                tooltips.
            ignore_keys: Set of key-name strings (lower-case) that will not
                generate :class:`~pywin_gui_inspector.recorder.events.HotkeyEvent`
                or :class:`~pywin_gui_inspector.recorder.events.TypeEvent`
                entries (e.g. the hotkeys used to start/stop the recorder).
                Defaults to an empty set when ``None``.
        """
        self._overlay     = overlay
        self._events:  list = []
        self._lock        = threading.Lock()
        self._active      = False
        self._cur_path    = ""
        self._cur_pid     = 0
        self._ignore_keys = {k.lower() for k in (ignore_keys or set())}

    def begin(self) -> None:
        """Starts recording by launching the tracking and click-detection threads.

        Clears any previously recorded events, sets the active flag, starts
        the cursor-tracking and click-detection daemon threads, and installs
        the keyboard hook if available.
        """
        with self._lock:
            self._events.clear()
        self._active = True
        threading.Thread(target=self._track_loop, daemon=True).start()
        threading.Thread(target=self._click_loop, daemon=True).start()
        if _KB:
            _kb.on_press(self._on_key)
        print("\n[recorder] Recording …  hover to highlight, click/type to capture\n")

    def end(self) -> list:
        """Stops recording and returns the list of captured events.

        Deactivates the recorder, hides the overlay, and unregisters all
        keyboard hooks.

        Returns:
            A copy of the recorded event list containing
            :class:`~pywin_gui_inspector.recorder.events.ClickEvent`,
            :class:`~pywin_gui_inspector.recorder.events.TypeEvent`, and
            :class:`~pywin_gui_inspector.recorder.events.HotkeyEvent`
            objects in capture order.
        """
        self._active = False
        self._overlay.hide()
        if _KB:
            try: _kb.unhook_all()
            except Exception: pass
        with self._lock:
            return list(self._events)

    def cancel(self) -> None:
        """Stops recording and discards all captured events.

        Deactivates the recorder, hides the overlay, unregisters keyboard
        hooks, and clears the internal event list.
        """
        self._active = False
        self._overlay.hide()
        if _KB:
            try: _kb.unhook_all()
            except Exception: pass
        with self._lock:
            self._events.clear()

    def _track_loop(self) -> None:
        """Background thread that tracks cursor movement and updates the overlay.

        Polls the cursor position every 80 ms and, once the cursor has been
        stable for two consecutive polls, queries the UIA element under the
        pointer, builds its path, and sends a show command to the overlay.
        Hides the overlay and resets state if any step fails.
        """
        desktop = Desktop(backend="uia")
        prev_pt, stable = (-9999, -9999), 0
        while self._active:
            time.sleep(0.08)
            pt = Win32Mouse.cursor_pos()
            if pt == prev_pt:
                stable += 1
                if stable < 2: continue
            else:
                prev_pt, stable = pt, 0
                continue
            try:
                elem           = desktop.from_point(*pt)
                path, label    = PathBuilder.build(elem)
                rect           = elem.rectangle()
                self._cur_path = path
                self._cur_pid  = elem.element_info.process_id
                self._overlay.show((rect.left, rect.top, rect.right, rect.bottom), path, label, pt)
            except Exception:
                self._cur_path = ""
                self._cur_pid  = 0
                self._overlay.hide()

    def _click_loop(self) -> None:
        """Background thread that detects mouse-button press edges and records clicks.

        Polls the left and right button states every 10 ms, detecting
        transitions from released to pressed.  Ignores clicks on the
        recorder's own process window.
        """
        lp = rp = False
        while self._active:
            time.sleep(0.01)
            ld = Win32Mouse.key_down(Win32Mouse.VK_LBUTTON)
            rd = Win32Mouse.key_down(Win32Mouse.VK_RBUTTON)
            if ld and not lp and self._cur_path and self._cur_pid != Win32Mouse._OWN_PID:
                self._record(ClickEvent(path=self._cur_path, button="left"))
            if rd and not rp and self._cur_path and self._cur_pid != Win32Mouse._OWN_PID:
                self._record(ClickEvent(path=self._cur_path, button="right"))
            lp, rp = ld, rd

    def _on_key(self, event) -> None:
        """Keyboard hook callback that classifies and records key-press events.

        Ignores keys in the ignore set and pure modifier key presses.
        Modifier+key combinations are recorded as
        :class:`~pywin_gui_inspector.recorder.events.HotkeyEvent` objects.
        Printable single characters are appended to the last
        :class:`~pywin_gui_inspector.recorder.events.TypeEvent` if it targets
        the same element; otherwise a new ``TypeEvent`` is created.  Named
        navigation/function keys are recorded as single-key ``HotkeyEvent``
        objects.

        Args:
            event: The ``keyboard`` library key event object with a ``name``
                attribute.
        """
        if not self._active:
            return
        name = (event.name or "").lower()
        if name in self._ignore_keys:
            return
        mods = [m for m in ("ctrl", "shift", "alt") if _kb.is_pressed(m)]
        if mods and name not in self._MODS and len(name) <= 20:
            self._record(HotkeyEvent(keys=mods + [name]))
            return
        if len(name) == 1:
            path = self._cur_path
            with self._lock:
                if (self._events and isinstance(self._events[-1], TypeEvent)
                        and self._events[-1].path == path):
                    self._events[-1].text += name
                    return
            self._record(TypeEvent(path=path, text=name))
        elif name in ("enter", "tab", "backspace", "delete", "space",
                      "up", "down", "left", "right",
                      *[f"f{i}" for i in range(1, 13)]):
            self._record(HotkeyEvent(keys=[name]))

    def _record(self, event) -> None:
        """Appends an event to the captured list and logs a summary line.

        Thread-safe; acquires the internal lock before appending.

        Args:
            event: A recorder event object
                (:class:`~pywin_gui_inspector.recorder.events.ClickEvent`,
                :class:`~pywin_gui_inspector.recorder.events.TypeEvent`, or
                :class:`~pywin_gui_inspector.recorder.events.HotkeyEvent`)
                to store.
        """
        with self._lock:
            self._events.append(event)
        kind   = type(event).__name__.replace("Event", "")
        detail = getattr(event, "path", None) or " + ".join(getattr(event, "keys", [])) or getattr(event, "text", "")
        print(f"  [REC] {kind:<12}  {detail[:72]}")