# Phase 5: analysis-prompts

## 사전 준비

아래 문서를 읽어라:

- `docs/prd.md` — 12가지 핵심가치 전체 목록과 키워드
- `docs/data-schema.md` — analyses 테이블의 JSON 필드 구조 (values_scores, contradictions, preemptive_questions)
- `docs/adr.md` — ADR-007 (AI 탐지 대신 Drill-down), ADR-005 (Claude claude-sonnet-4-6)

이전 phase 산출물:
- `backend/services/anonymizer.py` — anonymize/restore 함수

## 작업 내용

`backend/agents/prompts.py` 파일 하나에 모든 한국어 프롬프트를 정의한다. 이 파일이 LangGraph 분석 품질의 핵심이다.

### 인터엑스 12가지 핵심가치

```python
INTERX_VALUES = {
    "목표의식": "선도적/정량 목표 설정, 마일스톤 수치화, 조직 목표 연계, 도전적 목표(X차원)",
    "시간관리": "AI 등 리소스 활용 자동화, 확보된 시간을 고부가가치 업무 집중, 마감기한 엄수",
    "끈기": "실패를 통해 전략을 빠르게 바꿔 반복 실행, 불확실성과 모호함 속에서 집요하게 해답 도출",
    "문제해결": "고객/시장에 대한 깊은 공감, 문제의 본질 파악, 구조적 재발 방지 해결책",
    "비판적사고": "수치/데이터 기반 근거, 기존 경험 비판적 통찰, 근본적 대안 도출",
    "지속적개선": "AI/신기술 업무 적극 도입, 기존 프로세스 혁신, 개선안 제시 및 전파",
    "정성스러움": "반복적 실수 방지, 높은 품질 지속 유지, 결과물에 최고 수준 전문성 지향",
    "자기동기부여": "일의 의미와 가치 명확 인식, 강박적 호기심, 자율적 성장 궤도 설정",
    "긍정적태도": "예상치 못한 변화/위기 상황에서 낙천성 유지, 주변 사람 사기에 긍정적 영향",
    "솔직한피드백": "피드백 정기적 요청 및 제공, 성장지향적 피드백 수용, 솔직한 소통 문화",
    "네트워크활용": "내외부 이해관계자와 전략적 네트워크, 시너지를 통한 새로운 기회 창출",
    "호기심": "새로운 분야에 지치지 않는 호기심, 지속적 질문과 학습, 실무에 선제적 적용",
}
```

### 프롬프트 1: `STRUCTURED_EXTRACTION_PROMPT`

이력서/포트폴리오 통합 텍스트에서 구조화된 데이터를 추출하는 프롬프트.

반드시 포함해야 할 내용:
- 아래 JSON 스키마를 정확히 따르도록 지시
- 한국어 이력서 특성 고려 (직책, 연봉, 인턴/정규직 구분)
- 날짜 형식 통일 지시 (YYYY.MM 형식)

출력 JSON 스키마:
```json
{
  "career": [{"company": "", "role": "", "start": "YYYY.MM", "end": "YYYY.MM or 재직중", "description": ""}],
  "education": [{"school": "", "major": "", "degree": "", "start": "YYYY.MM", "end": "YYYY.MM"}],
  "skills": ["기술1", "기술2"],
  "achievements": [{"title": "", "description": "", "quantified_result": "수치화된 성과 (없으면 null)"}],
  "certifications": [{"name": "", "issuer": "", "date": "YYYY.MM"}],
  "projects": [{"name": "", "role": "", "period": "", "description": "", "tech_stack": []}]
}
```

### 프롬프트 2: `VALUE_SCORING_PROMPT`

12가지 핵심가치 각각을 0~100점으로 평가하는 프롬프트.

