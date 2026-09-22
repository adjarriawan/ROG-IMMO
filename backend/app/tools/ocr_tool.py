import os

from paddleocr import PaddleOCR

_ocr = None


def _get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="en")
    return _ocr


def image_ocr(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    result = _get_ocr().ocr(image_path, cls=True)
    lines = [line[1][0] for block in result for line in block]
    return "\n".join(lines)
