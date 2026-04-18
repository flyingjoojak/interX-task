# Phase 13: integration

## 사전 준비

모든 이전 phase 산출물이 완료되어 있다고 가정.

## 작업 내용

### 1. CORS 설정 확인 및 수정

`backend/main.py`에 프론트엔드 포트(3102) 허용 확인:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3102", "http://127.0.0.1:3102"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

이미 설정되어 있으면 스킵.

### 2. `start.bat` — 통합 실행 스크립트

```bat
@echo off
echo InterX MVP 시작 중...

REM 백엔드 시작
start "InterX Backend" cmd /k "cd /d C:\Users\main\Downloads\interX\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8102 --reload"

REM 프론트엔드 시작
start "InterX Frontend" cmd /k "cd /d C:\Users\main\Downloads\interX\frontend && npm run dev -- --port 3102"

echo.
echo 백엔드: http://localhost:8102
echo 프론트엔드: http://localhost:3102
echo API 문서: http://localhost:8102/docs
echo.
echo 두 서버가 시작되었습니다. 각 창을 닫으면 해당 서버가 종료됩니다.
```

### 3. `backend/.env.example` 업데이트 확인

```
DATABASE_URL=sqlite:///./interx.db
JWT_SECRET=your-secret-key-change-in-production
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### 4. `frontend/.env.local` 확인

```
NEXT_PUBLIC_API_URL=http://localhost:8102
```

### 5. 최종 통합 검증

백엔드 전체 엔드포인트 목록 확인:

```bash
cd C:/Users/main/Downloads/interX/backend
python -c "
from main import app
routes = [(r.methods, r.path) for r in app.routes if hasattr(r, 'methods') and r.methods]
for methods, path in sorted(routes, key=lambda x: x[1]):
    print(f'{list(methods)[0]:8} {path}')
"
```

예상 엔드포인트:
```
POST     /api/auth/login
GET      /api/auth/me
GET      /api/candidates/
POST     /api/candidates/
GET      /api/candidates/{id}
PATCH    /api/candidates/{id}
DELETE   /api/candidates/{id}
POST     /api/candidates/{id}/documents/resume
POST     /api/candidates/{id}/documents/portfolio
DELETE   /api/candidates/{id}/documents/{doc_id}
POST     /api/candidates/{id}/analysis
GET      /api/candidates/{id}/analysis
GET      /api/candidates/{id}/analysis/progress
DELETE   /api/candidates/{id}/analysis
GET      /api/candidates/{id}/report/pdf
POST     /api/candidates/{id}/interview/session
GET      /api/candidates/{id}/interview/session
DELETE   /api/candidates/{id}/interview/session
POST     /api/interview/qa
PATCH    /api/interview/qa/{qa_id}
```

### 6. 프론트엔드 빌드 최종 확인

```bash
cd C:/Users/main/Downloads/interX/frontend
npm run build
```

### 7. tasks/0-mvp/index.json 최종 상태 확인

모든 phase가 `"completed"` 또는 `"blocked"` 상태인지 확인.

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX

# 1. 백엔드 임포트 검증
python -c "
import sys
sys.path.insert(0, 'backend')
from main import app
print(f'등록된 라우트 수: {len([r for r in app.routes if hasattr(r, \"methods\")])}')
print('백엔드 임포트 OK')
"

# 2. 프론트엔드 빌드
cd frontend && npm run build
echo "프론트엔드 빌드 OK"

# 3. start.bat 존재 확인
cd .. && test -f start.bat && echo "start.bat OK" || echo "start.bat 없음"
```

모든 검증 통과 시 phase 13 status를 `"completed"`로 변경하라.
전체 task 완료 시 tasks/index.json의 mvp task status도 `"completed"`로 변경하라.

## AC 검증 방법

위 스크립트 실행 후 에러 없으면 phase 13 status를 `"completed"`로 변경하라.
모든 13개 phase(0~12)가 completed 또는 blocked 상태면 tasks/index.json의 mvp status도 `"completed"`로 변경.

## 주의사항

- `start.bat`은 새 cmd 창 2개를 열어서 각각 백엔드/프론트를 실행. `start "title" cmd /k "..."` 형식 사용.
- CORS 설정에서 `allow_credentials=True`일 때 `allow_origins=["*"]`는 동작하지 않는다. 반드시 명시적 origin 목록 사용.
- 프론트엔드 `npm run build`가 실패하면 TypeScript 에러를 수정 후 재빌드.
- `backend/.env`에 실제 `ANTHROPIC_API_KEY` 없이도 백엔드 시작은 가능. 분석 기능만 제한됨.
- 이 phase는 새 코드 작성보다 통합 확인이 주목적. 누락된 라우터 연결, 잘못된 임포트 등을 수정.
