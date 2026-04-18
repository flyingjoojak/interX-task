# Data Schema — InterX 채용 솔루션

## DB: SQLite / ORM: SQLAlchemy
파일 위치: `backend/interx.db`

---

## 테이블 정의

### users
면접관 계정. 초기 계정은 시드 스크립트로 생성, 추가는 개발자 직접.
모든 면접관은 모든 후보자 데이터 공유.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| email | TEXT | UNIQUE NOT NULL | 로그인 ID |
| password_hash | TEXT | NOT NULL | bcrypt |
| name | TEXT | NOT NULL | 표시 이름 |
| created_at | DATETIME | NOT NULL | |

---

### candidates
후보자 기본정보 + 현재 상태.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| name | TEXT | NOT NULL | 표시 이름 |
| birth_year | INTEGER | | 생년 |
| position | TEXT | | 지원 포지션 |
| interviewer_memo | TEXT | | 면접관 메모 |
| status | TEXT | DEFAULT '미분석' | 아래 ENUM |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |

**status 값:**
- 자동 전환 (시스템): `미분석` → `분석중` → `분석완료`
- 수동 설정 (면접관, 자유롭게 변경/되돌리기 가능):
  `서류합격` `서류탈락` `면접합격` `면접탈락` `최종합격` `최종탈락`

---

### documents
업로드된 파일 + OCR 결과. 후보자당 최대 2개 (이력서 1 + 포트폴리오 1).

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| candidate_id | TEXT | FK → candidates.id | |
| original_name | TEXT | NOT NULL | 원본 파일명 |
| file_path | TEXT | NOT NULL | uploads/{candidate_id}/{uuid}.{ext} |
| file_type | TEXT | NOT NULL | `pdf` `image` `ppt` `pptx` |
| doc_type | TEXT | NOT NULL | `resume` `portfolio` |
| ocr_text | TEXT | | 추출된 전체 텍스트 |
| ocr_method | TEXT | | `pymupdf` `paddleocr` `claude_vision` |
| ocr_quality_score | REAL | | 0.0~1.0, fallback 판단 기준 |
| created_at | DATETIME | NOT NULL | |

**파일 허용 형식:**
- resume: PDF, JPG, PNG, PPT, PPTX
- portfolio: PDF, JPG, PNG (PPT/PPTX 미지원)

**OCR 파이프라인:**
- resume: PyMuPDF → (낮은 품질) PaddleOCR → (낮은 품질) Claude Vision
- portfolio: 전부 이미지 변환 후 Claude Vision (PDF는 PyMuPDF 페이지 렌더링)

---

### analyses
AI 분석 결과. 후보자당 1개 (재분석 시 덮어씀).

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| candidate_id | TEXT | FK UNIQUE → candidates.id | 1:1 |
| structured_data | TEXT | | JSON — 경력/학력/기술/성과 구조화 |
| values_scores | TEXT | | JSON — 12가지 가치별 결과 |
| doc_reliability_score | REAL | | 0~100 (일치도+신뢰도+완성도) |
| contradictions | TEXT | | JSON — 탐지된 모순 목록 |
| preemptive_questions | TEXT | | JSON — 사전 압박질문 목록 |
| summary | TEXT | | 종합 요약 |
| current_step | TEXT | | 진행 단계 (아래 참조) |
| step_started_at | DATETIME | | 예상 시간 계산용 |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |

**current_step 값:** `OCR` `추출` `가치매핑` `모순탐지` `질문생성` `완료` `오류`

**values_scores JSON 구조:**
```json
{
  "목표의식": { "score": 85, "evidence": "...", "examples": ["..."] },
  "시간관리": { "score": 72, "evidence": "...", "examples": ["..."] },
  ...
}
```

**contradictions JSON 구조:**
```json
[
  {
    "source_a": "이력서 3페이지",
    "source_b": "포트폴리오 1페이지",
    "description": "재직 기간 불일치 (2021.03~2022.06 vs 2021.03~2022.12)",
    "severity": "high"
  }
]
```

**preemptive_questions JSON 구조:**
```json
[
  {
    "question": "포트폴리오에 기재된 재직 기간과 이력서의 기간이 다릅니다. 실제 재직 기간은 언제까지였나요?",
    "target_value": "정성스러움",
    "basis": "문서 간 날짜 불일치"
  }
]
```

---

### interview_sessions
면접 세션. 후보자당 1개, 재시작 시 Q&A 초기화 후 재사용.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| candidate_id | TEXT | FK UNIQUE → candidates.id | 1:1 |
| last_accessed_at | DATETIME | | 세션 재개 판단용 |
| created_at | DATETIME | NOT NULL | |

---

### qa_pairs
Q&A 기록. 시간순 선형 누적 (채팅형).

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | TEXT | PK | UUID4 |
| session_id | TEXT | FK → interview_sessions.id | |
| question_source | TEXT | NOT NULL | `pregenerated` `custom` `followup` |
| question_text | TEXT | NOT NULL | |
| answer_text | TEXT | | NULL = 미답변 |
| followup_questions | TEXT | | JSON — 생성된 꼬리질문 목록 |
| parent_qa_id | TEXT | FK → qa_pairs.id | followup 컨텍스트 연결용 |
| order_index | INTEGER | NOT NULL | 화면 표시 순서 |
| created_at | DATETIME | NOT NULL | |
| answered_at | DATETIME | | |

**followup_questions JSON 구조:**
```json
[
  {
    "question": "당시 팀원이 몇 명이었고, 본인이 직접 내린 결정 중 가장 어려웠던 것은 무엇인가요?",
    "reasoning": "답변이 추상적이고 구체적 경험 근거 부재",
    "priority": 1
  }
]
```

---

## 관계 다이어그램
```
users (공유 접근, 별도 FK 없음)

candidates
  ├── documents (1:N, cascade delete)
  ├── analyses (1:1, cascade delete)
  └── interview_sessions (1:1, cascade delete)
        └── qa_pairs (1:N, cascade delete)
              └── qa_pairs (self-ref, parent_qa_id)
```

## Cascade 정책
후보자 삭제 시: documents(파일 포함) + analyses + interview_sessions + qa_pairs 전부 삭제
재분석 시: analyses 덮어쓰기 + interview_sessions Q&A 초기화
