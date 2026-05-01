import json
import pytest
from pathlib import Path
from pywin_gui_inspector.helper.script_writer import ScriptWriter


EXPORT = {
    "element_tree": {
        "name": "File Dialog", "control_type": "Dialog",
        "automation_id": "", "is_enabled": True, "is_visible": True,
        "rectangle": "(0,0,500,400)",
        "children": [
            {
                "name": "File name:", "control_type": "Edit",
                "automation_id": "",
                "is_enabled": True, "is_visible": True,
                "rectangle": "(50,100,300,130)", "children": [],
            },
            {
                "name": "Save", "control_type": "Button",
                "automation_id": "btn_save",
                "is_enabled": True, "is_visible": True,
                "rectangle": "(100,200,160,230)", "children": [],
            },
        ],
    },
    "ocr_results":   [{"text": "Cancel", "confidence": 92.0,
                       "rect": {"left": 200, "top": 200, "right": 265, "bottom": 230}}],
    "image_results": [{"template": "ok_icon.png", "confidence": 0.9,
                       "center": {"x": 300, "y": 215},
                       "rect": {"left": 280, "top": 200, "right": 320, "bottom": 230}}],
}


@pytest.fixture
def export_file(tmp_path: Path) -> Path:
    f = tmp_path / "export.json"
    f.write_text(json.dumps(EXPORT), encoding="utf-8")
    return f


class TestScriptWriter:
    def test_click_by_auto_id_when_available(self, export_file):
        sw = ScriptWriter(export_file)
        code = sw._resolve_click("Save")
        assert "click_by_auto_id" in code
        assert "btn_save" in code

    def test_click_by_name_when_no_auto_id(self, export_file):
        sw = ScriptWriter(export_file)
        # "File name:" has no automation_id in this fixture → falls back to click_by_name
        code = sw._resolve_click("File name:")
        assert "click_by_name" in code
        assert "'File name:'" in code

    def test_click_ocr_fallback(self, export_file):
        sw = ScriptWriter(export_file)
        code = sw._resolve_click("Cancel")
        assert "click_ocr" in code

    def test_click_image_fallback(self, export_file):
        sw = ScriptWriter(export_file)
        code = sw._resolve_click("ok_icon.png")
        assert "click_image" in code

    def test_smart_click_when_not_found(self, export_file):
        sw = ScriptWriter(export_file)
        code = sw._resolve_click("Nonexistent Button")
        assert "smart_click" in code
        assert "WARNING" in code

    def test_generate_includes_gui_session(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("click Save")
        assert "GUISession" in script
        assert "import time" in script

    def test_type_into_step(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("type report.txt into File name:")
        assert "type_into" in script
        assert "'report.txt'" in script

    def test_wait_step(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("wait 2 seconds")
        assert "time.sleep(2)" in script

    def test_hotkey_step(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("hotkey ctrl+s")
        assert "hotkey" in script
        assert "'ctrl'" in script

    def test_press_step(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("press enter")
        assert "press('enter')" in script

    def test_write_creates_file(self, export_file, tmp_path):
        sw  = ScriptWriter(export_file)
        out = tmp_path / "output.py"
        sw.write("click Save", output=out)
        assert out.exists()
        assert "GUISession" in out.read_text(encoding="utf-8")

    def test_multiline_instructions(self, export_file):
        sw     = ScriptWriter(export_file)
        script = sw.generate("click Save\ntype hello into File name:")
        assert "click" in script
        assert "type_into" in script