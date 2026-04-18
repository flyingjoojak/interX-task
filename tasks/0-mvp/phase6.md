# Phase 6: analysis-agent

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — LangGraph 사전 분석 그래프 노드 목록, Analysis Runner 로직
- `docs/data-schema.md` — analyses 테이블, current_step 값 목록
- `docs/adr.md` — ADR-006 (LangGraph 선택 이유)

이전 phase 산출물:
- `backend/agents/prompts.py` — 모든 프롬프트 빌더 함수
- `backend/services/ocr_service.py` — extract_resume_text
- `backend/services/portfolio_service.py` — extract_portfolio_text
- `backend/services/anonymizer.py` — anonymize, restore
- `backend/models/analysis.py` — Analysis 모델
- `backend/models/document.py` — Document 모델
- `backend/database.py` — SessionLocal

## 작업 내용

### 1. `backend/agents/analysis_graph.py` — LangGraph 사전 분석 그래프

**State 정의**:

```python
from typing import TypedDict, Optional, List, Dict, Any

class AnalysisState(TypedDict):
    candidate_id: str
    documents: List[Dict]       # [{"text": str, "doc_type": "resume|portfolio", "file_type": str}]
    resume_text: str            # OCR 추출된 이력서 텍스트
    portfolio_text: str         # OCR 추출된 포트폴리오 텍스트
    anonymized_resume: str
    anonymized_portfolio: str
    pii_map: Dict[str, str]
    structured_data: Dict
    values_scores: Dict
    doc_reliability_score: float
    contradictions: List[Dict]
    preemptive_questions: List[Dict]
    summary: str
    error: Optional[str]
```

**8개 노드 구현**:

각 노드는 `(state: AnalysisState) -> dict` 시그니처. 반환값이 state에 merge됨.

각 노드 시작 시 `_update_step(state["candidate_id"], step_name)` 호출하여 DB의 `analyses.current_step`과 `step_started_at`을 업데이트한다.

```
노드 1: parse_documents
  - documents 리스트에서 이력서/포트폴리오 텍스트 추출
  - resume: ocr_service.extract_resume_text 호출
  - portfolio: portfolio_service.extract_portfolio_text 호출
  - → resume_text, portfolio_text 업데이트
  - DB step: "OCR"

노드 2: anonymize_pii
  - resume_text + portfolio_text에 anonymizer.anonymize 적용
  - → anonymized_resume, anonymized_portfolio, pii_map
  - DB step: "추출" (이 단계에서 구조화 추출도 시작)

노드 3: extract_structured_data
  - Claude API: build_extraction_prompt(anonymized_resume, anonymized_portfolio)
  - 응답 JSON 파싱
  - → structured_data
  - DB step: "추출"

노드 4: score_12_values
  - Claude API: build_value_scoring_prompt(anonymized_resume, structured_data)
  - 응답 JSON 파싱 (12가지 가치 점수)
  - → values_scores
  - DB step: "가치매핑"

노드 5: calculate_doc_reliability
  - Claude API: build_reliability_prompt(anonymized_resume, anonymized_portfolio)
  - → doc_reliability_score (float)
  - DB step: "가치매핑"

노드 6: detect_contradictions
  - Claude API: build_contradiction_prompt(...)
  - → contradictions (list)
  - DB step: "모순탐지"

노드 7: generate_preemptive_questions
  - Claude API: build_preemptive_questions_prompt(structured_data, values_scores, contradictions)
  - → preemptive_questions (list)
  - DB step: "질문생성"

노드 8: compile_and_restore
  - PII 복원: restore(json.dumps(structured_data), pii_map) 등
  - 종합 요약 생성 (Claude API 한 번 더 또는 로컬 조합)
  - DB step: "완료"
  - analyses 테이블에 전체 결과 저장
```

