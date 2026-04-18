# Phase 10: frontend-home

## 사전 준비

아래 문서를 읽어라:

- `docs/flow.md` — F1 (후보자 목록/홈), F2 (후보자 등록)
- `docs/code-architecture.md` — POST/GET/DELETE /api/candidates/, 파일 업로드 엔드포인트

이전 phase 산출물:
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/lib/hooks.ts`
- `frontend/components/ui/` — Button, Badge, Modal, Spinner
- `frontend/components/layout/Header.tsx`

## 작업 내용

### 1. `frontend/app/page.tsx` — 홈 (후보자 목록)

```
레이아웃:
- Header
- 상단 바: "후보자 관리" 제목 + "새 후보자 등록" 버튼
- 상태 필터 탭: 전체 | 분석완료 | 서류합격 | 면접합격 | 최종합격
- 후보자 카드 그리드 (2~3열)
- 빈 상태: "등록된 후보자가 없습니다" 메시지
```

**후보자 카드 (`CandidateCard.tsx`)**:
```
- 이름 + 직군
- 상태 Badge
- 분석완료 시: 가치 평균 점수 표시 (값 없으면 "-")
- 버튼: "리포트 보기" (→ /candidates/{id}/report), "면접 시작" (→ /candidates/{id}/interview)
- 우측 상단: 삭제 버튼 (휴지통 아이콘, 클릭 시 확인 모달)
```

**상태 필터**: URL 쿼리 파라미터 (`?status=분석완료`) 또는 클라이언트 state로 구현.

### 2. `frontend/components/candidates/RegisterModal.tsx` — 후보자 등록 모달

단계 1 - 기본 정보:
```
- 이름 입력 (필수)
- 직군 입력 (필수)
- "다음" 버튼
```

단계 2 - 파일 첨부:
```
Zone 1 — 이력서 (필수):
  - 드래그&드롭 영역
  - 지원 형식: PDF, JPG, PNG, PPT, PPTX
  - 최대 20MB
  - 선택된 파일명 표시

Zone 2 — 포트폴리오 (선택):
  - 드래그&드롭 영역
  - 지원 형식: PDF, JPG, PNG
  - 최의 안내: "PPT/PPTX는 지원되지 않습니다. PDF 또는 이미지 파일을 사용해주세요."
  - 최대 20MB
  - 선택된 파일명 표시

- "등록하기" 버튼 (이력서 선택 시 활성화)
- "이전" 버튼
```

**등록 플로우**:
```typescript
// 1. POST /api/candidates/ → candidate.id 획득
// 2. FormData로 이력서 업로드: POST /api/candidates/{id}/documents/resume
// 3. 포트폴리오 있으면: POST /api/candidates/{id}/documents/portfolio
// 4. 등록 완료 후 목록 새로고침
```

### 3. `frontend/components/candidates/StatusSelector.tsx` — 상태 변경 드롭다운

```typescript
// 클릭 시 모든 상태 목록 드롭다운 표시
// PATCH /api/candidates/{id} 호출로 status 변경
// 변경 후 부모 컴포넌트에 onUpdate 콜백 호출
```

### 4. `frontend/components/candidates/DeleteConfirmModal.tsx`

```
- "정말 삭제하시겠습니까?" 메시지
- "후보자명과 모든 분석 데이터가 삭제됩니다." 안내
- "취소" / "삭제" 버튼
- DELETE /api/candidates/{id} 호출
```

### 5. `frontend/app/candidates/[id]/report/page.tsx` — 리포트 페이지 (placeholder)

이 Phase에서는 빈 페이지만 생성 (Phase 11에서 구현):

```typescript
export default function ReportPage() {
  return <div className="p-8">리포트 페이지 (준비 중)</div>
}
```

### 6. `frontend/app/candidates/[id]/interview/page.tsx` — 면접 페이지 (placeholder)

```typescript
export default function InterviewPage() {
  return <div className="p-8">면접 페이지 (준비 중)</div>
}
```

## 구현 상세

### 파일 업로드 드래그&드롭

```typescript
const handleDrop = (e: React.DragEvent, zone: 'resume' | 'portfolio') => {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) setFile(zone, file)
}

const uploadFile = async (candidateId: string, file: File, docType: 'resume' | 'portfolio') => {
  const formData = new FormData()
  formData.append('file', file)
  await api.post(`/api/candidates/${candidateId}/documents/${docType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
```

### 가치 평균 점수 계산

```typescript
const calcAvgScore = (valuesScores?: Record<string, { score: number }>) => {
  if (!valuesScores) return null
  const scores = Object.values(valuesScores).map(v => v.score)
  if (scores.length === 0) return null
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
}
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/frontend
npm run build
```

빌드 성공 + 다음 페이지 존재 확인:
- `app/page.tsx` (홈)
- `app/candidates/[id]/report/page.tsx`
- `app/candidates/[id]/interview/page.tsx`
- `components/candidates/RegisterModal.tsx`

## AC 검증 방법

빌드 성공 시 phase 10 status를 `"completed"`로 변경하라.

## 주의사항

- 파일 크기 검증은 프론트에서도 수행: 20MB 초과 시 "파일 크기는 20MB 이하여야 합니다" 알림.
- `'use client'` 컴포넌트에서 `useRouter`, `useState` 등 훅 사용. 서버 컴포넌트와 클라이언트 컴포넌트 경계 명확히.
- 등록 모달 로딩 중 버튼 비활성화 + Spinner 표시.
- 삭제 후 목록에서 즉시 제거 (낙관적 업데이트 또는 목록 재조회).
- 홈 페이지는 `'use client'`로 선언하고 `useCandidates` 훅 사용.
- 후보자 없을 때 빈 상태 UI 표시 (아이콘 + 안내 문구).
