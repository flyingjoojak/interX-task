import json


INTERX_VALUES: dict[str, str] = {
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


JSON_ONLY_SUFFIX = "반드시 위 JSON 형식만 반환하고, 다른 텍스트는 포함하지 마세요."

KOREAN_INSTRUCTION = "모든 응답은 한국어로 작성하세요."


STRUCTURED_EXTRACTION_PROMPT = """당신은 한국어 이력서/포트폴리오 분석 전문가입니다. 아래 텍스트에서 구조화된 데이터를 추출하세요.

[추출 지침]
- 한국 이력서 특성을 반영하여 직책/직급(예: 사원, 대리, 과장)과 고용 형태(정규직/인턴/계약직)를 가능한 구분해 `role`에 명시.
- 연봉/성과 수치가 있다면 반드시 `quantified_result`에 원문 그대로 기재(예: "매출 30% 향상", "연봉 5,400만원").
- 날짜는 반드시 `YYYY.MM` 형식으로 통일. 재직 중이면 `end`를 `재직중`으로 표기. 월 정보가 없으면 `YYYY.01`로 보정.
- 원문에 없는 정보는 추측하지 말고 해당 필드를 빈 문자열("") 또는 빈 배열([])로 두세요.
- 동일 경력이 여러 번 언급되면 한 번만 기록하되, 상세 설명은 가장 구체적인 쪽을 선택.

[출력 JSON 스키마]
{{
  "career": [
    {{"company": "", "role": "", "start": "YYYY.MM", "end": "YYYY.MM or 재직중", "description": ""}}
  ],
  "education": [
    {{"school": "", "major": "", "degree": "", "start": "YYYY.MM", "end": "YYYY.MM"}}
  ],
  "skills": ["기술1", "기술2"],
  "achievements": [
    {{"title": "", "description": "", "quantified_result": "수치화된 성과 (없으면 null)"}}
  ],
  "certifications": [
    {{"name": "", "issuer": "", "date": "YYYY.MM"}}
  ],
  "projects": [
    {{"name": "", "role": "", "period": "", "description": "", "tech_stack": []}}
  ]
}}

[이력서 텍스트]
{resume_text}

[포트폴리오 텍스트]
{portfolio_text}

{korean_instruction}
{json_only_suffix}
"""


VALUE_SCORING_PROMPT = """당신은 인터엑스 채용 심사관입니다. 아래 12가지 핵심가치 각각에 대해 후보자의 이력서를 0~100점으로 평가하세요.

[12가지 핵심가치 정의]
{values_block}

[점수 원칙]
- 점수 범위: 0~100. 증거가 전혀 없거나 모호하면 0~30, 부분적이면 30~60, 충분한 구체적 증거와 일관성이 있으면 80 이상.
- 80점 기준: "충분한 구체적 증거(수치, 프로젝트, 행동 결과)가 있고 가치 정의와 일관되는 행동이 반복적으로 관찰되는 경우"에 부여.
- 추상적 자기서술(예: "열정적입니다", "성실합니다", "책임감이 강합니다")은 증거로 인정하지 않습니다. 반드시 행동/결과/수치로 뒷받침되는 내용만 증거로 채택하세요.
- 증거가 없는 가치는 0~30점을 부여하고, `examples`는 빈 배열로 둡니다.
- `evidence`는 점수의 근거를 1~2문장으로 요약. `examples`에는 이력서의 구체 문장을 원문 그대로 1~3개 인용.

[후보자 구조화 데이터(참고)]
{structured_data}

[이력서 원문]
{resume_text}

[출력 JSON 스키마]
{{
  "목표의식":   {{"score": 0, "evidence": "", "examples": []}},
  "시간관리":   {{"score": 0, "evidence": "", "examples": []}},
  "끈기":       {{"score": 0, "evidence": "", "examples": []}},
  "문제해결":   {{"score": 0, "evidence": "", "examples": []}},
  "비판적사고": {{"score": 0, "evidence": "", "examples": []}},
  "지속적개선": {{"score": 0, "evidence": "", "examples": []}},
  "정성스러움": {{"score": 0, "evidence": "", "examples": []}},
  "자기동기부여": {{"score": 0, "evidence": "", "examples": []}},
  "긍정적태도": {{"score": 0, "evidence": "", "examples": []}},
  "솔직한피드백": {{"score": 0, "evidence": "", "examples": []}},
  "네트워크활용": {{"score": 0, "evidence": "", "examples": []}},
  "호기심":     {{"score": 0, "evidence": "", "examples": []}}
}}

{korean_instruction}
{json_only_suffix}
"""


DOC_RELIABILITY_PROMPT = """당신은 채용 문서의 신뢰도를 평가하는 심사관입니다. 아래 이력서와 포트폴리오를 읽고 0~100점으로 평가하세요.

[평가 기준]
1) 일치도 (40점 만점): 문서 내부 및 문서 간 정보의 일관성. 날짜, 직책, 성과 수치가 서로 충돌하지 않을수록 높게.
2) 신뢰도 (30점 만점): 성과 수치의 구체성, 검증 가능성, 과장 가능성. 구체적 수치와 맥락이 있을수록 높게, 1인칭 과장 주장일수록 낮게.
3) 완성도 (30점 만점): 필수 정보(경력, 학력, 연락처, 주요 프로젝트) 기재의 충실도.

[출력 지침]
- `score`는 세 항목 점수의 합(0~100).
- `breakdown`에 각 항목별 실제 부여 점수를 기재.
- `issues`에는 발견된 구체적 문제점을 원문 인용 또는 간결한 설명으로 나열. 문제가 없으면 빈 배열.

[이력서 텍스트]
{resume_text}

[포트폴리오 텍스트]
{portfolio_text}

[출력 JSON 스키마]
{{
  "score": 0,
  "breakdown": {{"consistency": 0, "credibility": 0, "completeness": 0}},
  "issues": ["문제점1", "문제점2"]
}}

{korean_instruction}
{json_only_suffix}
"""


CONTRADICTION_DETECTION_PROMPT = """당신은 이력서/포트폴리오의 모순과 불일치를 탐지하는 심사관입니다. 이력서 내부의 모순뿐 아니라 이력서↔포트폴리오 간 불일치도 찾아내세요.

[탐지 대상]
- 날짜/기간 불일치: 재직 기간 겹침, 학업과 직장 기간 중복 이상, 프로젝트 기간과 회사 재직 기간 불일치.
- 직책/역할 불일치: 동일 경험을 다른 직책/역할로 기술한 경우.
- 성과 수치 불일치: 동일 프로젝트의 성과를 서로 다르게 기재(예: 매출 30% vs 50%).
- 기술 스택 불일치: 한쪽에서는 경험이 없다가 다른 쪽에서 사용했다고 표기.

[심각도 분류]
- high: 명백한 수치/날짜 오류, 설명이 불가능한 직접적 모순.
- medium: 부분적 불일치, 해석에 따라 다를 수 있는 차이.
- low: 표현 방식의 차이, 의도적 생략 가능성이 있는 경미한 불일치.

[출력 지침]
- `source_a`, `source_b`에는 출처를 "이력서", "포트폴리오", 또는 구체적 위치(예: "이력서: 경력 3번째", "포트폴리오: 프로젝트 설명")로 표기.
- 동일 문서 내 모순이면 `source_b`에도 동일 문서 내 다른 위치를 명시.
- 모순이 발견되지 않으면 빈 배열 `[]`을 반환.

[이력서 원문]
---RESUME START---
{resume_text}
---RESUME END---

[포트폴리오 원문]
---PORTFOLIO START---
{portfolio_text}
---PORTFOLIO END---

[후보자 구조화 데이터(참고)]
{structured_data}

[출력 JSON 스키마]
[
  {{"source_a": "문서/위치", "source_b": "문서/위치", "description": "불일치 내용", "severity": "high|medium|low"}}
]

{korean_instruction}
{json_only_suffix}
"""


PREEMPTIVE_QUESTIONS_PROMPT = """당신은 실제 경험 여부를 검증하는 압박 면접 질문을 설계하는 면접 코치입니다. 아래 모순과 낮은 가치 점수를 근거로 사전 압박 질문을 생성하세요.

[질문 생성 원칙]
- 모순 항목 하나당 최소 1개의 직접적 확인 질문을 생성.
- 40점 미만 가치에 대해서는 해당 가치의 실제 경험을 드릴다운하는 구체 질문을 생성.
- "~에 대해 말씀해주세요" 형태의 개방형 질문은 금지. 반드시 구체 수치, 인원, 시점, 결과 등 세부사항을 묻는 형태로 작성.
- 예) "당시 팀원은 몇 명이었고, 본인이 직접 내린 결정 중 가장 어려웠던 것은 무엇인가요?"
- AI가 생성한 답변자는 구체적 세부사항을 모르므로, 반드시 세부사항에 대한 질문으로 실제 경험을 검증할 수 있어야 함.
- `target_value`는 관련 핵심가치명(12가지 중 하나) 또는 모순 확인 질문인 경우 null.
- `basis`에는 이 질문을 하는 근거(모순 요약 또는 낮은 점수 가치)를 1문장으로 기술.

[구조화 데이터]
{structured_data}

[12가지 가치 점수 결과]
{values_scores}

[탐지된 모순 목록]
{contradictions}

[출력 JSON 스키마]
[
  {{"question": "질문 내용", "target_value": "관련 핵심가치명 or null", "basis": "이 질문을 하는 근거"}}
]

{korean_instruction}
{json_only_suffix}
"""


INTERVIEW_FOLLOWUP_PROMPT = """당신은 실시간 면접에서 면접관에게 즉시 사용 가능한 압박 꼬리질문을 제공하는 AI 보조자입니다. 후보자의 답변에서 가장 취약한 지점을 파고드는 꼬리질문 3~5개를 생성하세요.

[분석 항목]
- 모호성: 추상적 표현, 수치 없는 성과, "열심히 했습니다"류의 답변.
- 불일치: 이력서와 답변 간 사실관계 차이(날짜, 직책, 역할, 성과).
- 과장 가능성: 검증 불가능한 성과 주장, 팀 성과를 1인칭 공로로 가져가는 듯한 표현.

[꼬리질문 원칙]
- 답변의 가장 취약한 지점 1~2개를 정확히 파고들어야 함.
- "구체적으로", "그때 직접", "수치로", "당시 팀원은 몇 명", "본인이 내린 결정" 등 구체성을 요구하는 문장 형태.
- 면접관이 즉시 읽고 사용할 수 있는 완성된 한 문장의 질문으로 작성.
- 우선순위 순으로 정렬(priority 1이 가장 중요).
- `reasoning`에는 이 질문을 선택한 이유(어떤 취약점을 노리는지)를 1~2문장으로.

[이력서 요약(구조화 데이터)]
{resume_summary}

[이전 Q&A 히스토리(최근 3개)]
{history}

[현재 질문]
{question}

[후보자 답변]
{answer}

[출력 JSON 스키마]
[
  {{"question": "질문", "reasoning": "이 질문을 선택한 이유", "priority": 1}}
]

{korean_instruction}
{json_only_suffix}
"""


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _values_block() -> str:
    lines = [f"- {name}: {desc}" for name, desc in INTERX_VALUES.items()]
    return "\n".join(lines)


def build_extraction_prompt(resume_text: str, portfolio_text: str = "") -> str:
    return STRUCTURED_EXTRACTION_PROMPT.format(
        resume_text=resume_text or "(없음)",
        portfolio_text=portfolio_text or "(없음)",
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


def build_value_scoring_prompt(resume_text: str, structured_data: dict) -> str:
    return VALUE_SCORING_PROMPT.format(
        values_block=_values_block(),
        structured_data=_dumps(structured_data or {}),
        resume_text=resume_text or "(없음)",
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


def build_reliability_prompt(resume_text: str, portfolio_text: str) -> str:
    return DOC_RELIABILITY_PROMPT.format(
        resume_text=resume_text or "(없음)",
        portfolio_text=portfolio_text or "(없음)",
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


def build_contradiction_prompt(
    resume_text: str, portfolio_text: str, structured_data: dict
) -> str:
    return CONTRADICTION_DETECTION_PROMPT.format(
        resume_text=resume_text or "(없음)",
        portfolio_text=portfolio_text or "(없음)",
        structured_data=_dumps(structured_data or {}),
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


def build_preemptive_questions_prompt(
    structured_data: dict, values_scores: dict, contradictions: list
) -> str:
    return PREEMPTIVE_QUESTIONS_PROMPT.format(
        structured_data=_dumps(structured_data or {}),
        values_scores=_dumps(values_scores or {}),
        contradictions=_dumps(contradictions or []),
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


def build_followup_prompt(
    resume_summary: dict, question: str, answer: str, history: list
) -> str:
    recent = (history or [])[-3:]
    return INTERVIEW_FOLLOWUP_PROMPT.format(
        resume_summary=_dumps(resume_summary or {}),
        history=_dumps(recent),
        question=question or "(없음)",
        answer=answer or "(없음)",
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )
