# Phase 3: candidate-api

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — Candidate/Document API 엔드포인트 목록
- `docs/data-schema.md` — candidates, documents 테이블 정의, status ENUM, cascade 정책
- `docs/flow.md` — F2 (후보자 등록), F9 (삭제)

이전 phase 산출물:
- `backend/models/candidate.py`, `backend/models/document.py`
- `backend/api/auth.py` — `get_current_user` dependency
- `backend/config.py` — `settings.UPLOAD_DIR`, `settings.MAX_FILE_SIZE_MB`

## 작업 내용

### 1. `backend/utils/file_validator.py`

파일 유효성 검증 유틸리티.

```python
ALLOWED_RESUME = {'.pdf', '.jpg', '.jpeg', '.png', '.ppt', '.pptx'}
ALLOWED_PORTFOLIO = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # 20MB

def validate_file(file: UploadFile, doc_type: str) -> None:
    """
    검증 실패 시 HTTPException(400) raise.
    1. 파일 크기 확인 (20MB 제한)
    2. 확장자 확인 (doc_type에 따라 허용 목록 다름)
    3. filetype 라이브러리로 실제 MIME 확인
    """
```

filetype 라이브러리 사용:
```python
import filetype
kind = filetype.guess(file_bytes)
# kind.mime 확인: image/jpeg, image/png, application/pdf 등
```

허용 MIME:
- PDF: `application/pdf`
- 이미지: `image/jpeg`, `image/png`
- PPT: `application/vnd.ms-powerpoint`
- PPTX: `application/vnd.openxmlformats-officedocument.presentationml.presentation`

### 2. `backend/schemas/candidate.py`

```python
class CandidateCreate(BaseModel):
    name: str
    birth_year: Optional[int] = None
    position: Optional[str] = None
    interviewer_memo: Optional[str] = None

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    birth_year: Optional[int] = None
    position: Optional[str] = None
    interviewer_memo: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str  # 9가지 상태 중 하나

class CandidateResponse(BaseModel):
    id: str
    name: str
    birth_year: Optional[int]
    position: Optional[str]
    interviewer_memo: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    # 분석 점수 (홈 화면 카드 표시용, analyses JOIN)
    avg_value_score: Optional[float] = None
    doc_reliability_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
```

### 3. `backend/api/candidates.py`

**모든 엔드포인트는 `get_current_user` dependency 필수.**

```
GET    /api/candidates/          → CandidateResponse 목록 (status 쿼리 파라미터 필터)
POST   /api/candidates/          → CandidateResponse (등록)
GET    /api/candidates/{id}      → CandidateResponse
PATCH  /api/candidates/{id}      → CandidateResponse (기본 정보 수정)
PATCH  /api/candidates/{id}/status → CandidateResponse (상태 변경)
DELETE /api/candidates/{id}      → {"message": "삭제 완료"}
```

**삭제 처리**:
- 업로드 파일 물리 삭제: `uploads/{candidate_id}/` 폴더 전체 삭제
- DB cascade로 documents, analyses, interview_sessions, qa_pairs 자동 삭제

**status 유효 값** (검증 필수):
`미분석`, `분석중`, `분석완료`, `서류합격`, `서류탈락`, `면접합격`, `면접탈락`, `최종합격`, `최종탈락`

자동 상태(미분석/분석중/분석완료)도 면접관이 수동으로 변경 가능하다 (제약 없음).

**avg_value_score 계산**: analyses.values_scores JSON에서 12개 값의 score 평균. 분석이 없으면 None.

### 4. `backend/api/documents.py`

```
POST   /api/candidates/{id}/documents   파일 업로드
DELETE /api/documents/{doc_id}          파일 삭제
```

**업로드 처리**:
1. `doc_type` form 파라미터 수신 (resume | portfolio)
2. `validate_file(file, doc_type)` 호출
3. `uploads/{candidate_id}/` 폴더 생성
4. 파일을 `{uuid}.{ext}` 이름으로 저장
5. Document DB 레코드 생성 (ocr_text, ocr_method, ocr_quality_score는 null)
6. 후보자당 동일 doc_type이 이미 존재하면 기존 파일 삭제 후 교체

**삭제 처리**:
- DB 레코드 삭제 + 물리 파일 삭제

### 5. `backend/main.py` 업데이트

```python
from api.candidates import router as candidates_router
from api.documents import router as documents_router

app.include_router(candidates_router, prefix="/api/candidates", tags=["candidates"])
app.include_router(documents_router, prefix="/api", tags=["documents"])
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
from fastapi.testclient import TestClient
from main import app
import io

client = TestClient(app)

# 로그인
token = client.post('/api/auth/login', json={'email': 'admin@interx.com', 'password': 'interx1234'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 후보자 등록
r = client.post('/api/candidates/', json={'name': '테스트지원자', 'position': '백엔드 개발자'}, headers=headers)
assert r.status_code == 200, f'Create failed: {r.text}'
cid = r.json()['id']

# 조회
r2 = client.get(f'/api/candidates/{cid}', headers=headers)
assert r2.status_code == 200
assert r2.json()['name'] == '테스트지원자'

# 상태 변경
r3 = client.patch(f'/api/candidates/{cid}/status', json={'status': '서류합격'}, headers=headers)
assert r3.status_code == 200
assert r3.json()['status'] == '서류합격'

# 목록 조회
r4 = client.get('/api/candidates/', headers=headers)
assert r4.status_code == 200
assert len(r4.json()) >= 1

# 파일 업로드 (더미 PDF)
pdf_bytes = b'%PDF-1.4 test'
files = {'file': ('test.pdf', io.BytesIO(pdf_bytes), 'application/pdf')}
r5 = client.post(f'/api/candidates/{cid}/documents', files=files, data={'doc_type': 'resume'}, headers=headers)
# filetype 검증 실패할 수 있으므로 200 또는 400 모두 허용 (파일 형식 검증 동작 확인)
print(f'Upload status: {r5.status_code}')

# 삭제
r6 = client.delete(f'/api/candidates/{cid}', headers=headers)
assert r6.status_code == 200

print('Candidate API 모든 테스트 통과')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없이 완료되면 phase 3 status를 `"completed"`로 변경하라.

## 주의사항

- 파일 저장 경로는 `backend/` 기준으로 `uploads/{candidate_id}/{uuid}.{ext}`. uvicorn 실행 디렉토리가 `backend/`이므로 상대경로 그대로 사용.
- `shutil.rmtree`로 폴더 삭제 시 폴더가 없어도 에러 나지 않도록 `ignore_errors=True` 사용.
- 업로드 파일을 `await file.read()`로 읽을 때 `MAX_SIZE_BYTES` 초과 여부를 먼저 확인하라.
- filetype 라이브러리가 PPT/PPTX를 정확히 감지하지 못할 수 있다. 그 경우 확장자 기반 검증을 우선으로 하되, filetype 결과가 None이면 확장자만으로 통과시켜라.
- `avg_value_score` 계산 시 `analyses.values_scores`가 None이거나 파싱 실패하면 None 반환.
