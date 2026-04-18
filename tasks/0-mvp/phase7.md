# Phase 7: analysis-api

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — Analysis API 엔드포인트 목록, PDF export, Playwright
- `docs/flow.md` — F3 (분석 진행 중 폴링), F4 (리포트 확인), F7 (PDF 출력)
- `docs/adr.md` — ADR-009 (폴링 방식), ADR-010 (Playwright PDF)

이전 phase 산출물:
- `backend/services/analysis_runner.py` — `run_analysis` async 함수
- `backend/models/analysis.py` — Analysis 모델
- `backend/api/auth.py` — `get_current_user`

## 작업 내용

### 1. `backend/schemas/analysis.py`

```python
class AnalysisProgressResponse(BaseModel):
    candidate_id: str
    current_step: Optional[str]  # OCR|추출|가치매핑|모순탐지|질문생성|완료|오류
    step_started_at: Optional[datetime]
    estimated_remaining_seconds: Optional[int]
    progress_percent: int  # 0~100

class AnalysisResponse(BaseModel):
    candidate_id: str
    structured_data: Optional[dict]
    values_scores: Optional[dict]
    doc_reliability_score: Optional[float]
    contradictions: Optional[list]
    preemptive_questions: Optional[list]
    summary: Optional[str]
    current_step: Optional[str]
```

### 2. `backend/api/analysis.py`

**단계별 예상 소요시간** (초, 하드코딩):
```python
STEP_DURATIONS = {
    "OCR": 15,
    "추출": 20,
    "가치매핑": 25,
    "모순탐지": 15,
    "질문생성": 15,
}
STEP_ORDER = ["OCR", "추출", "가치매핑", "모순탐지", "질문생성", "완료"]
```

**엔드포인트**:

```
POST /api/candidates/{id}/analysis
  - 기존 분석이 있으면 삭제 (재분석 가능)
  - analyses 레코드 생성 (current_step="OCR")
  - BackgroundTasks.add_task(run_analysis, candidate_id)
  - 즉시 {"message": "분석이 시작되었습니다"} 반환

GET /api/candidates/{id}/analysis/progress
  - analyses.current_step + step_started_at 조회
  - estimated_remaining_seconds 계산:
    현재 단계 남은 시간 + 이후 단계들 합산
  - progress_percent 계산:
    완료 단계 수 / 전체 단계 수 * 100
  - current_step이 "완료"면 progress_percent=100

GET /api/candidates/{id}/analysis
  - analyses 전체 반환 (JSON 필드 파싱 포함)

DELETE /api/candidates/{id}/analysis
  - 분석 결과 삭제 + interview_sessions Q&A 초기화
  - (재분석 전처리용)

GET /api/candidates/{id}/report/pdf
  - pdf_export.generate_pdf(candidate_id) 호출
  - StreamingResponse로 PDF 바이트 반환
  - Content-Disposition: attachment; filename="report_{candidate_id}.pdf"
```

### 3. `backend/services/pdf_export.py`

Playwright로 리포트 HTML 페이지를 PDF로 렌더링.

```python
from playwright.async_api import async_playwright

async def generate_pdf(candidate_id: str) -> bytes:
    """
    1. async_playwright 컨텍스트 열기
    2. chromium 브라우저 실행
    3. http://localhost:3102/candidates/{candidate_id}?pdf=true 페이지 열기
    4. 페이지 로딩 완료 대기 (networkidle)
    5. page.pdf(format="A4", print_background=True) 호출
    6. PDF 바이트 반환
    """
```

PDF 렌더링 시 프론트엔드가 실행 중이어야 한다. 프론트엔드가 없을 경우를 위한 fallback: FastAPI 자체에서 HTML 템플릿으로 PDF 생성 (jinja2 + weasyprint 또는 단순 HTML 스트링). 이 Phase에서는 Playwright 방식을 우선 구현하되, import 오류 없이 함수가 존재하면 AC 통과.

### 4. `backend/main.py` 업데이트

```python
from api.analysis import router as analysis_router
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
token = client.post('/api/auth/login', json={'email': 'admin@interx.com', 'password': 'interx1234'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 후보자 생성
r = client.post('/api/candidates/', json={'name': '분석테스트', 'position': 'PM'}, headers=headers)
cid = r.json()['id']

# 분석 시작 (BackgroundTask이므로 즉시 반환됨)
r2 = client.post(f'/api/candidates/{cid}/analysis', headers=headers)
assert r2.status_code == 200, f'Analysis start failed: {r2.text}'

# 진행 상태 조회
r3 = client.get(f'/api/candidates/{cid}/analysis/progress', headers=headers)
assert r3.status_code == 200
prog = r3.json()
assert 'progress_percent' in prog
assert 'current_step' in prog
print(f'Progress: {prog}')

# 분석 결과 조회 (아직 완료 안 됐어도 200 반환해야 함)
r4 = client.get(f'/api/candidates/{cid}/analysis', headers=headers)
assert r4.status_code == 200

# 분석 삭제 (재분석 전처리 테스트)
r5 = client.delete(f'/api/candidates/{cid}/analysis', headers=headers)
assert r5.status_code == 200

# 정리
client.delete(f'/api/candidates/{cid}', headers=headers)
print('Analysis API 모든 테스트 통과')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없으면 phase 7 status를 `"completed"`로 변경하라.

## 주의사항

- BackgroundTask 내에서 DB 세션은 반드시 별도 `SessionLocal()`을 생성해야 한다. request scope 세션을 캡처하면 task 완료 전에 세션이 닫힌다.
- `GET /api/candidates/{id}/analysis/progress`는 analyses 레코드가 없어도 200 반환 (`current_step: null`, `progress_percent: 0`).
- PDF 엔드포인트 AC는 이 phase에서 테스트하지 않는다 (프론트엔드 미존재). import만 확인.
- `estimated_remaining_seconds` 계산: 현재 단계 시작 이후 경과 시간을 감안하여 남은 시간 추정. `step_started_at`이 null이면 전체 예상 시간 반환.
- analysis 결과의 JSON 필드(`values_scores` 등)는 DB에서 꺼낼 때 `json.loads()`로 파싱하여 dict/list로 반환.
