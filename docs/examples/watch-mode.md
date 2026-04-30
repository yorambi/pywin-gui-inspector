# 08 — Watch mode

**Script:** `ExampleScripts/08_watch_mode.py`

Polls a live window at a configurable interval and reacts when specific
elements appear or disappear — useful for waiting on progress bars, detecting
error dialogs, or monitoring live dashboards.

## Part A — Shell watcher

Print element diffs to the console:

```bash
python gui_detector.py --watch 1234 --interval 0.5
```

```
[*] Watching PID 1234 every 0.5s  (Ctrl-C to stop)

  [*] Baseline: 18 element(s)
  [=] No change
  [+] New elements:     ['Save As', 'File name:', 'Cancel']
  [-] Removed elements: ['Save As', 'File name:', 'Cancel']
```

## Part B — Python polling loop

```bash
python gui_detector.py --pid 1234 --export baseline.json
python ExampleScripts/08_watch_mode.py
```

```python
from gui_helper import GUISession
from pywinauto import Application
import time

s = GUISession("baseline.json")
pid = s._pid

WAIT_FOR = "OK"       # element to watch for
TIMEOUT  = 60.0       # give up after 60 s

def snapshot(pid):
    app  = Application(backend="uia").connect(process=pid)
    wins = app.windows()
    if not wins:
        return set()
    def walk(node):
        return {node.window_text()} | {t for c in node.children() for t in walk(c)}
    return walk(wins[0])

previous = snapshot(pid)
start    = time.time()

while time.time() - start < TIMEOUT:
    time.sleep(1.0)
    current = snapshot(pid)
    added   = current - previous

    if WAIT_FOR in added:
        print(f"[!] '{WAIT_FOR}' appeared — clicking it")
        s.smart_click(WAIT_FOR)
        break

    previous = current
```

## Use cases

- Wait for a progress dialog to complete, then click OK
- Detect when an error dialog appears and dismiss it
- React to a login form appearing after a page load
- Monitor for new list items in a live dashboard