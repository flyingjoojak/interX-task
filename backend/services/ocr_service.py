import base64
import io
import os

import fitz
from PIL import Image

from config import settings
from services.ppt_service import extract_ppt_text

QUALITY_THRESHOLD = 0.7
MAX_IMAGE_BYTES = 5 * 1024 * 1024
CLAUDE_VISION_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 4096
VISION_PROMPT = (
    "이 이미지의 모든 텍스트를 추출하여 원문 그대로 반환하세요. "
    "서식은 무시하고 텍스트 내용만 반환하세요."
)

_paddle_ocr = None


def _calc_quality(text: str, page_count: int) -> float:
    if page_count <= 0:
        return 0.0
    return min(1.0, len(text.strip()) / (page_count * 200))


def _pdf_to_pngs(file_path: str, zoom: float = 2.0) -> list[bytes]:
    pngs: list[bytes] = []
    doc = fitz.open(file_path)
    try:
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat)
            pngs.append(pix.tobytes("png"))
    finally:
        doc.close()
    return pngs


def _compress_png_if_needed(png_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    if len(png_bytes) <= max_bytes:
        return png_bytes
    img = Image.open(io.BytesIO(png_bytes))
    scale = (max_bytes / len(png_bytes)) ** 0.5
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _read_image_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def _image_to_png_bytes(file_path: str) -> bytes:
    img = Image.open(file_path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pymupdf_extract(file_path: str) -> tuple[str, float]:
    doc = fitz.open(file_path)
    try:
        text = "".join(page.get_text() for page in doc)
        quality = _calc_quality(text, len(doc))
    finally:
        doc.close()
    return text, quality


def _get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR  # type: ignore

        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="korean", show_log=False)
    return _paddle_ocr


def _paddle_extract_from_image_bytes(img_bytes: bytes) -> str:
    import numpy as np  # type: ignore

    ocr = _get_paddle_ocr()
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img)
    result = ocr.ocr(arr, cls=True)
    lines: list[str] = []
    if result:
        for page_result in result:
            if not page_result:
                continue
            for line in page_result:
                if line and len(line) >= 2 and line[1]:
                    lines.append(line[1][0])
    return "\n".join(lines)


def _paddle_extract(file_path: str, file_type: str) -> tuple[str, float]:
    if file_type == "pdf":
        pngs = _pdf_to_pngs(file_path)
        page_texts = [_paddle_extract_from_image_bytes(p) for p in pngs]
        text = "\n".join(page_texts)
        quality = _calc_quality(text, len(pngs))
    else:
        png = _image_to_png_bytes(file_path)
        text = _paddle_extract_from_image_bytes(png)
        quality = _calc_quality(text, 1)
    return text, quality


def _claude_vision_extract_page(client, png_bytes: bytes) -> str:
    png_bytes = _compress_png_if_needed(png_bytes)
    b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
    response = client.messages.create(
        model=CLAUDE_VISION_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }
        ],
    )
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _claude_vision_extract(file_path: str, file_type: str) -> tuple[str, float]:
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    if file_type == "pdf":
        pngs = _pdf_to_pngs(file_path)
        page_texts = [_claude_vision_extract_page(client, p) for p in pngs]
        text = "\n\n".join(page_texts)
        quality = _calc_quality(text, len(pngs))
    else:
        png = _image_to_png_bytes(file_path)
        text = _claude_vision_extract_page(client, png)
        quality = _calc_quality(text, 1)
    return text, quality


def extract_resume_text(file_path: str, file_type: str) -> tuple[str, str, float]:
    """이력서 OCR: PyMuPDF → PaddleOCR → Claude Vision 3단계 폴백."""
    ft = (file_type or "").lower().lstrip(".")

    if ft in ("ppt", "pptx"):
        text = extract_ppt_text(file_path)
        quality = 1.0 if text.strip() else 0.0
        return text, "pptx", quality

    if ft == "pdf":
        text, quality = _pymupdf_extract(file_path)
        if quality >= QUALITY_THRESHOLD:
            return text, "pymupdf", quality

    try:
        text, quality = _paddle_extract(file_path, ft if ft == "pdf" else "image")
        if quality >= QUALITY_THRESHOLD:
            return text, "paddleocr", quality
    except ImportError:
        pass
    except Exception:
        pass

    text, quality = _claude_vision_extract(file_path, ft if ft == "pdf" else "image")
    return text, "claude_vision", quality
