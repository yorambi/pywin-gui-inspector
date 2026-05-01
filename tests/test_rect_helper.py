import pytest
from pywin_gui_inspector.helper.rect_helper import RectHelper


class TestParse:
    def test_tuple_string(self):
        assert RectHelper.parse("(10, 20, 100, 200)") == (10, 20, 100, 200)

    def test_pywinauto_rect_repr(self):
        assert RectHelper.parse("RECT(left=10, top=20, right=100, bottom=200)") == (10, 20, 100, 200)

    def test_negative_values(self):
        assert RectHelper.parse("(-5, -10, 50, 80)") == (-5, -10, 50, 80)

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            RectHelper.parse("not a rectangle")

    def test_too_few_numbers_raises(self):
        with pytest.raises(ValueError):
            RectHelper.parse("(1, 2)")


class TestCenter:
    def test_square(self):
        assert RectHelper.center((0, 0, 100, 100)) == (50, 50)

    def test_offset_rect(self):
        assert RectHelper.center((10, 20, 50, 60)) == (30, 40)

    def test_single_pixel(self):
        assert RectHelper.center((5, 5, 6, 6)) == (5, 5)


class TestFromDict:
    def test_extracts_rect(self):
        d = {"rect": {"left": 5, "top": 10, "right": 50, "bottom": 80}}
        assert RectHelper.from_dict(d) == (5, 10, 50, 80)