import pytest

from app.tools.ocr_tool import image_ocr


def test_ocr_extracts_text_from_image():
    text = image_ocr("tests/fixtures/sample_text_image.png")
    assert "150000" in text or "TOTAL" in text.upper()


def test_ocr_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        image_ocr("tests/fixtures/does_not_exist.png")
