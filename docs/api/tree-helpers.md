# Tree helper functions

Standalone functions that operate on the element tree dict without needing a
`GUISession`. Useful for bulk processing, filtering, and analysis.

```python
from gui_helper import (
    load_export,
    flatten_tree,
    find_by_name,
    find_by_automation_id,
    find_by_control_type,
    find_all,
    element_rect,
    element_center,
    print_flat,
)
```

---

## Loading exports

### `load_export(path) → dict`

Load a `gui_detector.py` JSON export and return the raw dict.

```python
data = load_export("dump.json")
tree          = data["element_tree"]
ocr_results   = data.get("ocr_results", [])
image_results = data.get("image_results", [])
```

---

## Tree traversal

### `flatten_tree(node) → list[dict]`

Return a flat depth-first list of every element node in the tree.

```python
nodes = flatten_tree(data["element_tree"])
print(f"Total elements: {len(nodes)}")
```

### `find_by_name(node, name, exact=False, enabled_only=True, visible_only=True) → dict | None`

Depth-first search for the first element whose name matches.

```python
btn = find_by_name(tree, "Save")                  # substring, case-insensitive
btn = find_by_name(tree, "Save", exact=True)       # exact match
btn = find_by_name(tree, "Save", visible_only=False)  # include hidden elements
```

### `find_by_automation_id(node, auto_id) → dict | None`

Find the first element whose `automation_id` exactly matches `auto_id`.

```python
node = find_by_automation_id(tree, "btn_ok")
```

### `find_by_control_type(node, control_type) → dict | None`

Find the first element matching a control type string (case-insensitive).

```python
first_edit = find_by_control_type(tree, "Edit")
```

### `find_all(node, name="", control_type="", enabled_only=True, visible_only=True) → list[dict]`

Collect every element matching **all** supplied filters. Omit a parameter to
skip that filter.

```python
buttons    = find_all(tree, control_type="Button")
edits      = find_all(tree, control_type="Edit")
save_btns  = find_all(tree, name="Save", control_type="Button")
all_items  = find_all(tree, control_type="MenuItem", enabled_only=False)
```

---

## Coordinates

### `element_rect(node) → tuple[int, int, int, int]`

Return `(left, top, right, bottom)` screen coordinates of an element node.

```python
l, t, r, b = element_rect(node)
width  = r - l
height = b - t
```

### `element_center(node) → tuple[int, int]`

Return the center `(x, y)` pixel of an element node.

```python
x, y = element_center(node)
```

---

## Printing

### `print_flat(node, enabled_only=False)`

Print a flat readable list of all elements with name, type, automation ID, and
bounding rectangle.

```python
print_flat(tree)
print_flat(tree, enabled_only=True)  # skip disabled elements
```

```
  [Window]   'Untitled - Notepad'  []  (100, 200, 900, 700)
  [MenuBar]  '<no name>'           []  (100, 200, 900, 221)
  [MenuItem] 'File'            [Item 1]  (100, 200, 140, 221)
  [Edit]     'Text Editor'         []  (100, 221, 900, 700)
```

---

## Common patterns

**Filter with list comprehensions:**

```python
nodes = flatten_tree(tree)

# Elements with automation IDs (most reliable to interact with)
reliable = [n for n in nodes if n.get("automation_id")]

# Disabled elements (useful for auditing)
disabled = [n for n in nodes if not n.get("is_enabled", True)]

# All buttons by size
large_buttons = [
    n for n in nodes
    if n.get("control_type") == "Button"
    and n.get("is_visible")
    and (element_rect(n)[2] - element_rect(n)[0]) > 80
]
```