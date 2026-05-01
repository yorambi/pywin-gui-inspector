"""Entry point — delegates to pywin_gui_inspector.detector."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pywin_gui_inspector.detector.elevation   import ElevationManager
from pywin_gui_inspector.detector.ocr_processor import OCRProcessor
from pywin_gui_inspector.detector.image_matcher import ImageMatcher
from pywin_gui_inspector.detector.inspector    import WindowInspector, ChangeMonitor
from pywin_gui_inspector.detector.renderer     import Renderer

import argparse, json
from typing import Optional


def main() -> None:
    ElevationManager.require()

    p = argparse.ArgumentParser(
        description="Detect & inspect GUI objects using Pywinauto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--pid",   type=int)
    g.add_argument("--title", type=str)
    g.add_argument("--dump",  action="store_true")
    g.add_argument("--watch", type=int, metavar="PID")
    p.add_argument("--depth",      type=int,   default=8)
    p.add_argument("--export",     type=str,   metavar="FILE.json")
    p.add_argument("--interval",   type=float, default=1.0)
    p.add_argument("--ocr",        action="store_true")
    p.add_argument("--find",       type=str,   metavar="TEXT")
    p.add_argument("--image",      type=str,   metavar="FILE.png")
    p.add_argument("--confidence", type=float, default=0.9)
    args = p.parse_args()

    inspector = WindowInspector(max_depth=args.depth)

    if args.dump:
        windows = inspector.list_windows()
        Renderer.windows(windows)
        if args.export:
            with open(args.export, "w", encoding="utf-8") as f:
                json.dump(windows, f, indent=2, default=str)
        return

    if args.watch:
        ChangeMonitor.watch(args.watch, interval=args.interval, max_depth=args.depth)
        return

    root: Optional[dict] = None
    if args.pid:        root = inspector.inspect_pid(args.pid)
    elif args.title:    root = inspector.inspect_title(args.title)
    else:               root = inspector.interactive()

    if root is None:
        sys.exit(1)

    Renderer.tree(root)
    target_pid = args.pid or root.get("process_id")

    ocr_results: list[dict] = []
    if (args.ocr or args.find) and target_pid:
        OCRProcessor.require_deps()
        if args.find:
            ocr_results = OCRProcessor.find_text(target_pid, args.find)
            Renderer.ocr_results(ocr_results, query=args.find)
        else:
            ocr_results = OCRProcessor.scan_all(target_pid)
            Renderer.ocr_results(ocr_results)

    image_results: list[dict] = []
    if args.image:
        ImageMatcher.require_deps()
        image_results = ImageMatcher.find(args.image, confidence=args.confidence)
        Renderer.image_results(image_results, args.image)

    if args.export:
        data: dict = {"element_tree": root}
        if ocr_results:    data["ocr_results"]   = ocr_results
        if image_results:  data["image_results"]  = image_results
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\n[+] Exported → {args.export}")


if __name__ == "__main__":
    main()