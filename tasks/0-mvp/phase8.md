# Phase 8: interview-agent-api

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — Interview Agent (interview_graph), Interview API 엔드포인트
- `docs/data-schema.md` — interview_sessions, qa_pairs 테이블
- `docs/flow.md` — F6 (실시간 면접 흐름, 꼬리질문 사이클)
- `docs/adr.md` — ADR-011 (Q&A 선형 타임라인)

이전 phase 산출물:
- `backend/agents/prompts.py` — `build_followup_prompt`
- `backend/models/interview.py` — InterviewSession, QAPair 모델
- `backend/api/auth.py` — `get_current_user`
- `backend/models/analysis.py` — Analysis 모델 (면접 컨텍스트용)

## 작업 내용

### 1. `backend/agents/interview_graph.py` — 실시간 꼬리질문 생성 그래프

**목표 응답 시간: 10초 이내**

```python
class InterviewState(TypedDict):
    candidate_id: str
    resume_summary: dict        # analyses.structured_data (이미 파싱됨)
    values_context: dict        # analyses.values_scores (낮은 점수 가치 컨텍스트)
    current_question: str
    current_answer: str
    conversation_history: list  # 최근 3개 Q&A [{"q": str, "a": str}]
    answer_analysis: dict       # {"vagueness": str, "inconsistency": str, "exaggeration": str}
    followup_questions: list    # [{"question": str, "reasoning": str, "priority": int}]
```

**4개 노드**:

```
노드 1: prepare_context
  - candidate_id로 DB에서 analyses 로드
  - structured_data + values_scores 파싱
  - conversation_history 구성 (최근 3개 QAPair)
  - → resume_summary, values_context 업데이트

노드 2: analyze_answer
  - 답변의 모호성/불일치/과장 분석
  - Claude API 호출: 짧은 분석 (max_tokens=512)
  - → answer_analysis

노드 3: generate_followups
  - build_followup_prompt 사용
  - Claude API 호출: 꼬리질문 생성 (max_tokens=1024)
  - → followup_questions (3~5개)

노드 4: rank_and_filter
  - priority 기준 정렬
  - 상위 5개 선택
  - → followup_questions (최종)
```

**그래프 조립 및 export**:
```python
interview_graph = build_interview_graph()

async def generate_followup_questions(
    candidate_id: str,
    question: str,
    answer: str,
    session_id: str,
) -> list[dict]:
    """interview_graph.ainvoke 래퍼. 꼬리질문 리스트 반환."""
```

### 2. `backend/schemas/interview.py`

```python
class SessionResponse(BaseModel):
    id: str
    candidate_id: str
    last_accessed_at: Optional[datetime]
    created_at: datetime
    qa_pairs: list  # QAPairResponse 목록

class QAPairResponse(BaseModel):
    id: str
    session_id: str
    question_source: str  # pregenerated|custom|followup
    question_text: str
    answer_text: Optional[str]
    followup_questions: Optional[list]
    parent_qa_id: Optional[str]
    order_index: int
    created_at: datetime
    answered_at: Optional[datetime]

class CreateQARequest(BaseModel):
    session_id: str
    question_source: str
    question_text: str
    parent_qa_id: Optional[str] = None

class AnswerQARequest(BaseModel):
    answer_text: str
```

### 3. `backend/api/interview.py`

```
POST /api/candidates/{id}/interview/session
  - 기존 세션이 있으면 반환 (last_accessed_at 업데이트)
  - 없으면 새 세션 생성
  - qa_pairs 포함하여 반환

GET /api/candidates/{id}/interview/session
  - 세션 + 전체 Q&A (order_index 오름차순) 반환

DELETE /api/candidates/{id}/interview/session
  - 세션의 모든 qa_pairs 삭제 (새로 시작)
  - 세션 자체는 유지 (last_accessed_at 초기화)

POST /api/interview/qa
  - QAPair 생성 (answer_text = null)
  - order_index = 현재 세션 최대 order_index + 1
  - QAPairResponse 반환

PATCH /api/interview/qa/{qa_id}
  - answer_text 저장
  - answered_at = now
  - generate_followup_questions 호출 (await)
  - followup_questions JSON 저장
  - 업데이트된 QAPairResponse 반환 (followup_questions 포함)
```

### 4. `backend/main.py` 업데이트

```python
from api.interview import router as interview_router
app.include_router(interview_router, prefix="/api", tags=["interview"])
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
import asyncio
from fastapi.testclient import TestClient
from main import app
from agents.interview_graph import interview_graph, InterviewState

client = TestClient(app)
token = client.post('/api/auth/login', json={'email': 'admin@interx.com', 'password': 'interx1234'}).json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 후보자 생성
cid = client.post('/api/candidates/', json={'name': '면접테스트', 'position': 'PM'}, headers=headers).json()['id']

# 세션 생성
r = client.post(f'/api/candidates/{cid}/interview/session', headers=headers)
assert r.status_code == 200, f'Session failed: {r.text}'
session_id = r.json()['id']

# Q&A 생성
r2 = client.post('/api/interview/qa', json={
    'session_id': session_id,
    'question_source': 'custom',
    'question_text': '자기소개를 해주세요'
}, headers=headers)
assert r2.status_code == 200
qa_id = r2.json()['id']

# 답변 제출 (꼬리질문 생성 - 실제 API 호출 발생)
# 참고: ANTHROPIC_API_KEY가 필요. 없으면 blocked 처리
import os
if not os.getenv('ANTHROPIC_API_KEY') and not open('.env').read().__contains__('ANTHROPIC_API_KEY'):
    print('ANTHROPIC_API_KEY 없음 - 꼬리질문 생성 테스트 스킵')
else:
    r3 = client.patch(f'/api/interview/qa/{qa_id}', json={'answer_text': '저는 5년차 PM입니다.'}, headers=headers)
    assert r3.status_code == 200, f'Answer failed: {r3.text}'
    result = r3.json()
    assert 'followup_questions' in result
    print(f'꼬리질문 생성: {result[\"followup_questions\"]}')

# 세션 조회
r4 = client.get(f'/api/candidates/{cid}/interview/session', headers=headers)
assert r4.status_code == 200

# 세션 초기화
r5 = client.delete(f'/api/candidates/{cid}/interview/session', headers=headers)
assert r5.status_code == 200

client.delete(f'/api/candidates/{cid}', headers=headers)
print('Interview API 모든 테스트 통과')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없으면 phase 8 status를 `"completed"`로 변경하라.

ANTHROPIC_API_KEY가 없어 꼬리질문 생성이 불가능하면 해당 부분은 스킵하고 나머지가 통과하면 `"completed"`. API 키가 없는 상황이면 `"blocked"` + `"blocked_reason": "ANTHROPIC_API_KEY가 backend/.env에 설정되어 있지 않습니다"`로 기록하라.

## 주의사항

- `PATCH /api/interview/qa/{qa_id}`의 꼬리질문 생성은 **await**이 필요한 async 작업. FastAPI async endpoint로 구현.
- 꼬리질문 생성 실패 시 (API 오류 등) 답변은 저장하되 followup_questions는 빈 리스트로 반환. 엔드포인트 자체가 500으로 실패하면 안 된다.
- `interview_graph`는 LangGraph async 그래프. `await interview_graph.ainvoke(state)` 사용.
- 세션 삭제 (`DELETE session`)는 qa_pairs만 삭제하고 세션 레코드는 유지. 이후 POST session 시 동일 세션에 새 Q&A 추가.
- `order_index`는 세션 내에서만 유일하면 됨. `SELECT MAX(order_index) FROM qa_pairs WHERE session_id = ?` + 1.
