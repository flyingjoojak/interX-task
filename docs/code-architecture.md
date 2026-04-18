# Code Architecture — InterX 채용 솔루션

## 기술 스택
| 레이어 | 기술 | 버전 기준 |
|--------|------|----------|
| Backend | FastAPI + Uvicorn | Python 3.11+ |
| Frontend | Next.js + Tailwind CSS + Recharts | Next.js 14 |
| ORM | SQLAlchemy | 2.x |
| DB | SQLite | interx.db |
| AI 모델 | Claude claude-sonnet-4-6 API | Anthropic SDK |
| Agent | LangGraph | LangChain 0.2+ |
| OCR | PyMuPDF + PaddleOCR | |
| PDF 출력 | Playwright | Python |
| 인증 | JWT | python-jose + bcrypt |
| PPT 추출 | python-pptx | 이력서 한정 |

---

## 폴더 구조

```
interX/
├── backend/
│   ├── main.py                    # FastAPI 앱, CORS, 라우터 등록, 시작점
│   ├── config.py                  # pydantic BaseSettings, .env 로드
│   ├── database.py                # engine, SessionLocal, Base, get_db
│   ├── seed.py                    # 초기 테스트 계정 생성 스크립트
│   │
│   ├── models/                    # SQLAlchemy ORM 모델 (DB 테이블 정의)
│   │   ├── user.py
│   │   ├── candidate.py
│   │   ├── document.py
│   │   ├── analysis.py
│   │   └── interview.py           # interview_sessions + qa_pairs
│   │
│   ├── schemas/                   # Pydantic 요청/응답 직렬화
│   │   ├── auth.py
│   │   ├── candidate.py
│   │   ├── analysis.py
│   │   └── interview.py
│   │
│   ├── api/                       # FastAPI 라우터 (얇은 레이어, 로직은 services로)
│   │   ├── auth.py                # POST /auth/login, POST /auth/refresh
│   │   ├── candidates.py          # CRUD + 상태변경 + 삭제
│   │   ├── documents.py           # 파일 업로드/삭제
│   │   ├── analysis.py            # 분석 트리거 + 진행상태 폴링
│   │   └── interview.py           # 세션 관리 + Q&A + 꼬리질문 생성
│   │
│   ├── services/                  # 비즈니스 로직
│   │   ├── ocr_service.py         # OCR 파이프라인 (PyMuPDF→PaddleOCR→Claude Vision)
│   │   ├── portfolio_service.py   # 포트폴리오 이미지 변환 + Claude Vision
│   │   ├── ppt_service.py         # python-pptx 텍스트 추출 (이력서 한정)
│   │   ├── anonymizer.py          # PII 탐지/마스킹/역매핑
│   │   ├── analysis_runner.py     # LangGraph 실행 + DB 단계별 상태 업데이트
│   │   └── pdf_export.py          # Playwright PDF 생성
│   │
│   ├── agents/                    # LangGraph 그래프 정의
│   │   ├── analysis_graph.py      # 사전 분석 8단계 그래프
│   │   ├── interview_graph.py     # 실시간 꼬리질문 그래프
│   │   └── prompts.py             # 한국어 프롬프트 전체 (분리 관리)
│   │
│   ├── utils/
│   │   ├── logger.py              # PII 마스킹 로거
│   │   └── file_validator.py      # 확장자 + MIME + 크기(20MB) 검증
│   │
│   ├── uploads/                   # {candidate_id}/{uuid}.{ext}
│   ├── interx.db                  # SQLite DB
│   ├── .env                       # ANTHROPIC_API_KEY, JWT_SECRET 등
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # 글로벌 레이아웃, 헤더
│   │   ├── page.tsx               # /home — 후보자 목록 + 간이 비교
│   │   ├── login/page.tsx         # /login
│   │   └── candidates/
│   │       ├── new/page.tsx       # /candidates/new — 등록
│   │       └── [id]/
│   │           ├── page.tsx       # /candidates/{id} — 리포트 (진행중/완료)
│   │           └── interview/
│   │               └── page.tsx   # /candidates/{id}/interview — 면접
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   └── Header.tsx
│   │   ├── home/
│   │   │   ├── CandidateCard.tsx  # 이름/포지션/상태/점수 카드
│   │   │   └── StatusFilter.tsx
│   │   ├── report/
│   │   │   ├── AnalysisProgress.tsx   # 단계별 진행률 바 + 예상시간
│   │   │   ├── ValueRadarChart.tsx    # Recharts 레이더 차트
│   │   │   ├── ValueScoreList.tsx     # 12개 점수 바 리스트
│   │   │   ├── EvidencePanel.tsx      # 클릭 시 슬라이드 근거 패널
│   │   │   ├── ContradictionList.tsx  # 모순 탐지 목록
│   │   │   └── PreemptiveQuestions.tsx
│   │   ├── interview/
│   │   │   ├── LeftSidebar.tsx        # 사전분석 요약 + 사전질문 리스트
│   │   │   ├── QATimeline.tsx         # 채팅형 Q&A 히스토리
│   │   │   ├── AnswerInput.tsx        # 현재질문 표시 + 답변 입력 + 분석버튼
│   │   │   └── FollowupPanel.tsx      # 토글 가능한 꼬리질문 패널
│   │   └── ui/                        # Button, Badge, Card, Modal, Spinner 등
│   │
│   ├── lib/
│   │   ├── api.ts                 # Axios 인스턴스 + JWT 헤더 처리
│   │   └── types.ts               # TypeScript 타입 전체 정의
│   │
│   └── package.json
│
├── docs/                          # 설계 문서
├── start.bat                      # 백엔드 + 프론트엔드 동시 실행
└── .env.example
```

