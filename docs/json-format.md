# JSON Export Format

When `--export FILE.json` is used, the output is a single JSON object with up
to three top-level keys.

## Schema

```
{
  "element_tree": { ... },
  "ocr_results":  [ ... ],
  "image_results": [ ... ]
}
```

`ocr_results` is present only when `--ocr` or `--find` was used.
`image_results` is present only when `--image` was used.

When `--dump` is used the file contains a flat JSON array of window objects
instead of the wrapped schema above.

---

## `element_tree`

A tree of nested element nodes. Each node has the same shape:

```json
{
  "name":          "Untitled - Notepad",
  "control_type":  "Window",
  "class_name":    "Notepad",
  "automation_id": "",
  "rectangle":     "(100, 200, 900, 700)",
  "is_visible":    true,
  "is_enabled":    true,
  "handle":        65842,
  "process_id":    1234,
  "framework_id":  "Win32",
  "depth":         0,
  "children": [
    {
      "name": "",
      "control_type": "MenuBar",
      "...": "..."
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `name` | string | Element label / window text |
| `control_type` | string | UIA control type (e.g. `Button`, `Edit`, `MenuItem`) |
| `class_name` | string | Win32 window class name |
| `automation_id` | string | UIA automation ID (stable across runs, preferred for scripting) |
| `rectangle` | string | Bounding box `"(left, top, right, bottom)"` in screen pixels |
| `is_visible` | bool | Whether the element is currently visible |
| `is_enabled` | bool | Whether the element accepts input |
| `handle` | int \| null | Win32 HWND handle (null for pure-UIA elements) |
| `process_id` | int | PID of the owning process |
| `framework_id` | string | Underlying framework (`Win32`, `WPF`, `WinForm`, …) |
| `depth` | int | Depth in the element tree (root = 0) |
| `children` | array | Child element nodes (same schema, recursive) |

---

## `ocr_results`

A flat array of text regions detected by EasyOCR:

```json
[
  {
    "text":       "Save",
    "confidence": 96.3,
    "rect": {
      "left":   412,
      "top":    310,
      "right":  463,
      "bottom": 328
    }
  }
]
```

| Field | Type | Description |
|---|---|---|
| `text` | string | The detected text string |
| `confidence` | float | EasyOCR confidence score, 0–100 |
| `rect` | object | Absolute screen bounding box in pixels |

---

## `image_results`

A flat array of template-match results from PyAutoGUI:

```json
[
  {
    "template":   "save_icon.png",
    "confidence": 0.9,
    "center":     { "x": 437, "y": 319 },
    "rect": {
      "left":   412,
      "top":    304,
      "right":  462,
      "bottom": 334
    }
  }
]
```

| Field | Type | Description |
|---|---|---|
| `template` | string | Path to the reference image that was matched |
| `confidence` | float | Match threshold used (0.0–1.0) |
| `center` | object | Center pixel `{x, y}` of the matched region |
| `rect` | object | Absolute screen bounding box in pixels |

---

## Loading the export

```python
import json

with open("dump.json", encoding="utf-8") as f:
    data = json.load(f)

tree          = data["element_tree"]
ocr_results   = data.get("ocr_results", [])
image_results = data.get("image_results", [])
```

Or use the helper:

```python
from gui_helper import load_export

data = load_export("dump.json")
```