**그래프 조립**:
```python
from langgraph.graph import StateGraph, END

def build_analysis_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("parse_documents", parse_documents)
    graph.add_node("anonymize_pii", anonymize_pii)
    graph.add_node("extract_structured_data", extract_structured_data)
    graph.add_node("score_12_values", score_12_values)
    graph.add_node("calculate_doc_reliability", calculate_doc_reliability)
    graph.add_node("detect_contradictions", detect_contradictions)
    graph.add_node("generate_preemptive_questions", generate_preemptive_questions)
    graph.add_node("compile_and_restore", compile_and_restore)

    graph.set_entry_point("parse_documents")
    graph.add_edge("parse_documents", "anonymize_pii")
    graph.add_edge("anonymize_pii", "extract_structured_data")
    graph.add_edge("extract_structured_data", "score_12_values")
    graph.add_edge("score_12_values", "calculate_doc_reliability")
    graph.add_edge("calculate_doc_reliability", "detect_contradictions")
    graph.add_edge("detect_contradictions", "generate_preemptive_questions")
    graph.add_edge("generate_preemptive_questions", "compile_and_restore")
    graph.add_edge("compile_and_restore", END)

    return graph.compile()

analysis_graph = build_analysis_graph()
```

### 2. `backend/services/analysis_runner.py`

FastAPI BackgroundTask에서 호출되는 진입점.

```python
async def run_analysis(candidate_id: str) -> None:
    """
    1. DB에서 candidate + documents 로드
    2. analyses 레코드 upsert (없으면 생성, 있으면 초기화)
    3. AnalysisState 초기 값 구성
    4. analysis_graph.ainvoke(initial_state) 실행
    5. 오류 발생 시 analyses.current_step = "오류" 업데이트
    """
```

**DB 업데이트 헬퍼**:
```python
def _update_step(candidate_id: str, step: str) -> None:
    """독립 DB 세션으로 current_step + step_started_at 업데이트"""
    # BackgroundTask 컨텍스트에서는 별도 세션 사용 필수
```

**Claude API 호출 래퍼**:
```python
def _call_claude(prompt: str, max_tokens: int = 4096) -> str:
    """
    anthropic.Anthropic 동기 클라이언트 사용.
    응답에서 텍스트만 추출.
    JSON 파싱 실패 시 재시도 1회.
    """
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
# 그래프 구조 검증 (API 호출 없이)
from agents.analysis_graph import analysis_graph, AnalysisState
from services.analysis_runner import run_analysis
import inspect

# 그래프 import 성공
print('Analysis graph import OK')

# 노드 수 확인
nodes = list(analysis_graph.nodes.keys())
print(f'그래프 노드: {nodes}')
assert len(nodes) >= 8, f'노드 수 부족: {len(nodes)}'

# run_analysis는 async 함수
assert inspect.iscoroutinefunction(run_analysis), 'run_analysis는 async여야 함'

print('Phase 6 그래프 구조 검증 완료')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없으면 phase 6 status를 `"completed"`로 변경하라.

## 주의사항

- `_update_step`은 **별도의 독립 SessionLocal 세션**을 사용해야 한다. BackgroundTask 컨텍스트에서 request scope DB 세션은 사용 불가.
- Claude API 호출은 모두 **동기 클라이언트** (`anthropic.Anthropic`, 비동기 아님). LangGraph가 asyncio 루프를 관리하므로 내부에서 sync 호출이 더 안정적.
- JSON 파싱 시 Claude 응답에 마크다운 코드블록(` ```json `)이 포함될 수 있다. 정규식으로 제거 후 파싱.
- 각 Claude API 호출 사이에 `time.sleep(0.5)` 추가하여 rate limit 회피.
- `compile_and_restore` 노드에서 DB 저장 시 JSON 필드는 `json.dumps(data, ensure_ascii=False)` 사용.
- 오류 노드를 별도로 만들지 않고, 각 노드에서 try/except로 잡아 `analyses.current_step = "오류"`로 업데이트 후 raise.
