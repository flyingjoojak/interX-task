# Phase 1: db-models

## 사전 준비

아래 문서를 읽어 전체 DB 설계를 이해하라:

- `docs/data-schema.md` — 6개 테이블 정의, 컬럼 타입, JSON 필드 구조, cascade 정책
- `docs/code-architecture.md` — 폴더 구조, config.py/database.py 역할

이전 phase 산출물:
- `backend/` 폴더 구조 (models/, schemas/, api/, services/, agents/, utils/)
- `backend/requirements.txt`
- `backend/main.py` (기본 FastAPI 앱)

## 작업 내용

### 1. `backend/config.py`

pydantic-settings `BaseSettings`를 사용해 `.env` 파일에서 환경변수를 로드한다.

필드:
- `ANTHROPIC_API_KEY: str`
- `JWT_SECRET: str = "interx-dev-secret-change-in-production"`
- `JWT_ALGORITHM: str = "HS256"`
- `JWT_EXPIRE_HOURS: int = 24`
- `DATABASE_URL: str = "sqlite:///./interx.db"`
- `UPLOAD_DIR: str = "uploads"`
- `MAX_FILE_SIZE_MB: int = 20`

`model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`

싱글턴 `settings = Settings()` export.

### 2. `backend/database.py`

SQLAlchemy 2.x 스타일로 작성.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 전용
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3. SQLAlchemy 모델 (data-schema.md 기준)

각 파일을 `backend/models/` 에 생성하라.

**`models/user.py`** — `users` 테이블
- id: Text PK (UUID4)
- email: Text UNIQUE NOT NULL
- password_hash: Text NOT NULL
- name: Text NOT NULL
- created_at: DateTime NOT NULL (default=utcnow)

**`models/candidate.py`** — `candidates` 테이블
- id: Text PK (UUID4)
- name: Text NOT NULL
- birth_year: Integer nullable
- position: Text nullable
- interviewer_memo: Text nullable
- status: Text NOT NULL default='미분석'
- created_at: DateTime NOT NULL
- updated_at: DateTime NOT NULL (onupdate=utcnow)

**`models/document.py`** — `documents` 테이블
- id: Text PK (UUID4)
- candidate_id: Text FK → candidates.id (ondelete='CASCADE')
- original_name: Text NOT NULL
- file_path: Text NOT NULL
- file_type: Text NOT NULL  (pdf|image|ppt|pptx)
- doc_type: Text NOT NULL  (resume|portfolio)
- ocr_text: Text nullable
- ocr_method: Text nullable  (pymupdf|paddleocr|claude_vision)
- ocr_quality_score: Float nullable
- created_at: DateTime NOT NULL

**`models/analysis.py`** — `analyses` 테이블
- id: Text PK (UUID4)
- candidate_id: Text FK UNIQUE → candidates.id (ondelete='CASCADE')
- structured_data: Text nullable  (JSON)
- values_scores: Text nullable  (JSON)
- doc_reliability_score: Float nullable
- contradictions: Text nullable  (JSON)
- preemptive_questions: Text nullable  (JSON)
- summary: Text nullable
- current_step: Text nullable  (OCR|추출|가치매핑|모순탐지|질문생성|완료|오류)
- step_started_at: DateTime nullable
- created_at: DateTime NOT NULL
- updated_at: DateTime NOT NULL

**`models/interview.py`** — `interview_sessions` + `qa_pairs` 두 테이블 모두 이 파일에 작성
- InterviewSession: id, candidate_id FK UNIQUE, last_accessed_at, created_at
- QAPair: id, session_id FK, question_source (pregenerated|custom|followup), question_text NOT NULL, answer_text nullable, followup_questions nullable (JSON), parent_qa_id self-ref FK nullable, order_index NOT NULL, created_at, answered_at nullable

**`models/__init__.py`** — 모든 모델 import (Base.metadata.create_all이 인식하도록)

```python
from .user import User
from .candidate import Candidate
from .document import Document
from .analysis import Analysis
from .interview import InterviewSession, QAPair
```

### 4. `backend/seed.py`

DB 테이블 생성 + 초기 관리자 계정 생성.

```python
# 실행 시: python seed.py
# - interx.db에 테이블 생성 (이미 있으면 skip)
# - admin@interx.com / interx1234 계정 생성 (이미 있으면 skip)
```

passlib bcrypt로 비밀번호 해싱. 계정이 이미 존재하면 아무 작업 안 함.

출력: `"DB 초기화 완료"`, `"테스트 계정 생성됨: admin@interx.com / interx1234"` 또는 `"테스트 계정 이미 존재"`

### 5. `backend/main.py` 업데이트

DB 초기화 추가:

```python
from database import Base, engine
import models  # 모든 모델 import로 메타데이터 등록

# 앱 시작 시 테이블 생성
Base.metadata.create_all(bind=engine)
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

# 모델 import 확인
python -c "
from database import Base, engine
import models
Base.metadata.create_all(bind=engine)
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
expected = ['users', 'candidates', 'documents', 'analyses', 'interview_sessions', 'qa_pairs']
for t in expected:
    assert t in tables, f'Table {t} missing'
print('All 6 tables created OK:', tables)
"

# seed 실행 확인
python seed.py
```

## AC 검증 방법

두 커맨드 모두 에러 없이 완료되어야 한다. `interx.db` 파일이 `backend/` 폴더에 생성되고 6개 테이블이 모두 존재해야 한다. 성공 시 phase 1 status를 `"completed"`로 변경하라.

## 주의사항

- SQLite foreign key cascade는 SQLAlchemy ORM 레벨에서 `passive_deletes=True` + `ondelete='CASCADE'` 조합으로 처리한다.
- 모든 UUID는 `import uuid; str(uuid.uuid4())`로 생성한다. `default=lambda: str(uuid.uuid4())`.
- DateTime 필드의 `default`는 `datetime.utcnow` (callable, 괄호 없이).
- `interx.db` 파일은 `.gitignore`에 포함되어야 한다 (Phase 0에서 이미 처리됨).
- `config.py`의 `Settings` 클래스는 `backend/` 디렉토리에서 실행할 때 `.env` 파일을 찾아야 한다.
