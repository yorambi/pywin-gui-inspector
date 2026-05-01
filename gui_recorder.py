"""Entry point — delegates to pywin_gui_inspector.recorder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pywin_gui_inspector.recorder.tray_app import TrayApp
import argparse


def main() -> None:
    p = argparse.ArgumentParser(description="Record GUI actions → script")
    p.add_argument("-o", "--output", default="recorded.py", metavar="FILE")
    p.add_argument("--start",        default="f7",   metavar="KEY")
    p.add_argument("--stop",         default="f9",   metavar="KEY")
    p.add_argument("--exit",         default="f10",  metavar="KEY")
    args = p.parse_args()

    TrayApp(
        output       = args.output,
        start_hotkey = args.start.lower(),
        stop_hotkey  = args.stop.lower(),
        exit_hotkey  = args.exit.lower(),
    ).run()


if __name__ == "__main__":
    main()