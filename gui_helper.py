"""Entry point — re-exports pywin_gui_inspector.helper for backwards compatibility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pywin_gui_inspector.helper import (  # noqa: F401  (public re-exports)
    GUISession, ScriptWriter,
    RectHelper, TreeSearch, OCRSearch, ImageSearch,
)
from pywin_gui_inspector.helper.tree_search    import TreeSearch as _TS
from pywin_gui_inspector.helper.search_helpers import OCRSearch as _OS, ImageSearch as _IS

import json
from pathlib import Path as _Path

# Module-level aliases kept for scripts that do `from gui_helper import find_by_name` etc.
def load_export(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

find_by_name          = _TS.by_name
find_by_automation_id = _TS.by_auto_id
find_by_control_type  = _TS.by_control_type
find_all              = _TS.find_all
flatten_tree          = _TS.flatten
element_rect          = _TS.rect
element_center        = _TS.center
print_flat            = _TS.print_flat
find_ocr              = _OS.find
find_all_ocr          = _OS.find_all
ocr_center            = _OS.center
find_image_result     = _IS.find
image_center          = _IS.center


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gui_helper.py <export.json>")
        sys.exit(1)
    session = GUISession(sys.argv[1])
    session.print_summary()