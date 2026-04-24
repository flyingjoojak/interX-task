# interX — AI 면접 솔루션

interX는 AI 기반 면접 솔루션입니다. 면접관이 지원자 이력서/포트폴리오를 업로드하면, AI가 12가지 핵심가치 기준으로 분석하고 후속 질문을 생성합니다.

## 기술 스택

- **백엔드**: FastAPI (Python), SQLite, LangGraph Agents
- **프론트엔드**: Next.js 14, React 18, TypeScript, Recharts, Tailwind CSS
- **AI**: Anthropic Claude API

## 프로젝트 구조

```
interX/
├── backend/              # FastAPI 백엔드
│   ├── api/             # REST API 라우터 (auth, candidates, documents, analysis, interview)
│   ├── agents/          # LangGraph 에이전트 (면접/분석)
│   ├── models/         # SQLAlchemy 모델
│   ├── schemas/        # Pydantic 스키마
│   ├── services/       # 비즈니스 로직 (OCR, PDF 내보내기, 익명화 등)
│   ├── utils/         # 유틸리티 (JWT, 파일 검증, 로거)
│   ├── main.py         # FastAPI 진입점
│   └── config.py      # 설정
├── frontend/          # Next.js 프론트엔드
│   ├── app/           # Next.js 앱 라우터 페이지
│   ├── components/   # React 컴포넌트
│   └── package.json  # 의존성
├── docs/              # 문서 (PRD, ADR, 아키텍처 등)
└── scripts/          # 유틸리티 스크립트
```

## 12가지 핵심가치

| # | 가치명 | 키워드 |
|---|--------|--------|
| 1 | 목표의식 | 선도적, 정량 목표, 마일스톤 수치화 |
| 2 | 시간관리 | AI 활용 자동화, 마감기한 엄수 |
| 3 | 끈기 | 실패 후 재실행, 모호함 속 해답 도출 |
| 4 | 문제해결 | 고객 공감, 구조적 재발 방지 |
| 5 | 비판적사고 | 데이터 기반, 기존 경험 비판적 통찰 |
| 6 | 지속적개선 | AI/신기술 도입, 프로세스 혁신 |
| 7 | 정성스러움 | 반복 실수 방지, 최고 수준 결과물 |
| 8 | 자기동기부여 | 업무 의미 인식, 자율적 성장 |
| 9 | 긍정적태도 | 위기 속 낙천성, 주변 사기 영향 |
| 10 | 솔직한피드백 | 정기적 피드백 요청/수용 |
| 11 | 네트워크활용 | 이해관계자 전략적 네트워크 |
| 12 | 호기심 | 새 분야 학습 지속, 선제적 실무 적용 |

## 시작하기

### 필수 조건

- Python 3.10+
- Node.js 18+
- Anthropic API Key

### 백엔드 설정

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Unix

pip install -r requirements.txt

# .env 파일 생성
copy ..env.example .env
# .env에 ANTHROPIC_API_KEY 입력

python main.py
```

백엔드는 http://localhost:3101에서 실행

### 프론트엔드 설정

```bash
cd frontend
npm install

npm run dev
```

프론트엔드는 http://localhost:3102에서 실행

### 둘 다 시작

```bash
.\start.bat
```

## 주요 기능

- **이력서/포트폴리오 업로드**: PDF, JPG, PNG, PPT, PPTX
- **OCR 처리**: 텍스트 추출 및 구조화 분석
- **12가지 가치 점수화**: 12가지 핵심가치로 지원자 평가
- **모순 탐지**: 이력서 데이터 교차 검증
- **후속 질문 생성**: AI 기반 면접 질문 생성
- **실시간 면접**: 실시간 Q&A 및 후속 질문 패널
- **의사결정 대시보드**: 레이더 차트, 근거 패널, PDF 내보내기
- **9단계 지원자 관리**: 지원자 진행 상황 추적

## API 엔드포인트

- `POST /api/auth/login` — JWT 로그인
- `GET/POST /api/candidates` — 지원자 관리
- `POST /api/documents/upload` — 문서 업로드 (OCR 포함)
- `POST /api/analysis/run` — 분석 실행
- `GET /api/interview/{id}` — 면��� 세션 조회
- `POST /api/interview/{id}/answer` — 답변 제출

## 라이선스

MIT