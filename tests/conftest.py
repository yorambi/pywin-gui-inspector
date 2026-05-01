import sys
from pathlib import Path

# Add src/ to path so tests can import pywin_gui_inspector without installing it
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))