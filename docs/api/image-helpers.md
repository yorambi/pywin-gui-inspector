# Image helper functions

Standalone functions for working with image template match results from a
`gui_detector.py --image` export.

```python
from gui_helper import find_image_result, image_center
```

Image results are stored in the `image_results` key of the JSON export. Each
result is a dict:

```python
{
    "template":   "save_icon.png",
    "confidence": 0.9,
    "center":     {"x": 437, "y": 319},
    "rect": {
        "left": 412, "top": 304,
        "right": 462, "bottom": 334
    }
}
```

---

## Functions

### `find_image_result(results, template="") → dict | None`

Return the first image result, optionally filtered by template filename.

```python
image_results = data["image_results"]

first = find_image_result(image_results)                    # any match
match = find_image_result(image_results, "save_icon.png")   # by filename
```

### `image_center(image_result) → tuple[int, int]`

Return the pre-computed center `(x, y)` of an image result dict.

```python
result = find_image_result(image_results, "save_icon.png")
if result:
    x, y = image_center(result)
    pyautogui.click(x, y)
```

---

## Capturing good template images

1. Take a screenshot of the target button with **Win + Shift + S**
2. Crop tightly to just the icon — avoid whitespace borders
3. Save as `.png` (not `.jpg` — JPEG compression changes pixels)
4. Capture at **100% zoom** — scaling breaks template matching
5. If the icon has hover/pressed states, capture each separately

If `confidence=0.9` misses the target, lower it:

```bash
python gui_detector.py --pid 1234 --image save_icon.png --confidence 0.8
```