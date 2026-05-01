import pytest
from pywin_gui_inspector.recorder.script_exporter import ScriptExporter
from pywin_gui_inspector.recorder.events import ClickEvent, TypeEvent, HotkeyEvent


class TestPrimaryWindow:
    def test_picks_app_over_desktop(self):
        events = [
            ClickEvent("Desktop 1||Pane->Taskbar||Pane", "left"),
            ClickEvent("Calculator||Window->Seven||Button", "left"),
            ClickEvent("Calculator||Window->Plus||Button",  "left"),
        ]
        assert ScriptExporter.primary_window(events) == "Calculator"

    def test_skips_shell_windows(self):
        events = [
            ClickEvent("Desktop 1||Pane->Desktop||List", "left"),
            ClickEvent("Taskbar||Pane->Clock||Text",     "left"),
            ClickEvent("Notepad||Window->File||MenuItem", "left"),
        ]
        assert ScriptExporter.primary_window(events) == "Notepad"

    def test_most_frequent_wins(self):
        events = [
            ClickEvent("Chrome||Window->A||Button",   "left"),
            ClickEvent("Notepad||Window->B||Button",  "left"),
            ClickEvent("Notepad||Window->C||Button",  "left"),
        ]
        assert ScriptExporter.primary_window(events) == "Notepad"

    def test_empty_events(self):
        assert ScriptExporter.primary_window([]) == "..."

    def test_skips_own_app(self):
        events = [
            ClickEvent("GUI Recorder  [idle]||Window->x||Button", "left"),
            ClickEvent("Calc||Window->1||Button", "left"),
        ]
        assert ScriptExporter.primary_window(events) == "Calc"


class TestGenerate:
    def test_left_click(self):
        script = ScriptExporter.generate([ClickEvent("App||Window->OK||Button", "left")])
        assert "s.click('App||Window->OK||Button')" in script

    def test_right_click(self):
        script = ScriptExporter.generate([ClickEvent("App||Window->Item||ListItem", "right")])
        assert "s.right_click(" in script

    def test_set_text(self):
        script = ScriptExporter.generate([TypeEvent("App||Window->||Edit", "hello world")])
        assert "s.set_text(" in script
        assert "'hello world'" in script

    def test_send_keys_when_no_path(self):
        script = ScriptExporter.generate([TypeEvent("", "abc")])
        assert "s.send_keys(" in script

    def test_single_key_hotkey(self):
        script = ScriptExporter.generate([HotkeyEvent(keys=["enter"])])
        assert "s.press('enter')" in script

    def test_combo_hotkey(self):
        script = ScriptExporter.generate([HotkeyEvent(keys=["ctrl", "s"])])
        assert "s.hotkey('ctrl', 's')" in script

    def test_time_sleep_for_gap(self):
        e1 = ClickEvent("App||Window->A||Button", "left")
        e2 = ClickEvent("App||Window->B||Button", "left")
        e2.timestamp = e1.timestamp + 3.0
        script = ScriptExporter.generate([e1, e2])
        assert "time.sleep(3.0)" in script

    def test_no_sleep_for_small_gap(self):
        e1 = ClickEvent("App||Window->A||Button", "left")
        e2 = ClickEvent("App||Window->B||Button", "left")
        e2.timestamp = e1.timestamp + 0.5
        script = ScriptExporter.generate([e1, e2])
        assert "time.sleep" not in script

    def test_desktop_session_used(self):
        script = ScriptExporter.generate([ClickEvent("App||Window->OK||Button", "left")])
        assert "DesktopSession" in script
        # connect_application must only appear in the comment, not as the active assignment
        assert "s = DesktopSession()" in script

    def test_empty_events(self):
        script = ScriptExporter.generate([])
        assert "DesktopSession" in script