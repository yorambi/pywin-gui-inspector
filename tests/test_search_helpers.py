import pytest
from pywin_gui_inspector.helper.search_helpers import OCRSearch, ImageSearch

OCR = [
    {"text": "Save",    "confidence": 96.3, "rect": {"left": 10, "top": 20, "right": 60,  "bottom": 40}},
    {"text": "Save As", "confidence": 88.1, "rect": {"left": 10, "top": 50, "right": 80,  "bottom": 70}},
    {"text": "Cancel",  "confidence": 92.5, "rect": {"left": 90, "top": 20, "right": 150, "bottom": 40}},
]

IMAGES = [
    {"template": "save_icon.png",   "confidence": 0.95,
     "center": {"x": 35, "y": 30}, "rect": {"left": 10, "top": 10, "right": 60, "bottom": 50}},
    {"template": "cancel_icon.png", "confidence": 0.91,
     "center": {"x": 120, "y": 30}, "rect": {"left": 90, "top": 10, "right": 150, "bottom": 50}},
]


class TestOCRSearch:
    def test_find_substring(self):
        r = OCRSearch.find(OCR, "Save")
        assert r["text"] == "Save"

    def test_find_exact_true(self):
        r = OCRSearch.find(OCR, "Save", exact=True)
        assert r["text"] == "Save"

    def test_find_exact_no_partial(self):
        assert OCRSearch.find(OCR, "Sav", exact=True) is None

    def test_find_not_found(self):
        assert OCRSearch.find(OCR, "Print") is None

    def test_find_case_insensitive(self):
        assert OCRSearch.find(OCR, "cancel") is not None

    def test_find_all_returns_both_save_entries(self):
        results = OCRSearch.find_all(OCR, "Save")
        assert len(results) == 2

    def test_center(self):
        cx, cy = OCRSearch.center(OCR[0])
        assert cx == 35
        assert cy == 30


class TestImageSearch:
    def test_find_any(self):
        r = ImageSearch.find(IMAGES)
        assert r is not None

    def test_find_by_template_name(self):
        r = ImageSearch.find(IMAGES, "save_icon.png")
        assert r["template"] == "save_icon.png"

    def test_find_by_template_name_not_found(self):
        assert ImageSearch.find(IMAGES, "no_such_icon.png") is None

    def test_center(self):
        cx, cy = ImageSearch.center(IMAGES[0])
        assert cx == 35
        assert cy == 30