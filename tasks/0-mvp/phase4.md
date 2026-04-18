# Phase 4: ocr-services

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — OCR Service, Portfolio Service, PPT Service, Anonymizer 역할
- `docs/adr.md` — ADR-002 (OCR 3단계 폴백), ADR-003 (포트폴리오 Claude Vision), ADR-004 (PPT 미지원)

이전 phase 산출물:
- `backend/config.py` — `settings.ANTHROPIC_API_KEY`
- `backend/models/document.py` — Document 모델 (ocr_text, ocr_method, ocr_quality_score)

## 작업 내용

### 1. PaddleOCR 설치

```bash
pip install paddlepaddle paddleocr
```

첫 실행 시 모델 파일을 자동 다운로드한다 (~500MB). 오류 발생 시 CPU 버전 명시:
```bash
pip install paddlepaddle==2.6.1 paddleocr==2.7.3
```

### 2. `backend/services/ocr_service.py` — 이력서 OCR (3단계 폴백)

```python
QUALITY_THRESHOLD = 0.7  # 이 값 미만이면 다음 단계로 폴백

def extract_resume_text(file_path: str, file_type: str) -> tuple[str, str, float]:
    """
    Returns: (ocr_text, ocr_method, quality_score)
    file_type: 'pdf' | 'image' | 'ppt' | 'pptx'
    """
```

**단계 1 — PyMuPDF (PDF 전용)**:
```python
import fitz  # PyMuPDF
doc = fitz.open(file_path)
text = "".join(page.get_text() for page in doc)
quality = _calc_quality(text, len(doc))
# quality = min(1.0, len(text.strip()) / (len(doc) * 200))
# 페이지당 200자 이상이면 품질 양호로 간주
```

**단계 2 — PaddleOCR (image 및 PDF 폴백)**:
```python
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='korean', show_log=False)
# PDF인 경우: fitz로 각 페이지를 PNG로 렌더링 후 OCR
# image인 경우: 직접 OCR
```

**단계 3 — Claude Vision API (최종 폴백)**:
```python
import anthropic
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
# PDF: fitz로 페이지별 PNG 렌더링 → base64 인코딩 → Claude API 전송
# image: 파일 직접 base64 → Claude API 전송
```

Claude Vision 호출 예시:
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_data}},
            {"type": "text", "text": "이 이미지의 모든 텍스트를 추출하여 원문 그대로 반환하세요. 서식은 무시하고 텍스트 내용만 반환하세요."}
        ]
    }]
)
```

**PPT/PPTX는 `ppt_service.py`로 위임** (이 함수에서 file_type이 ppt/pptx면 ppt_service 호출).

### 3. `backend/services/portfolio_service.py` — 포트폴리오 처리

포트폴리오는 **항상 Claude Vision**으로 처리 (품질 폴백 없음).

```python
def extract_portfolio_text(file_path: str, file_type: str) -> str:
    """
    PDF: fitz로 각 페이지를 PNG로 렌더링 → Claude Vision (페이지별 순차 처리)
    image (jpg/png): 직접 Claude Vision
    결과 텍스트를 페이지 구분자와 함께 통합하여 반환
    """
```

PDF 페이지 렌더링:
```python
doc = fitz.open(file_path)
for i, page in enumerate(doc):
    mat = fitz.Matrix(2.0, 2.0)  # 2x 해상도
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    # base64 인코딩 후 Claude Vision 호출
```

페이지 수가 많은 경우 최대 20페이지까지만 처리 (API 비용 제한).

### 4. `backend/services/ppt_service.py` — PPT/PPTX 텍스트 추출 (이력서 한정)

```python
from pptx import Presentation

def extract_ppt_text(file_path: str) -> str:
    """python-pptx로 텍스트 요소만 추출. 이미지 내 텍스트는 추출 불가."""
    prs = Presentation(file_path)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
    return "\n".join(texts)
```

### 5. `backend/services/anonymizer.py` — PII 익명화

```python
import re

def anonymize(text: str) -> tuple[str, dict]:
    """
    Returns: (anonymized_text, pii_map)
    pii_map: {"지원자A": "홍길동", "[연락처1]": "010-1234-5678", ...}
    """

def restore(text: str, pii_map: dict) -> str:
    """anonymized text에서 pii_map을 역방향으로 복원"""
```

마스킹 패턴:
- 한국 휴대폰: `010-\d{4}-\d{4}` → `[연락처N]`
- 이메일: 이메일 패턴 → `[이메일N]`
- 이름 (별도 추출 없이, Claude API 전송 후 복원만 지원)

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
import sys

# 1. 서비스 import 확인
from services.ocr_service import extract_resume_text
from services.portfolio_service import extract_portfolio_text
from services.ppt_service import extract_ppt_text
from services.anonymizer import anonymize, restore
print('모든 서비스 import OK')

# 2. anonymizer 단위 테스트
text = '홍길동, 010-1234-5678, hong@example.com'
anon, pii_map = anonymize(text)
assert '010-1234-5678' not in anon, '전화번호 마스킹 실패'
assert 'hong@example.com' not in anon, '이메일 마스킹 실패'
restored = restore(anon, pii_map)
assert '010-1234-5678' in restored, '복원 실패'
print('Anonymizer 테스트 OK')

# 3. PyMuPDF 동작 확인
import fitz
print(f'PyMuPDF 버전: {fitz.version}')

print('Phase 4 기본 검증 완료')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없이 완료되면 phase 4 status를 `"completed"`로 변경하라.

PaddleOCR import 오류 발생 시: `pip install paddlepaddle paddleocr` 재실행 후 retry. PaddleOCR 설치가 계속 실패하더라도 나머지 서비스(PyMuPDF, Claude Vision, anonymizer)가 동작하면 통과시켜라 (PaddleOCR은 폴백 2단계로, 없어도 PyMuPDF + Claude Vision으로 동작 가능).

## 주의사항

- Claude Vision API 호출 시 이미지 크기 제한: 단일 이미지 최대 5MB. 초과 시 PIL로 리사이즈하라.
- `fitz.open()`은 pdf 파일만 사용. image 파일은 fitz로 열지 말고 PIL/Pillow로 처리.
- anonymizer의 `pii_map`은 순서 보장이 중요하다. `[연락처1]`, `[연락처2]` 같이 순번을 부여하여 충돌 방지.
- PaddleOCR은 첫 실행 시 모델 다운로드가 오래 걸릴 수 있다. `show_log=False`로 로그 억제.
- 이 phase에서 실제 API 호출 테스트는 하지 않는다 (비용 발생). import와 함수 시그니처 확인만.
