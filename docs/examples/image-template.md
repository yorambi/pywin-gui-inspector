# 04 — Image template search

**Script:** `ExampleScripts/04_image_template_search.py`

Uses PyAutoGUI template matching to find and click buttons that have no text
and no automation ID — toolbar icons, custom widgets, game UI elements.

## Prerequisites

1. Capture a `.png` screenshot of the icon you want to click (cropped tightly)
2. Export the window:

```bash
python gui_detector.py --title "MyApp" --image save_icon.png --export myapp.json
```

## Run

```bash
python ExampleScripts/04_image_template_search.py
```

## What it demonstrates

```python
from gui_helper import GUISession, find_image_result, image_center

s = GUISession("myapp.json")

# Click by template filename
s.click_image("save_icon.png")

# Click any match regardless of template
s.click_image()

# Access raw match data
result = find_image_result(s.image_results, "save_icon.png")
if result:
    x, y = image_center(result)
    print(f"Found at center=({x},{y})")
```

## Tips for reliable matching

- Capture at **100% zoom** — scaling breaks the match
- Use **PNG**, not JPEG (compression changes pixels)
- **Crop tightly** — extra whitespace reduces confidence
- Lower `--confidence` if the default `0.9` misses: try `0.8`
- Capture hover/pressed states separately if the icon changes appearance