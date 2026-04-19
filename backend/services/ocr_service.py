import base64
import io

import fitz
from PIL import Image

from config import settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
CLAUDE_VISION_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 4096
VISION_PROMPT = (
    "이 이미지의 모든 텍스트를 **시각적으로 읽는 순서 그대로** 추출하세요. "
    "- 위에서 아래로, 같은 줄이면 왼쪽에서 오른쪽으로.\n"
    "- 2단 이상 컬럼이면 좌측 컬럼 전체를 먼저 다 읽고 그다음 우측 컬럼으로 이동.\n"
    "- 각 프로젝트/경력 블록의 제목·기간·기술스택·설명은 **같은 블록끼리 붙여서** 반환.\n"
    "- 서식(굵기, 색, 폰트)은 무시하고 텍스트 내용만."
)


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


def _image_to_png_bytes(file_path: str) -> bytes:
    img = Image.open(file_path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
    """이력서 텍스트 추출: PDF/JPG/PNG 모두 Claude Vision."""
    ft = (file_type or "").lower().lstrip(".")
    text, quality = _claude_vision_extract(file_path, "pdf" if ft == "pdf" else "image")
    return text, "claude_vision", quality
