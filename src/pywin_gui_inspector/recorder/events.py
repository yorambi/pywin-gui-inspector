from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto


class State(Enum):
    """Represents the recording state of the TrayApp.

    Attributes:
        IDLE: The recorder is not currently capturing events.
        RECORDING: The recorder is actively capturing mouse and keyboard events.
    """

    IDLE      = auto()
    RECORDING = auto()


@dataclass
class ClickEvent:
    """Represents a single recorded mouse-click interaction.

    Attributes:
        path: The UIA path string of the element that was clicked.
        button: The mouse button used; either ``"left"`` or ``"right"``.
        timestamp: Unix timestamp (seconds) at the moment the click was
            recorded. Populated automatically on creation.
    """

    path:      str
    button:    str          # "left" | "right"
    timestamp: float = field(default_factory=time.time)


@dataclass
class TypeEvent:
    """Represents a sequence of typed characters recorded at a given element.

    Attributes:
        path: The UIA path string of the element that had keyboard focus
            when the text was typed.
        text: The accumulated string of characters typed in sequence.
        timestamp: Unix timestamp (seconds) at the start of the typing
            sequence. Populated automatically on creation.
    """

    path:      str
    text:      str
    timestamp: float = field(default_factory=time.time)


@dataclass
class HotkeyEvent:
    """Represents a modifier-key combination or special key press that was recorded.

    Attributes:
        keys: Ordered list of key name strings making up the hotkey
            (e.g. ``["ctrl", "shift", "s"]`` or ``["enter"]``).
        timestamp: Unix timestamp (seconds) at the moment the hotkey was
            detected. Populated automatically on creation.
    """

    keys:      list[str]
    timestamp: float = field(default_factory=time.time)