반드시 포함해야 할 내용:
- 각 가치의 정의와 키워드를 프롬프트에 명시적으로 포함
- 점수 근거는 반드시 이력서의 구체적 사례/문장을 인용
- 증거가 없으면 낮은 점수(0~30) 부여 지시
- 80점 기준은 "충분한 구체적 증거가 있고 일관성이 있는 경우"로 정의
- 추상적 자기서술("열정적입니다", "성실합니다")은 증거로 인정하지 않음

출력 JSON 스키마:
```json
{
  "목표의식": {"score": 0-100, "evidence": "구체적 근거 문장", "examples": ["이력서 인용1", "이력서 인용2"]},
  "시간관리": {"score": 0-100, "evidence": "...", "examples": [...]},
  ...모든 12가지 가치...
}
```

### 프롬프트 3: `DOC_RELIABILITY_PROMPT`

문서 신뢰도를 0~100점으로 평가하는 프롬프트.

평가 기준 (프롬프트에 명시):
- **일치도** (40점): 문서 내/간 정보의 일관성 (날짜, 직책, 성과 수치)
- **신뢰도** (30점): 성과 수치의 구체성, 검증 가능성, 과장 가능성
- **완성도** (30점): 필수 정보(경력/학력/연락처) 충분히 기재 여부

출력: `{"score": 0-100, "breakdown": {"consistency": 0-40, "credibility": 0-30, "completeness": 0-30}, "issues": ["문제점1", "문제점2"]}`

### 프롬프트 4: `CONTRADICTION_DETECTION_PROMPT`

이력서 내부 모순 + 이력서↔포트폴리오 간 불일치를 탐지하는 프롬프트.

탐지 대상 (프롬프트에 명시):
- 날짜/기간 불일치 (재직 기간 겹침, 학업과 직장 기간 중복 이상)
- 직책/역할 불일치 (동일 경험의 다른 설명)
- 성과 수치 불일치 (같은 프로젝트의 다른 성과 기술)
- 기술 스택 불일치 (사용 경험 없다가 있다고 표기)

각 모순에 심각도 부여:
- `high`: 명백한 수치/날짜 오류, 설명 불가능한 불일치
- `medium`: 부분적 불일치, 해석에 따라 다를 수 있음
- `low`: 표현 방식 차이, 의도적 생략 가능성

출력 스키마 (`data-schema.md`의 contradictions JSON 구조 그대로):
```json
[{"source_a": "문서/위치", "source_b": "문서/위치", "description": "불일치 내용", "severity": "high|medium|low"}]
```

### 프롬프트 5: `PREEMPTIVE_QUESTIONS_PROMPT`

모순 탐지 결과와 낮은 가치 점수를 기반으로 사전 압박 질문을 생성하는 프롬프트.

질문 생성 원칙 (프롬프트에 명시):
- 모순 항목마다 최소 1개의 직접적인 확인 질문 생성
- 낮은 점수(40점 미만) 가치에 대해 구체적 경험 드릴다운 질문 생성
- 질문은 **구체적이고 답변하기 어려운** 형태 ("~에 대해 말씀해주세요" 형태 금지)
- 대신: "당시 팀원은 몇 명이었고, 본인이 직접 내린 결정 중 가장 어려웠던 것은?"
- AI가 생성한 답변자는 구체적 세부사항을 모르므로 세부사항을 묻는 방식 사용

출력 스키마:
```json
[{"question": "질문 내용", "target_value": "관련 핵심가치명 or null", "basis": "이 질문을 하는 근거"}]
```

### 프롬프트 6: `INTERVIEW_FOLLOWUP_PROMPT`

실시간 면접에서 후보자 답변을 받아 압박 꼬리질문을 생성하는 프롬프트.

입력 컨텍스트:
- 이력서 요약 (structured_data)
- 질문과 후보자 답변
- 이전 Q&A 히스토리 (최근 3개)

분석 항목 (프롬프트에 명시):
- **모호성**: 추상적 표현, 수치 없는 성과, "열심히 했습니다" 류의 답변
- **불일치**: 이력서와 답변의 사실관계 차이
- **과장 가능성**: 검증하기 어려운 성과 주장, 1인칭 공로 주장

