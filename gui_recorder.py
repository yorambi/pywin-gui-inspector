"""
gui_recorder.py
===============
Background GUI recorder with system tray icon.

Sits in the Windows system tray and waits for you to start a recording
session.  Hover over any element to see a green highlight and its UIA path.
Every click and keystroke is captured and turned into a gui_live.py script
when you stop.

Usage
-----
    python gui_recorder.py
    python gui_recorder.py -o login_flow.py
    python gui_recorder.py --start F6 --stop F9

Controls
--------
    Tray icon  → right-click for menu, double-click to start / stop
    F7         start recording  (--start to change)
    F9         stop  recording  (--stop  to change)
    Esc        cancel recording (discard events)

Requirements
------------
    pip install pywinauto pyautogui keyboard pystray Pillow
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

try:
    from pywinauto import Desktop
    import pyautogui
except ImportError as exc:
    sys.exit(f"[recorder] pip install pywinauto pyautogui\n{exc}")

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    _TRAY = True
except ImportError:
    _TRAY = False
    print("[recorder] pystray / Pillow not found — running in CLI mode.\n"
          "           pip install pystray Pillow for tray support.\n")

try:
    import keyboard as _kb
    _KB = True
except ImportError:
    _KB = False
    print("[recorder] keyboard not found — pip install keyboard\n")

import os
_OWN_PID = os.getpid()


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class State(Enum):
    IDLE      = auto()
    RECORDING = auto()


# ─────────────────────────────────────────────────────────────────────────────
# Win32 helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cursor_pos() -> tuple[int, int]:
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def _key_down(vk: int) -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

_VK_LBUTTON = 0x01
_VK_RBUTTON = 0x02


# ─────────────────────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClickEvent:
    path:      str
    button:    str          # "left" | "right"
    timestamp: float = field(default_factory=time.time)

@dataclass
class TypeEvent:
    path:      str
    text:      str
    timestamp: float = field(default_factory=time.time)

@dataclass
class HotkeyEvent:
    keys:      list[str]
    timestamp: float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────────────────────────────
# Element path builder
# ─────────────────────────────────────────────────────────────────────────────

_SKIP_UNNAMED = {"Pane", "Group", "Custom", "Thumb", "ScrollBar", "TitleBar", "Header"}

def build_path(element) -> tuple[str, str]:
    """
    Walk up the UIA tree from *element* to its top-level window.

    Returns ``(full_path, short_label)`` where:
      full_path  —  ``"Window||Window->Button||Button"``
      short_label — last path segment only, shown in the tooltip
    """
    parts: list[str] = []
    current = element

    for _ in range(20):
        try:
            name = (current.window_text() or "").strip()
            ctrl = (current.element_info.control_type or "").strip()
        except Exception:
            break
        if not name and ctrl in _SKIP_UNNAMED:
            try:
                current = current.parent()
                continue
            except Exception:
                break
        if name or ctrl:
            parts.append(f"{name}||{ctrl}" if (name and ctrl) else (name or f"||{ctrl}"))
        if ctrl in ("Window", "Dialog") and name:
            break
        try:
            parent = current.parent()
            if parent is None or parent is current:
                break
            current = parent
        except Exception:
            break

    parts.reverse()
    return "->".join(parts), (parts[-1] if parts else "")


# ─────────────────────────────────────────────────────────────────────────────
# Tkinter overlay (runs in its own thread)
# ─────────────────────────────────────────────────────────────────────────────

class TkOverlay(threading.Thread):
    """
    Dedicated thread for the Tkinter overlay (green border + path tooltip).

    Receives commands via an internal queue so other threads can drive it
    without touching Tkinter directly.
    """

    BORDER = 3
    COLOR  = "#00CC44"

    def __init__(self) -> None:
        super().__init__(daemon=True, name="TkOverlay")
        self._q: queue.Queue = queue.Queue()
        self._ready = threading.Event()

    # ── Public (called from any thread) ──────────────────────────────────────

    def show(self, rect: tuple[int, int, int, int], path: str, label: str,
             cursor: tuple[int, int]) -> None:
        self._q.put(("show", (rect, path, label, cursor)))

    def hide(self) -> None:
        self._q.put(("hide", None))

    def stop(self) -> None:
        self._q.put(("quit", None))

    def wait_ready(self, timeout: float = 3.0) -> None:
        self._ready.wait(timeout)

    # ── Thread body ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self._root = tk.Tk()
        self._root.withdraw()

        # Highlight strips (4 thin windows = top/bottom/left/right border)
        self._strips = [self._make_strip() for _ in range(4)]

        # Tooltip window
        self._tip_win = tk.Toplevel(self._root)
        self._tip_win.overrideredirect(True)
        self._tip_win.attributes("-topmost", True)
        self._tip_win.attributes("-alpha", 0.92)
        self._tip_win.configure(bg="#1a1a2e")
        self._tip_lbl = tk.Label(
            self._tip_win, text="", bg="#1a1a2e", fg="#00ff88",
            font=("Consolas", 9), padx=8, pady=4, justify="left", wraplength=700,
        )
        self._tip_lbl.pack()
        self._tip_win.withdraw()

        self._ready.set()
        self._root.after(50, self._flush)
        self._root.mainloop()

    def _make_strip(self) -> tk.Toplevel:
        w = tk.Toplevel(self._root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha", 0.85)
        w.configure(bg=self.COLOR)
        w.withdraw()
        return w

    def _flush(self) -> None:
        try:
            while True:
                cmd, data = self._q.get_nowait()
                if cmd == "show":
                    rect, path, label, cursor = data
                    self._show_strips(rect)
                    self._show_tip(path, label, cursor)
                elif cmd == "hide":
                    self._hide_strips()
                    self._hide_tip()
                elif cmd == "quit":
                    self._hide_strips()
                    self._hide_tip()
                    self._root.quit()
                    return
        except queue.Empty:
            pass
        self._root.after(50, self._flush)

    def _show_strips(self, rect: tuple[int, int, int, int]) -> None:
        l, t, r, b = rect
        w, h = max(r - l, 1), max(b - t, 1)
        bd   = self.BORDER
        for strip, (x, y, sw, sh) in zip(self._strips, [
            (l,      t,      w,  bd),
            (l,      b - bd, w,  bd),
            (l,      t,      bd, h ),
            (r - bd, t,      bd, h ),
        ]):
            strip.geometry(f"{sw}x{sh}+{x}+{y}")
            strip.deiconify()

    def _hide_strips(self) -> None:
        for s in self._strips:
            try: s.withdraw()
            except Exception: pass

    def _show_tip(self, path: str, label: str, cursor: tuple[int, int]) -> None:
        if not path:
            self._hide_tip()
            return
        self._tip_lbl.config(text=f"  {label}\n  {path}")
        self._tip_win.update_idletasks()
        sw = self._root.winfo_screenwidth()
        ww = self._tip_win.winfo_reqwidth()
        tx = min(cursor[0] + 18, sw - ww - 8)
        ty = cursor[1] + 26
        self._tip_win.geometry(f"+{tx}+{ty}")
        self._tip_win.deiconify()

    def _hide_tip(self) -> None:
        try: self._tip_win.withdraw()
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# Recorder (event capture)
# ─────────────────────────────────────────────────────────────────────────────

class Recorder:
    """Captures clicks and keystrokes and drives the overlay while recording."""

    def __init__(self, overlay: TkOverlay, ignore_keys: set[str] | None = None) -> None:
        self._overlay     = overlay
        self._events:  list = []
        self._lock        = threading.Lock()
        self._active      = False
        self._cur_path    = ""
        self._cur_lbl     = ""
        self._cur_pid: int = 0
        # Keys to silently drop (start/stop hotkeys must not appear in the script)
        self._ignore_keys = {k.lower() for k in (ignore_keys or set())}

    # ── Start / stop ──────────────────────────────────────────────────────────

    def begin(self) -> None:
        with self._lock:
            self._events.clear()
        self._active = True
        threading.Thread(target=self._track_loop, daemon=True).start()
        threading.Thread(target=self._click_loop, daemon=True).start()
        if _KB:
            _kb.on_press(self._on_key)
        print("\n[recorder] Recording …  (hover to highlight, click/type to capture)\n")

    def end(self) -> list:
        self._active = False
        self._overlay.hide()
        if _KB:
            try:
                _kb.unhook_all()
            except Exception:
                pass
        with self._lock:
            return list(self._events)

    def cancel(self) -> None:
        self._active = False
        self._overlay.hide()
        if _KB:
            try:
                _kb.unhook_all()
            except Exception:
                pass
        with self._lock:
            self._events.clear()

    # ── Element tracking ──────────────────────────────────────────────────────

    def _track_loop(self) -> None:
        desktop = Desktop(backend="uia")
        prev_pt = (-9999, -9999)
        stable  = 0

        while self._active:
            time.sleep(0.08)
            pt = _cursor_pos()

            if pt == prev_pt:
                stable += 1
                if stable < 2:
                    continue
            else:
                prev_pt = pt
                stable  = 0
                continue

            try:
                elem         = desktop.from_point(*pt)
                path, label  = build_path(elem)
                rect         = elem.rectangle()
                self._cur_path = path
                self._cur_lbl  = label
                self._cur_pid  = elem.element_info.process_id
                self._overlay.show(
                    (rect.left, rect.top, rect.right, rect.bottom),
                    path, label, pt,
                )
            except Exception:
                self._cur_path = ""
                self._cur_lbl  = ""
                self._cur_pid  = 0
                self._overlay.hide()

    # ── Click monitoring ──────────────────────────────────────────────────────

    def _click_loop(self) -> None:
        lp = rp = False
        while self._active:
            time.sleep(0.01)
            ld = _key_down(_VK_LBUTTON)
            rd = _key_down(_VK_RBUTTON)
            if ld and not lp:
                path = self._cur_path
                # Skip clicks on our own overlay windows
                if path and self._cur_pid != _OWN_PID:
                    self._record(ClickEvent(path=path, button="left"))
            if rd and not rp:
                path = self._cur_path
                if path and self._cur_pid != _OWN_PID:
                    self._record(ClickEvent(path=path, button="right"))
            lp, rp = ld, rd

    # ── Keyboard ─────────────────────────────────────────────────────────────

    _MODS = {"ctrl", "shift", "alt", "win"}

    def _on_key(self, event) -> None:
        if not self._active:
            return
        name = (event.name or "").lower()

        # Drop start/stop/cancel hotkeys — they control the recorder, not the app
        if name in self._ignore_keys:
            return

        mods = [m for m in ("ctrl", "shift", "alt") if _kb.is_pressed(m)]
        if mods and name not in self._MODS and len(name) <= 20:
            self._record(HotkeyEvent(keys=mods + [name]))
            return

        if len(name) == 1:
            path = self._cur_path
            with self._lock:
                if (self._events
                        and isinstance(self._events[-1], TypeEvent)
                        and self._events[-1].path == path):
                    self._events[-1].text += name
                    return
            self._record(TypeEvent(path=path, text=name))

        elif name in ("enter", "tab", "backspace", "delete", "space",
                      "up", "down", "left", "right",
                      *[f"f{i}" for i in range(1, 13)]):
            self._record(HotkeyEvent(keys=[name]))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _record(self, event) -> None:
        with self._lock:
            self._events.append(event)
        kind   = type(event).__name__.replace("Event", "")
        detail = (getattr(event, "path",  None) or
                  " + ".join(getattr(event, "keys", [])) or
                  getattr(event, "text",  ""))
        if len(detail) > 72:
            detail = detail[:69] + "..."
        print(f"  [REC] {kind:<12}  {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# Script generator
# ─────────────────────────────────────────────────────────────────────────────

def _primary_window(events: list) -> str:
    """Return the most-frequently-seen top-level window name across all events."""
    from collections import Counter
    names: list[str] = []
    for ev in events:
        path = getattr(ev, "path", "")
        if path:
            name = path.split("->")[0].split("||")[0].strip()
            if name:
                names.append(name)
    if not names:
        return "..."
    return Counter(names).most_common(1)[0][0]


def generate_script(events: list) -> str:
    title = _primary_window(events)
    lines = [
        '"""',
        "Auto-generated by gui_recorder.py",
        '"""',
        "import time",
        "from gui_live import connect_application",
        "",
        f"s = connect_application(title={title!r})",
        "s.focus()",
        "",
    ]
    prev_ts: Optional[float] = None
    for ev in events:
        if prev_ts is not None:
            gap = ev.timestamp - prev_ts
            if 1.5 < gap < 30:
                lines.append(f"time.sleep({gap:.1f})")
        prev_ts = ev.timestamp

        if isinstance(ev, ClickEvent):
            m = "right_click" if ev.button == "right" else "click"
            lines.append(f"s.{m}({ev.path!r})")
        elif isinstance(ev, TypeEvent):
            if ev.path:
                lines.append(f"s.set_text({ev.path!r}, {ev.text!r})")
            else:
                lines.append(f"s.send_keys({ev.text!r})")
        elif isinstance(ev, HotkeyEvent):
            if len(ev.keys) == 1:
                lines.append(f"s.press({ev.keys[0]!r})")
            else:
                keys = ", ".join(repr(k) for k in ev.keys)
                lines.append(f"s.hotkey({keys})")

    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Tray icon images
