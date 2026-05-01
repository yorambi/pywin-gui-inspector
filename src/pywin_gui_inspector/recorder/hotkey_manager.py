from __future__ import annotations

try:
    import keyboard as _kb
    _KB = True
except ImportError:
    _KB = False


class HotkeyManager:
    """Registers and unregisters global keyboard hotkeys.

    Wraps the ``keyboard`` library to provide a simple dictionary-based
    interface for binding hotkey strings to callback functions.  All keys
    are normalised to lower-case on registration.

    Attributes:
        _bindings: Mapping of lower-cased hotkey strings to their callback
            callables.
    """

    def __init__(self, bindings: dict[str, callable]) -> None:
        """Initialises the manager with a set of hotkey-to-callback bindings.

        Args:
            bindings: A dict mapping hotkey strings (e.g. ``"f7"``,
                ``"ctrl+s"``) to zero-argument callable objects that will
                be invoked when the hotkey is pressed.  Keys are
                lower-cased on storage.
        """
        self._bindings = {k.lower(): v for k, v in bindings.items()}

    def register(self) -> None:
        """Registers all configured hotkeys with the global keyboard hook.

        Prints a warning and returns without error if the ``keyboard``
        package is not installed.
        """
        if not _KB:
            print("[recorder] WARNING: pip install keyboard — hotkeys unavailable")
            return
        for key, cb in self._bindings.items():
            _kb.add_hotkey(key, cb)

    def unregister(self) -> None:
        """Removes all global keyboard hooks registered by this manager.

        Silently ignores errors and does nothing when the ``keyboard``
        package is not installed.
        """
        if _KB:
            try: _kb.unhook_all()
            except Exception: pass

    def describe(self) -> str:
        """Returns a formatted one-line summary of all registered hotkey bindings.

        Formats each binding as ``KEY = callback_name`` and joins them with
        triple-space separators.

        Returns:
            A single string listing every hotkey and its associated action
            name (e.g. ``"F7 = start_recording   F9 = stop_recording"``).
        """
        return "   ".join(
            f"{k.upper()} = {getattr(v, '__name__', str(v)).lstrip('_')}"
            for k, v in self._bindings.items()
        )