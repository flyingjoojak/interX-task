import base64
import io

import anthropic
import fitz
from PIL import Image

from config import settings

CLAUDE_VISION_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 4096
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20
VISION_PROMPT = (
    "이 포트폴리오 이미지의 텍스트, 레이아웃 설명, 차트/다이어그램의 핵심 내용을 "
    "한국어로 정리하여 반환하세요. 디자인 요소와 시각 구성도 간단히 서술하세요."
)


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


def _image_file_to_png_bytes(file_path: str) -> bytes:
    img = Image.open(file_path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pdf_to_pngs(file_path: str, zoom: float = 2.0, max_pages: int = MAX_PDF_PAGES) -> list[bytes]:
    pngs: list[bytes] = []
    doc = fitz.open(file_path)
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=mat)
            pngs.append(pix.tobytes("png"))
    finally:
        doc.close()
    return pngs


def _vision_call(client: anthropic.Anthropic, png_bytes: bytes) -> str:
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


def extract_portfolio_text(file_path: str, file_type: str) -> str:
    """포트폴리오는 항상 Claude Vision으로 처리 (페이지별 순차)."""
    ft = (file_type or "").lower().lstrip(".")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    if ft == "pdf":
        pngs = _pdf_to_pngs(file_path)
        pages: list[str] = []
        for i, png in enumerate(pngs, start=1):
            text = _vision_call(client, png)
            pages.append(f"--- Page {i} ---\n{text}")
        return "\n\n".join(pages)

    png = _image_file_to_png_bytes(file_path)
    return _vision_call(client, png)
