from __future__ import annotations

import queue
import threading
import tkinter as tk


class TkOverlay(threading.Thread):
    """Green border highlight and path tooltip rendered over the screen.

    Runs in a dedicated daemon thread; all commands are submitted through
    an internal queue to keep Tkinter calls on its own thread.  Displays
    four thin strips that form a rectangle around the hovered element, plus
    a small dark tooltip showing the element's path and short label.

    Attributes:
        BORDER: Width in pixels of the four highlight strips.
        COLOR: Hex colour string used for the highlight border.
    """

    BORDER = 3
    COLOR  = "#00CC44"

    def __init__(self) -> None:
        """Initialises the overlay thread and internal synchronisation primitives."""
        super().__init__(daemon=True, name="TkOverlay")
        self._q: queue.Queue = queue.Queue()
        self._ready          = threading.Event()

    def show(self, rect: tuple[int, int, int, int], path: str,
             label: str, cursor: tuple[int, int]) -> None:
        """Queues a command to display the highlight border and tooltip.

        Args:
            rect: Bounding rectangle of the element as ``(left, top, right,
                bottom)`` in screen coordinates.
            path: Full UIA path string shown in the tooltip body.
            label: Short human-readable label shown as the tooltip title.
            cursor: Current mouse cursor position as ``(x, y)`` used to
                position the tooltip near the pointer.
        """
        self._q.put(("show", (rect, path, label, cursor)))

    def hide(self) -> None:
        """Queues a command to hide both the highlight strips and the tooltip."""
        self._q.put(("hide", None))

    def stop(self) -> None:
        """Queues a quit command that will terminate the Tkinter main loop."""
        self._q.put(("quit", None))

    def wait_ready(self, timeout: float = 3.0) -> None:
        """Blocks until the Tkinter window has been created and is ready.

        Args:
            timeout: Maximum seconds to wait for the ready event.
                Defaults to 3.0.
        """
        self._ready.wait(timeout)

    def run(self) -> None:
        """Creates the Tkinter root, builds the overlay widgets, and starts the event loop.

        Called automatically when the thread is started.  Sets the ready
        event once the widgets are initialised, then enters the Tkinter
        main loop, polling the command queue every 50 ms.
        """
        self._root = tk.Tk()
        self._root.withdraw()
        self._strips = [self._make_strip() for _ in range(4)]

        self._tip = tk.Toplevel(self._root)
        self._tip.overrideredirect(True)
        self._tip.attributes("-topmost", True)
        self._tip.attributes("-alpha", 0.92)
        self._tip.configure(bg="#1a1a2e")
        self._lbl = tk.Label(
            self._tip, text="", bg="#1a1a2e", fg="#00ff88",
            font=("Consolas", 9), padx=8, pady=4, justify="left", wraplength=700,
        )
        self._lbl.pack()
        self._tip.withdraw()

        self._ready.set()
        self._root.after(50, self._flush)
        self._root.mainloop()

    def _make_strip(self) -> tk.Toplevel:
        """Creates a single borderless, transparent highlight-strip window.

        Returns:
            A withdrawn ``tk.Toplevel`` configured as a coloured overlay
            strip with no title bar or border.
        """
        w = tk.Toplevel(self._root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha", 0.85)
        w.configure(bg=self.COLOR)
        w.withdraw()
        return w

    def _flush(self) -> None:
        """Drains the command queue and applies pending show/hide/quit commands.

        Called repeatedly by ``root.after(50, ...)`` so that it runs on the
        Tkinter thread.  Reschedules itself unless a ``"quit"`` command is
        received.
        """
        try:
            while True:
                cmd, data = self._q.get_nowait()
                if cmd == "show":
                    rect, path, label, cursor = data
                    self._show_strips(rect)
                    self._show_tip(path, label, cursor)
                elif cmd == "hide":
                    self._hide_strips(); self._hide_tip()
                elif cmd == "quit":
                    self._hide_strips(); self._hide_tip()
                    self._root.quit()
                    return
        except queue.Empty:
            pass
        self._root.after(50, self._flush)

    def _show_strips(self, rect: tuple[int, int, int, int]) -> None:
        """Positions and reveals the four highlight strips around *rect*.

        Args:
            rect: The element bounding rectangle as ``(left, top, right,
                bottom)`` in screen coordinates.
        """
        l, t, r, b = rect
        w, h, bd = max(r - l, 1), max(b - t, 1), self.BORDER
        for strip, (x, y, sw, sh) in zip(self._strips, [
            (l,      t,      w,  bd),
            (l,      b - bd, w,  bd),
            (l,      t,      bd, h ),
            (r - bd, t,      bd, h ),
        ]):
            strip.geometry(f"{sw}x{sh}+{x}+{y}")
            strip.deiconify()

    def _hide_strips(self) -> None:
        """Withdraws all four highlight strips from the screen."""
        for s in self._strips:
            try: s.withdraw()
            except Exception: pass

    def _show_tip(self, path: str, label: str, cursor: tuple[int, int]) -> None:
        """Updates and positions the tooltip window near the cursor.

        Hides the tooltip when *path* is empty; otherwise updates the label
        text and positions the window so it stays within the screen bounds.

        Args:
            path: Full UIA path string to display in the tooltip body.
            label: Short label shown as the first line of the tooltip.
            cursor: Current mouse position ``(x, y)`` used to anchor the
                tooltip position.
        """
        if not path:
            self._hide_tip()
            return
        self._lbl.config(text=f"  {label}\n  {path}")
        self._tip.update_idletasks()
        sw = self._root.winfo_screenwidth()
        ww = self._tip.winfo_reqwidth()
        self._tip.geometry(f"+{min(cursor[0]+18, sw-ww-8)}+{cursor[1]+26}")
        self._tip.deiconify()

    def _hide_tip(self) -> None:
        """Withdraws the tooltip window from the screen."""
        try: self._tip.withdraw()
        except Exception: pass