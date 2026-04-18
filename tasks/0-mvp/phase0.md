# Phase 0: project-setup

## 사전 준비

아래 문서를 읽어 전체 아키텍처와 기술 스택을 이해하라:

- `docs/code-architecture.md` — 폴더 구조, 기술 스택, API 목록
- `docs/prd.md` — 제품 목적, 제약사항

이전 phase 없음 (첫 번째 phase).

## 작업 내용

### 1. 백엔드 폴더 구조 생성

`backend/` 하위에 아래 구조를 생성하라. 각 폴더에 빈 `__init__.py`를 추가하라.

```
backend/
├── models/
├── schemas/
├── api/
├── services/
├── agents/
├── utils/
└── uploads/          ← .gitkeep 파일 추가
```

### 2. `backend/requirements.txt` 생성

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
sqlalchemy>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
pydantic-settings>=2.2.0
python-dotenv>=1.0.0
anthropic>=0.28.0
langchain>=0.2.0
langgraph>=0.1.0
langchain-anthropic>=0.1.0
pymupdf>=1.24.0
paddleocr>=2.7.0
paddlepaddle>=2.6.0
python-pptx>=0.6.23
Pillow>=10.0.0
filetype>=1.2.0
playwright>=1.44.0
aiofiles>=23.0.0
httpx>=0.27.0
```

### 3. `backend/requirements.txt` 핵심 패키지 설치

```bash
cd backend
pip install fastapi uvicorn[standard] sqlalchemy python-jose[cryptography] passlib[bcrypt] pydantic-settings python-dotenv anthropic langchain langgraph langchain-anthropic pymupdf python-pptx Pillow filetype playwright aiofiles httpx python-multipart
```

PaddleOCR/PaddleOCR은 Phase 4에서 별도 설치. 지금은 설치하지 않아도 된다.

Playwright chromium 설치:
```bash
playwright install chromium
```

### 4. 프론트엔드 Next.js 14 프로젝트 생성

프로젝트 루트(`C:/Users/main/Downloads/interX/`)에서 실행:

```bash
npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*" --no-git
```

위 명령이 대화형으로 물어볼 경우 모두 기본값(Yes/No) 선택. TypeScript, Tailwind CSS, App Router 사용.

설치 완료 후:
```bash
cd frontend
npm install recharts axios
```

### 5. `.gitignore` 생성 (프로젝트 루트)

```
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
env/
*.egg-info/
dist/
build/

# Env
.env
backend/.env

# DB
*.db

# Uploads (실제 파일)
backend/uploads/*
!backend/uploads/.gitkeep

# Node
frontend/node_modules/
frontend/.next/
frontend/out/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Task outputs (JSON은 커밋, 대용량 output만 제외)
tasks/**/*-output.json
```

### 6. `.env.example` 생성 (프로젝트 루트)

```
ANTHROPIC_API_KEY=sk-ant-여기에_API_키_입력
JWT_SECRET=여기에_긴_랜덤_문자열_입력
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
BACKEND_PORT=8102
FRONTEND_PORT=3102
```

### 7. 빈 `backend/main.py` 생성

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="InterX API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3102"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

## Acceptance Criteria

```bash
# 백엔드 핵심 패키지 import 확인
cd C:/Users/main/Downloads/interX/backend
python -c "import fastapi, sqlalchemy, anthropic, langgraph, fitz, python_jose, passlib; print('backend deps OK')"

# 프론트엔드 빌드 확인
cd C:/Users/main/Downloads/interX/frontend
npm run build
```

## AC 검증 방법

위 두 커맨드를 순서대로 실행하라. 둘 다 성공하면 `tasks/0-mvp/index.json`의 phase 0 status를 `"completed"`로 변경하라.

`python -c` 실행 시 ModuleNotFoundError가 발생하면 해당 패키지를 pip install하고 재시도하라. 수정 3회 이상 시도해도 실패하면 status를 `"error"`로, error_message에 구체적 에러 내용을 기록하라.

## 주의사항

- `backend/.env`는 이미 존재한다 (ANTHROPIC_API_KEY 포함). 덮어쓰지 마라.
- `.gitignore`에 `backend/.env`가 포함되어야 한다. 환경변수 파일이 커밋되면 안 된다.
- `backend/uploads/` 폴더는 `.gitkeep`만 커밋되고 실제 업로드 파일은 커밋되지 않아야 한다.
- PaddleOCR은 이 phase에서 설치하지 않는다. requirements.txt에만 기록한다.
- `frontend/` 폴더는 `create-next-app`이 생성한 기본 구조를 유지하라. 불필요한 예시 파일(app/page.tsx 기본 내용 등)은 나중 phase에서 교체된다.
