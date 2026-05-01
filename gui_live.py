"""Entry point — re-exports pywin_gui_inspector.live for backwards compatibility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pywin_gui_inspector.live import (  # noqa: F401  (public re-exports)
    LiveSession, DesktopSession,
    PathEntry, PathSyntax,
    ElementSearch, TTLCache,
    ReadinessChecker, GridLayout,
    OCRWrapper, OCREngine,
    UIPath, ApplicationFactory,
    connect_application, start_application,
    wait_is_ready, get_sorted_region,
)