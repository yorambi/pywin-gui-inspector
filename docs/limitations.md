# Limitations

## Platform

**Windows only.** Pywinauto uses the Windows UIA and Win32 accessibility APIs,
which have no equivalent on macOS or Linux. The image template and OCR features
also assume a Windows screen coordinate system.

---

## Accessibility API coverage

| App type | Element tree quality | Notes |
|---|---|---|
| Win32 / MFC | Excellent | Full automation ID and name coverage |
| WinForms / WPF | Excellent | .NET accessibility APIs are rich |
| Qt | Good | Requires Qt Accessibility enabled |
| Electron / CEF | Sparse | Few automation IDs; use `--depth 3` |
| Java Swing | Varies | Depends on JAB (Java Access Bridge) |
| UWP | Good | Modern Windows apps work well |
| Games / DirectX | None | Element tree unavailable; use `--image` |

---

## Protected processes

Windows prevents non-elevated processes from inspecting elevated ones. This
affects:

- Task Manager
- Installers (UAC-elevated)
- System utilities running as SYSTEM

`gui_detector.py` requests elevation automatically. If declined, it continues
without admin rights — inspection of protected targets will fail silently.

---

## OCR performance

EasyOCR is accurate but slow on CPU. On a typical laptop without a GPU:

- Full window scan (`--ocr`): 2–5 seconds
- Targeted search (`--find TEXT`): same (whole image is always processed)

**Mitigation:** Use `--find` with a short keyword rather than full `--ocr`
dumps. A CUDA-capable GPU reduces scan time to under 1 second.

Model weights (~100 MB) are downloaded on first use and cached in
`~/.EasyOCR/model/`.

---

## Image template matching

Template matching is sensitive to:

- **Zoom / DPI changes** — capture the reference image at the exact screen
  scale you will run the search at
- **Rendering changes** — hover, pressed, focused states change pixel values
- **Themes** — a dark-mode screenshot won't match a light-mode template

Lower `--confidence` (e.g. `0.8`) if the default `0.9` misses valid matches.

---

## `gui_helper.py` live actions

Methods with `live=True` (e.g. `click_by_name("OK", live=True)`) require the
target process to still be running and accessible when the script executes.
They will raise `RuntimeError` if:

- The process has exited
- No `process_id` was present in the export
- The window is no longer found

---

## Dynamic UIs

`--watch` uses element name sets for diffing. In rapidly changing UIs
(video players, games, live dashboards) this can produce very noisy output.
Reduce noise with `--depth 3` or `--interval 2.0`.

---

## Large element trees

Very deep or wide UI trees (e.g. a browser's full DOM exposed via accessibility)
can be slow to walk and produce huge JSON exports. Use `--depth 3` to limit
recursion and focus on the top layers of the hierarchy.