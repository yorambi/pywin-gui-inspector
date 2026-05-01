"""detector — window inspection, OCR, image matching, and the CLI."""

from pywin_gui_inspector.detector.elevation   import ElevationManager
from pywin_gui_inspector.detector.ocr_processor import OCRProcessor
from pywin_gui_inspector.detector.image_matcher import ImageMatcher
from pywin_gui_inspector.detector.inspector    import WindowInspector, ChangeMonitor
from pywin_gui_inspector.detector.renderer     import Renderer

__all__ = [
    "ElevationManager",
    "OCRProcessor",
    "ImageMatcher",
    "WindowInspector",
    "ChangeMonitor",
    "Renderer",
]