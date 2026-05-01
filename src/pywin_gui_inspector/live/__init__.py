"""live — live UIA automation without a JSON snapshot."""

from pywin_gui_inspector.live.path_syntax    import PathEntry, PathSyntax
from pywin_gui_inspector.live.element_search import ElementSearch
from pywin_gui_inspector.live.cache          import TTLCache
from pywin_gui_inspector.live.readiness      import ReadinessChecker
from pywin_gui_inspector.live.grid_layout    import GridLayout
from pywin_gui_inspector.live.ocr_wrapper    import OCRWrapper, OCREngine
from pywin_gui_inspector.live.ui_path        import UIPath
from pywin_gui_inspector.live.app_factory    import ApplicationFactory
from pywin_gui_inspector.live.session        import LiveSession, DesktopSession


def connect_application(pid=None, title=None, title_re=None) -> LiveSession:
    return ApplicationFactory.connect(pid=pid, title=title, title_re=title_re)


def start_application(executable: str, *args: str, timeout: float = 15.0) -> LiveSession:
    return ApplicationFactory.start(executable, *args, timeout=timeout)


def wait_is_ready(element, timeout: float = 8.0, poll: float = 0.1) -> bool:
    return ReadinessChecker.wait(element, timeout, poll)


def get_sorted_region(elements, min_width=0, min_height=0, line_tolerance=None):
    return GridLayout.sort(elements, min_width, min_height, line_tolerance)


__all__ = [
    "PathEntry", "PathSyntax",
    "ElementSearch",
    "TTLCache",
    "ReadinessChecker",
    "GridLayout",
    "OCRWrapper", "OCREngine",
    "UIPath",
    "ApplicationFactory",
    "LiveSession", "DesktopSession",
    "connect_application", "start_application",
    "wait_is_ready", "get_sorted_region",
]