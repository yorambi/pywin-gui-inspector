import sys
from pathlib import Path

# Mock Windows-only imports so autodoc works on Linux (ReadTheDocs)
from unittest.mock import MagicMock
for mod in [
    "pywinauto", "pywinauto.application", "pywinauto.controls.uiawrapper",
    "pywinauto.findwindows", "pywinauto.Desktop", "pyautogui",
    "easyocr", "PIL", "PIL.ImageGrab", "cv2", "ctypes", "ctypes.windll",
]:
    sys.modules.setdefault(mod, MagicMock())

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Project info ──────────────────────────────────────────────────────────────
project   = "pywin-gui-inspector"
copyright = "2024, Yoram Samoray"
author    = "Yoram Samoray"
release   = "1.0"

# ── Extensions ────────────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

myst_enable_extensions = ["colon_fence", "deflist", "fieldlist"]
myst_heading_anchors = 3

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# ── Templates & static ────────────────────────────────────────────────────────
templates_path   = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_static_path = ["_static"]

# ── HTML output ───────────────────────────────────────────────────────────────
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}
html_show_sourcelink = True

# ── Autodoc ───────────────────────────────────────────────────────────────────
autodoc_member_order  = "bysource"
autodoc_typehints     = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring  = True