"""
pywin_gui_inspector
===================
Windows GUI inspection, automation, and recording toolkit.

Main public API::

    from pywin_gui_inspector import GUISession, LiveSession, DesktopSession
    from pywin_gui_inspector import connect_application, start_application
"""

from pywin_gui_inspector.helper.session       import GUISession
from pywin_gui_inspector.helper.script_writer import ScriptWriter
from pywin_gui_inspector.live.session         import LiveSession, DesktopSession
from pywin_gui_inspector.live.app_factory     import ApplicationFactory

# Convenience wrappers exposed at the top level
from pywin_gui_inspector.live import connect_application, start_application

__version__ = "1.0.0"

__all__ = [
    "GUISession",
    "ScriptWriter",
    "LiveSession",
    "DesktopSession",
    "ApplicationFactory",
    "connect_application",
    "start_application",
]