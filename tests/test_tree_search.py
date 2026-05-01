import pytest
from pywin_gui_inspector.helper.tree_search import TreeSearch

TREE = {
    "name": "Open File", "control_type": "Dialog",
    "automation_id": "dlg1", "is_enabled": True, "is_visible": True,
    "rectangle": "(0, 0, 500, 400)",
    "children": [
        {
            "name": "File name:", "control_type": "Edit",
            "automation_id": "edit_filename",
            "is_enabled": True, "is_visible": True,
            "rectangle": "(50, 100, 300, 130)", "children": [],
        },
        {
            "name": "Save", "control_type": "Button",
            "automation_id": "btn_save",
            "is_enabled": True, "is_visible": True,
            "rectangle": "(100, 200, 160, 230)", "children": [],
        },
        {
            "name": "Cancel", "control_type": "Button",
            "automation_id": "btn_cancel",
            "is_enabled": True, "is_visible": True,
            "rectangle": "(200, 200, 265, 230)", "children": [],
        },
        {
            "name": "Hidden button", "control_type": "Button",
            "automation_id": "btn_hidden",
            "is_enabled": True, "is_visible": False,
            "rectangle": "(0, 0, 1, 1)", "children": [],
        },
    ],
}


class TestByName:
    def test_finds_exact_substring(self):
        assert TreeSearch.by_name(TREE, "Save")["name"] in ("Save", "Cancel")

    def test_case_insensitive(self):
        assert TreeSearch.by_name(TREE, "save") is not None

    def test_exact_match(self):
        assert TreeSearch.by_name(TREE, "Save", exact=True)["name"] == "Save"
        assert TreeSearch.by_name(TREE, "Sav",  exact=True) is None

    def test_not_found(self):
        assert TreeSearch.by_name(TREE, "Nonexistent") is None

    def test_skips_hidden_by_default(self):
        assert TreeSearch.by_name(TREE, "Hidden button") is None

    def test_includes_hidden_when_requested(self):
        assert TreeSearch.by_name(TREE, "Hidden button", visible_only=False) is not None


class TestByAutoId:
    def test_found(self):
        assert TreeSearch.by_auto_id(TREE, "btn_save")["name"] == "Save"

    def test_not_found(self):
        assert TreeSearch.by_auto_id(TREE, "no_such_id") is None


class TestByControlType:
    def test_returns_first_match(self):
        result = TreeSearch.by_control_type(TREE, "Button")
        assert result["control_type"] == "Button"

    def test_case_insensitive(self):
        assert TreeSearch.by_control_type(TREE, "button") is not None


class TestFindAll:
    def test_all_visible_buttons(self):
        buttons = TreeSearch.find_all(TREE, control_type="Button")
        assert len(buttons) == 2
        assert all(b["control_type"] == "Button" for b in buttons)

    def test_name_and_type_filter(self):
        results = TreeSearch.find_all(TREE, name="Cancel", control_type="Button")
        assert len(results) == 1
        assert results[0]["name"] == "Cancel"

    def test_returns_empty_when_no_match(self):
        assert TreeSearch.find_all(TREE, name="Nonexistent") == []


class TestFlatten:
    def test_includes_all_nodes(self):
        flat = TreeSearch.flatten(TREE)
        assert len(flat) == 5  # root + 4 children

    def test_first_is_root(self):
        assert TreeSearch.flatten(TREE)[0]["name"] == "Open File"


class TestCount:
    def test_total_nodes(self):
        assert TreeSearch.count(TREE) == 5


class TestRectAndCenter:
    def test_rect(self):
        node = TREE["children"][1]  # Save button
        assert TreeSearch.rect(node) == (100, 200, 160, 230)

    def test_center(self):
        node = TREE["children"][1]
        cx, cy = TreeSearch.center(node)
        assert cx == 130
        assert cy == 215