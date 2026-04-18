# Phase 2: auth-api

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — Auth API 엔드포인트, 보안 레이어
- `docs/adr.md` — ADR-008 (JWT 인증 결정 이유)

이전 phase 산출물:
- `backend/config.py` — Settings (JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS)
- `backend/database.py` — get_db, engine
- `backend/models/user.py` — User 모델
- `backend/main.py` — FastAPI 앱
- `backend/seed.py` — admin@interx.com / interx1234 계정 존재

## 작업 내용

### 1. `backend/.env`에 JWT_SECRET 추가

`backend/.env` 파일을 열어 아래 라인을 추가하라 (ANTHROPIC_API_KEY는 건드리지 말 것):

```
JWT_SECRET=interx-jwt-secret-2026-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
```

### 2. `backend/utils/logger.py` — PII 마스킹 로거

Python 표준 logging을 래핑. 로그 메시지에서 이름/연락처 패턴을 `***`으로 치환 후 출력.

마스킹 대상:
- 한국 휴대폰: `010-\d{4}-\d{4}` → `010-***-****`
- 이메일: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+` → `***@***.***`
- 주민등록번호 패턴: `\d{6}-[1-4]\d{6}` → `******-*******`

`get_logger(name: str) -> logging.Logger` 함수 export.

### 3. `backend/schemas/auth.py`

```python
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: str
    email: str
```

### 4. `backend/api/auth.py` — JWT 인증 엔드포인트

**JWT 유틸리티 함수** (이 파일 또는 `utils/jwt_utils.py`):
- `create_access_token(data: dict) -> str` — HS256, exp 설정
- `verify_token(token: str) -> TokenData` — 검증 실패 시 HTTPException 401
- `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`

**엔드포인트**:
- `POST /api/auth/login` — email+password 검증, access_token 반환
  - 계정 없거나 비밀번호 틀리면 HTTP 401 `{"detail": "이메일 또는 비밀번호가 올바르지 않습니다"}`
- `GET /api/auth/me` — 현재 로그인 사용자 정보 반환 (인증 필요)

### 5. `backend/main.py` 업데이트

auth 라우터를 등록하라:

```python
from api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
```

모든 `/api/*` 경로는 `get_current_user` dependency로 보호한다. auth 라우터 자체(`/api/auth/login`)는 예외.

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/backend

python -c "
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. 로그인 성공 테스트
r = client.post('/api/auth/login', json={'email': 'admin@interx.com', 'password': 'interx1234'})
assert r.status_code == 200, f'Login failed: {r.status_code} {r.text}'
token = r.json()['access_token']
assert token, 'No token returned'

# 2. 토큰으로 /me 조회
r2 = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
assert r2.status_code == 200, f'Me failed: {r2.status_code} {r2.text}'
assert r2.json()['email'] == 'admin@interx.com'

# 3. 잘못된 비밀번호
r3 = client.post('/api/auth/login', json={'email': 'admin@interx.com', 'password': 'wrong'})
assert r3.status_code == 401

# 4. 토큰 없이 보호된 엔드포인트 접근
r4 = client.get('/api/auth/me')
assert r4.status_code == 401

print('Auth API 모든 테스트 통과')
"
```

## AC 검증 방법

위 Python 스크립트를 `backend/` 디렉토리에서 실행하라. 모두 통과하면 phase 2 status를 `"completed"`로 변경하라. 실패 시 3회까지 수정 후 재시도. 그래도 실패하면 `"error"` + error_message 기록.

## 주의사항

- `passlib.context.CryptContext(schemes=["bcrypt"])` 사용. bcrypt 직접 import 금지.
- JWT 토큰에 `sub` 필드는 user.id (UUID string)으로 설정.
- `get_current_user`는 FastAPI Dependency로 구현. 이후 모든 보호된 엔드포인트에서 재사용.
- TestClient는 ASGI 앱을 인메모리로 실행하므로 uvicorn을 별도 실행하지 않아도 된다.
- `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")` 사용.