# ─────────────────────────────────────────────────────────────────────────────

def _make_icon_image(recording: bool = False) -> "Image.Image":
    """
    Programmatically draw the tray icon.

    Idle     : dark background, green "R" letter
    Recording: dark background, red circle pulse + white "R"
    """
    size  = 64
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    if recording:
        # Outer red ring
        draw.ellipse([2, 2, size - 3, size - 3], outline=(220, 50, 50), width=4)
        # Inner red fill
        draw.ellipse([10, 10, size - 11, size - 11], fill=(200, 40, 40))
        txt_color = (255, 255, 255)
    else:
        # Solid dark circle with green border
        draw.ellipse([2, 2, size - 3, size - 3], fill=(30, 30, 50), outline=(0, 200, 80), width=3)
        txt_color = (0, 200, 80)

    # Draw "R" letter in centre
    try:
        font = ImageFont.truetype("consolab.ttf", 30)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "R", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), "R", fill=txt_color, font=font)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# Tray application
# ─────────────────────────────────────────────────────────────────────────────

class TrayApp:
    """
    Manages the system tray icon, hotkeys, and the recording state machine.

    States
    ------
    IDLE      — sitting in tray, green icon, overlay hidden
    RECORDING — tracking cursor, red icon, overlay active
    """

    def __init__(
        self,
        output:       str = "recorded.py",
        start_hotkey: str = "f7",
        stop_hotkey:  str = "f9",
    ) -> None:
        self.output       = Path(output)
        self.start_hotkey = start_hotkey.lower()
        self.stop_hotkey  = stop_hotkey.lower()

        self._state    = State.IDLE
        self._icon     = None
        self._last_out: Optional[Path] = None

        self._overlay  = TkOverlay()
        self._recorder = Recorder(
            self._overlay,
            ignore_keys={start_hotkey, stop_hotkey, "escape"},
        )

    # ── State transitions ─────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        if self._state is State.RECORDING:
            return
        self._state = State.RECORDING
        self._recorder.begin()
        if self._icon:
            self._icon.icon  = _make_icon_image(recording=True)
            self._icon.title = "GUI Recorder  [● RECORDING]"
            self._update_menu()
        print(f"[recorder] ● Recording started  "
              f"(press {self.stop_hotkey.upper()} or use tray to stop)")

    def _stop_recording(self, *, cancel: bool = False) -> None:
        if self._state is State.IDLE:
            return
        self._state = State.IDLE

        if cancel:
            self._recorder.cancel()
            print("\n[recorder] Recording cancelled — no file written.")
        else:
            events = self._recorder.end()
            print(f"\n[recorder] ■ Stopped.  {len(events)} event(s) captured.")
            if events:
                out = self._save(events)
                print(f"[recorder] Script → {out}")
                self._last_out = out
                if self._icon:
                    self._icon.notify(
                        f"Saved → {out.name}  ({len(events)} events)",
                        "GUI Recorder",
                    )
            else:
                print("[recorder] Nothing recorded.")

        if self._icon:
            self._icon.icon  = _make_icon_image(recording=False)
            self._icon.title = "GUI Recorder  [idle]"
            self._update_menu()

    def _save(self, events: list) -> Path:
        script = generate_script(events)
        self.output.write_text(script, encoding="utf-8")
        return self.output

    # ── Tray menu callbacks ───────────────────────────────────────────────────

    def _on_start(self, *_) -> None:
        self._start_recording()

    def _on_stop(self, *_) -> None:
        self._stop_recording()

    def _on_cancel(self, *_) -> None:
        self._stop_recording(cancel=True)

    def _on_open_script(self, *_) -> None:
        path = self._last_out or self.output
        if path.exists():
            subprocess.Popen(["notepad.exe", str(path)])
        else:
            if self._icon:
                self._icon.notify("No script saved yet.", "GUI Recorder")

    def _on_exit(self, *_) -> None:
        if self._state is State.RECORDING:
            self._stop_recording()
        self._overlay.stop()
        if self._icon:
            self._icon.stop()

    # ── Menu builder ──────────────────────────────────────────────────────────

    def _build_menu(self) -> "pystray.Menu":
        recording = self._state is State.RECORDING
        return pystray.Menu(
            pystray.MenuItem(
                f"▶  Start Recording  ({self.start_hotkey.upper()})",
                self._on_start,
                enabled=not recording,
                default=not recording,
            ),
            pystray.MenuItem(
                f"■  Stop Recording   ({self.stop_hotkey.upper()})",
                self._on_stop,
                enabled=recording,
                default=recording,
            ),
            pystray.MenuItem(
                "✕  Cancel (discard)",
                self._on_cancel,
                enabled=recording,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📄  Open last script", self._on_open_script),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit),
        )

    def _update_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()

    # ── Hotkeys ───────────────────────────────────────────────────────────────

    def _register_hotkeys(self) -> None:
        if not _KB:
            print(f"[recorder] WARNING: hotkeys unavailable (pip install keyboard)")
            return
        _kb.add_hotkey(self.start_hotkey, self._start_recording)
        _kb.add_hotkey(self.stop_hotkey,  self._stop_recording)
        _kb.add_hotkey("escape",          lambda: self._stop_recording(cancel=True))
        print(f"[recorder] Hotkeys: "
              f"{self.start_hotkey.upper()} = start   "
              f"{self.stop_hotkey.upper()} = stop   "
              f"ESC = cancel")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        # Start the Tkinter overlay thread
        self._overlay.start()
        self._overlay.wait_ready()

        # Register global hotkeys
        self._register_hotkeys()

        if _TRAY:
            self._icon = pystray.Icon(
                name  = "gui_recorder",
                icon  = _make_icon_image(recording=False),
                title = "GUI Recorder  [idle]",
                menu  = self._build_menu(),
            )
            print("[recorder] Tray icon active.  Right-click it or press "
                  f"{self.start_hotkey.upper()} to begin.\n")
            self._icon.run()          # blocks until _on_exit calls icon.stop()
        else:
            # CLI fallback — just wait for hotkeys
            print(f"[recorder] Tray unavailable.  Press {self.start_hotkey.upper()} to start.\n")
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self._stop_recording()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Record GUI actions → gui_live.py script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python gui_recorder.py\n"
            "  python gui_recorder.py -o login_flow.py\n"
            "  python gui_recorder.py --start F6 --stop F8\n"
        ),
    )
    p.add_argument("-o", "--output", default="recorded.py", metavar="FILE",
                   help="Output script path (default: recorded.py)")
    p.add_argument("--start",        default="f7",           metavar="KEY",
                   help="Start-recording hotkey (default: f7)")
    p.add_argument("--stop",         default="f9",           metavar="KEY",
                   help="Stop-recording  hotkey (default: f9)")
    args = p.parse_args()

    app = TrayApp(
        output       = args.output,
        start_hotkey = args.start.lower(),
        stop_hotkey  = args.stop.lower(),
    )
    app.run()


if __name__ == "__main__":
    main()