---

## API 엔드포인트

### 인증
```
POST /api/auth/login              { email, password } → { access_token }
POST /api/auth/refresh            → { access_token }
```

### 후보자
```
GET    /api/candidates/           목록 (상태 필터 쿼리 파라미터)
POST   /api/candidates/           등록 { name, birth_year, position, memo }
GET    /api/candidates/{id}       상세
PATCH  /api/candidates/{id}       기본정보 수정
PATCH  /api/candidates/{id}/status  상태 변경 { status }
DELETE /api/candidates/{id}       삭제 (cascade)
```

### 문서
```
POST   /api/candidates/{id}/documents   파일 업로드 (multipart, doc_type 포함)
DELETE /api/documents/{doc_id}          파일 삭제
```

### 분석
```
POST   /api/candidates/{id}/analysis          분석 시작 (BackgroundTask)
GET    /api/candidates/{id}/analysis          분석 결과 전체
GET    /api/candidates/{id}/analysis/progress 현재 단계 + 예상 남은 시간
DELETE /api/candidates/{id}/analysis          분석 초기화 (재분석 전처리)
GET    /api/candidates/{id}/report/pdf        통합 PDF 생성 및 다운로드
```

### 면접
```
POST   /api/candidates/{id}/interview/session   세션 생성 or 기존 반환
GET    /api/candidates/{id}/interview/session   세션 + Q&A 전체 조회
DELETE /api/candidates/{id}/interview/session   세션 초기화 (새로 시작)
POST   /api/interview/qa                        { session_id, question_source, question_text } → qa_pair 생성
PATCH  /api/interview/qa/{qa_id}                { answer_text } → 꼬리질문 생성 트리거
```

---

## LangGraph 에이전트

### 사전 분석 그래프 (analysis_graph.py)
```
parse_documents
  → extract_structured_data     (Claude API: 경력/학력/기술 JSON 추출)
  → anonymize_pii               (로컬: 이름/연락처 마스킹, pii_map 생성)
  → score_12_values             (Claude API: 각 가치 0~100 + 근거)
  → calculate_doc_reliability   (Claude API: 문서 일치도/신뢰도/완성도)
  → detect_contradictions       (Claude API: 문서 내/간 모순 탐지)
  → generate_preemptive_questions (Claude API: 모순 기반 압박질문)
  → compile_report              (로컬: 구조체 조립)
  → restore_pii                 (로컬: 익명화 역매핑 복원)

각 노드 시작 시 analyses.current_step + step_started_at DB 업데이트
→ 프론트 폴링이 이를 읽어 진행률 계산
```

### 실시간 면접 그래프 (interview_graph.py)
```
prepare_context       (이력서 구조화 데이터 + 대화 히스토리 로드)
  → analyze_answer    (Claude API: 모호성/불일치/과장 분석)
  → generate_followups (Claude API: 압박 꼬리질문 3~5개 생성)
  → rank_and_filter   (우선순위 정렬, 상위 5개 반환)

목표 응답시간: 10초 이내
```

---

## 핵심 서비스 로직

### OCR Service (이력서)
```python
1. PyMuPDF로 텍스트 추출 → quality_score 계산
2. quality_score < 0.7 → PaddleOCR
3. quality_score < 0.7 → Claude Vision API (페이지 이미지 전송)
4. ocr_method, ocr_text, ocr_quality_score DB 저장
```

### Portfolio Service
```python
1. PDF → PyMuPDF로 각 페이지 PNG 렌더링
2. JPG/PNG → 그대로 사용
3. 모든 이미지 → Claude Vision API (페이지별 순차 처리)
4. 결과 텍스트 통합
```

### Anonymizer
```python
# 전송 전
text, pii_map = anonymize(raw_text)
# "홍길동" → "지원자A", "010-1234-5678" → "[연락처]"

# 결과 수신 후
result = restore_pii(api_response, pii_map)
```

### Analysis Runner
```python
# FastAPI BackgroundTasks로 실행
async def run_analysis(candidate_id: str, db: Session):
    state = build_initial_state(candidate_id, db)
    result = await analysis_graph.ainvoke(state)
    save_result_to_db(result, db)
    update_candidate_status(candidate_id, "분석완료", db)
```

---

## 보안 레이어
| 항목 | 구현 |
|------|------|
| 인증 | JWT Bearer 토큰, 모든 /api/* 엔드포인트 보호 |
| 비밀번호 | bcrypt 해싱 |
| CORS | localhost:3102만 허용 |
| 파일 검증 | 확장자 + python-magic MIME 타입 + 20MB 제한 |
| PII 보호 | Claude API 전송 전 익명화, 결과 수신 후 복원 |
| 로그 마스킹 | name/contact 필드 *** 처리 |
| 환경변수 | .env 파일 분리, 코드에 키 하드코딩 금지 |

---

## start.bat
```bat
@echo off
echo InterX 서버를 시작합니다...

:: 백엔드 (port 8102)
start "InterX Backend" cmd /k "cd backend && python seed.py && uvicorn main:app --reload --port 8102"

:: 프론트엔드 (port 3102)
start "InterX Frontend" cmd /k "cd frontend && npm run dev -- --port 3102"

echo.
echo Backend : http://localhost:8102
echo Frontend: http://localhost:3102
echo API Docs: http://localhost:8102/docs
```
