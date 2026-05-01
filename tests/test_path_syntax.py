import pytest
from pywin_gui_inspector.live.path_syntax import PathEntry, PathSyntax


class TestParse:
    def test_simple_name_and_type(self):
        entries, grid, offset = PathSyntax.parse("OK||Button")
        assert len(entries) == 1
        assert entries[0].name == "OK"
        assert entries[0].ctrl == "Button"
        assert grid is None and offset is None

    def test_type_only(self):
        entries, _, _ = PathSyntax.parse("||Edit")
        assert entries[0].name == ""
        assert entries[0].ctrl == "Edit"

    def test_hierarchy(self):
        entries, _, _ = PathSyntax.parse("Window||Window->OK||Button")
        assert len(entries) == 2
        assert entries[0].name == "Window" and entries[0].ctrl == "Window"
        assert entries[1].name == "OK"     and entries[1].ctrl == "Button"

    def test_wildcard(self):
        entries, _, _ = PathSyntax.parse("*->OK||Button")
        assert entries[0].wildcard is True
        assert entries[1].name == "OK"

    def test_regex(self):
        entries, _, _ = PathSyntax.parse("RegEx: .*Save.*||Button")
        assert entries[0].regex is True
        assert entries[0].name == ".*Save.*"

    def test_grid_suffix(self):
        _, grid, offset = PathSyntax.parse("||Button#[1,2]")
        assert grid == (1, 2)
        assert offset is None

    def test_offset_suffix(self):
        _, grid, offset = PathSyntax.parse("||Slider%(0.8,0.0)")
        assert grid is None
        assert offset == (0.8, 0.0)

    def test_grid_and_offset(self):
        _, grid, offset = PathSyntax.parse("||Button#[1,0]%(0.5,0.0)")
        assert grid == (1, 0)
        assert offset == (0.5, 0.0)

    def test_negative_offset(self):
        _, _, offset = PathSyntax.parse("||Slider%(-1.0, 0.0)")
        assert offset == (-1.0, 0.0)


class _MockElement:
    def __init__(self, name: str, ctrl: str):
        self._name = name
        class _EI:
            def __init__(self, c): self.control_type = c
        self.element_info = _EI(ctrl)
    def window_text(self): return self._name


class TestMatch:
    def test_name_and_ctrl_match(self):
        el    = _MockElement("OK", "Button")
        entry = PathEntry(name="OK", ctrl="Button")
        assert PathSyntax.match(el, entry) is True

    def test_name_substring(self):
        el    = _MockElement("OK Button", "Button")
        entry = PathEntry(name="OK", ctrl="Button")
        assert PathSyntax.match(el, entry) is True

    def test_wrong_ctrl_type(self):
        el    = _MockElement("OK", "Edit")
        entry = PathEntry(name="OK", ctrl="Button")
        assert PathSyntax.match(el, entry) is False

    def test_wildcard_matches_anything(self):
        el    = _MockElement("Anything", "AnyType")
        entry = PathEntry(name="", ctrl="", wildcard=True)
        assert PathSyntax.match(el, entry) is True

    def test_regex_match(self):
        el    = _MockElement("Save As", "Button")
        entry = PathEntry(name=".*Save.*", ctrl="Button", regex=True)
        assert PathSyntax.match(el, entry) is True

    def test_regex_no_match(self):
        el    = _MockElement("Cancel", "Button")
        entry = PathEntry(name=".*Save.*", ctrl="Button", regex=True)
        assert PathSyntax.match(el, entry) is False

    def test_case_insensitive_name(self):
        el    = _MockElement("Save", "Button")
        entry = PathEntry(name="save", ctrl="Button")
        assert PathSyntax.match(el, entry) is True

    def test_case_insensitive_ctrl(self):
        el    = _MockElement("OK", "BUTTON")
        entry = PathEntry(name="OK", ctrl="button")
        assert PathSyntax.match(el, entry) is True