꼬리질문 원칙:
- 답변의 가장 취약한 지점 1~2개를 정확히 파고드는 질문
- "구체적으로", "그때 직접", "수치로" 등 구체성을 요구하는 형태
- 면접관이 즉시 사용 가능한 완성된 문장

출력: 우선순위 순으로 정렬된 3~5개 질문
```json
[{"question": "질문", "reasoning": "이 질문을 선택한 이유", "priority": 1}]
```

### 프롬프트 조립 함수

```python
def build_extraction_prompt(resume_text: str, portfolio_text: str = "") -> str:
    """이력서+포트폴리오 텍스트를 받아 완성된 프롬프트 반환"""

def build_value_scoring_prompt(resume_text: str, structured_data: dict) -> str:
    """INTERX_VALUES 전체를 포함하는 완성된 프롬프트"""

def build_reliability_prompt(resume_text: str, portfolio_text: str) -> str: ...

def build_contradiction_prompt(resume_text: str, portfolio_text: str, structured_data: dict) -> str: ...

def build_preemptive_questions_prompt(structured_data: dict, values_scores: dict, contradictions: list) -> str: ...

def build_followup_prompt(resume_summary: dict, question: str, answer: str, history: list) -> str: ...
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
from agents.prompts import (
    INTERX_VALUES,
    build_extraction_prompt,
    build_value_scoring_prompt,
    build_reliability_prompt,
    build_contradiction_prompt,
    build_preemptive_questions_prompt,
    build_followup_prompt,
)

# 12가지 가치 모두 정의됨
assert len(INTERX_VALUES) == 12, f'가치 수 오류: {len(INTERX_VALUES)}'
expected_values = ['목표의식','시간관리','끈기','문제해결','비판적사고','지속적개선','정성스러움','자기동기부여','긍정적태도','솔직한피드백','네트워크활용','호기심']
for v in expected_values:
    assert v in INTERX_VALUES, f'{v} 누락'

# 프롬프트 빌더 동작 확인
dummy_text = '홍길동. 백엔드 개발자. 2021.03~2023.06 ABC회사 재직.'
p1 = build_extraction_prompt(dummy_text)
assert len(p1) > 100, '추출 프롬프트가 너무 짧음'
assert 'JSON' in p1, 'JSON 지시 누락'

p2 = build_value_scoring_prompt(dummy_text, {})
assert '목표의식' in p2 and '호기심' in p2, '가치 누락'
assert '0~100' in p2 or '0-100' in p2, '점수 범위 지시 누락'

p6 = build_followup_prompt({}, '자기소개를 해주세요', '저는 열심히 일합니다', [])
assert len(p6) > 50, '꼬리질문 프롬프트 너무 짧음'

print('모든 프롬프트 검증 통과')
print(f'추출 프롬프트 길이: {len(p1)}자')
print(f'가치 스코어링 프롬프트 길이: {len(p2)}자')
"
```

## AC 검증 방법

위 스크립트 실행 후 에러 없으면 phase 5 status를 `"completed"`로 변경하라.

## 주의사항

- 프롬프트는 **한국어**로 작성. Claude가 한국어로 응답하도록 명시 지시.
- 모든 프롬프트 끝에 "반드시 위 JSON 형식만 반환하고, 다른 텍스트는 포함하지 마세요." 추가.
- `build_value_scoring_prompt`에는 INTERX_VALUES 전체를 프롬프트 안에 인라인으로 삽입. 외부 파일 참조 금지.
- 프롬프트에 "추상적 자기서술은 증거로 인정하지 않는다"를 명시. 이게 평가 정확도의 핵심.
- `build_contradiction_prompt`에는 이력서 텍스트와 포트폴리오 텍스트를 명확히 분리하여 각각의 출처를 표시.
