"""recorder — system-tray GUI recorder."""

from pywin_gui_inspector.recorder.events         import State, ClickEvent, TypeEvent, HotkeyEvent
from pywin_gui_inspector.recorder.win32_mouse    import Win32Mouse
from pywin_gui_inspector.recorder.path_builder   import PathBuilder
from pywin_gui_inspector.recorder.overlay        import TkOverlay
from pywin_gui_inspector.recorder.script_exporter import ScriptExporter
from pywin_gui_inspector.recorder.tray_icon      import TrayIconFactory
from pywin_gui_inspector.recorder.hotkey_manager import HotkeyManager
from pywin_gui_inspector.recorder.capture        import Recorder
from pywin_gui_inspector.recorder.tray_app       import TrayApp

__all__ = [
    "State", "ClickEvent", "TypeEvent", "HotkeyEvent",
    "Win32Mouse", "PathBuilder", "TkOverlay",
    "ScriptExporter", "TrayIconFactory", "HotkeyManager",
    "Recorder", "TrayApp",
]