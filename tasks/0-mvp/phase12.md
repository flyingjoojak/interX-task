# Phase 12: frontend-interview

## 사전 준비

아래 문서를 읽어라:

- `docs/flow.md` — F5 (면접 세션 진입), F6 (실시간 면접 흐름, 꼬리질문 사이클)
- `docs/adr.md` — ADR-011 (Q&A 선형 타임라인)

이전 phase 산출물:
- `frontend/lib/types.ts` — InterviewSession, QAPair, FollowupQuestion 타입
- `backend/api/interview.py` — 면접 세션/Q&A 엔드포인트

## 작업 내용

### 1. `frontend/app/candidates/[id]/interview/page.tsx` — 면접 페이지 (전체 구현)

```
레이아웃 (2단):
┌─────────────────────────────────────────────────────┐
│ Header                                               │
├──────────────┬──────────────────────────────────────┤
│ LeftSidebar  │ QATimeline                           │
│ (w-80)       │                                      │
│ - 후보자 정보 │ - Q&A 카드 목록 (시간순)             │
│ - 사전 질문  │ - AnswerInput (현재 질문)            │
│   목록       │ - FollowupPanel (꼬리질문)           │
│ - 상태 변경  │                                      │
└──────────────┴──────────────────────────────────────┘
```

### 2. `frontend/components/interview/LeftSidebar.tsx` — 좌측 사이드바

```typescript
interface Props {
  candidate: Candidate
  preemptiveQuestions: PreemptiveQuestion[]
  onAddQuestion: (text: string, source: 'pregenerated' | 'custom') => void
}

// 섹션 1: 후보자 정보
//   - 이름, 직군, 상태 Badge
//   - StatusSelector

// 섹션 2: 사전 압박 질문 목록
//   - preemptive_questions 목록
//   - 각 항목 클릭 → onAddQuestion('pregenerated') 호출
//   - 클릭된 항목 시각적 표시 (이미 추가됨)

// 섹션 3: 직접 질문 입력
//   - textarea
//   - "질문 추가" 버튼 → onAddQuestion('custom') 호출

// 세션 초기화 버튼
//   - "새로 시작" 클릭 시 확인 모달 → DELETE /api/candidates/{id}/interview/session
```

### 3. `frontend/components/interview/QATimeline.tsx` — Q&A 타임라인

```typescript
// QAPair 배열을 order_index 순으로 렌더링
// 각 카드: QACard 컴포넌트
// 마지막에 AnswerInput 표시 (answer_text가 null인 마지막 QAPair 또는 신규 입력)
// 자동 스크롤: 새 Q&A 추가 시 하단으로 스크롤
```

```typescript
export default function QATimeline({ qaPairs, sessionId, onUpdate }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [qaPairs])

  const unanswered = qaPairs.find(q => q.answer_text === null)

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {qaPairs.filter(q => q.answer_text !== null).map(qa => (
        <QACard key={qa.id} qa={qa} onSelectFollowup={...} />
      ))}
      {unanswered && (
        <AnswerInput qa={unanswered} onSubmit={onUpdate} />
      )}
      <div ref={bottomRef} />
    </div>
  )
}
```

### 4. `frontend/components/interview/QACard.tsx` — Q&A 카드

```typescript
// 질문 표시 (상단, 회색 배경)
// question_source 뱃지: "사전질문" | "커스텀" | "꼬리질문"
// 답변 표시 (하단, 흰색)
// 꼬리질문 패널 토글 버튼 (followup_questions가 있을 때)
// parent_qa_id 있으면 "↩ 꼬리질문" 표시

interface Props {
  qa: QAPair
  onSelectFollowup: (question: string) => void
}

const SOURCE_LABELS = {
  pregenerated: '사전질문',
  custom: '커스텀',
  followup: '꼬리질문',
}

export default function QACard({ qa, onSelectFollowup }: Props) {
  const [showFollowups, setShowFollowups] = useState(false)

  return (
    <div className="border rounded-xl overflow-hidden">
      {/* 질문 영역 */}
      <div className="bg-gray-50 p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
            {SOURCE_LABELS[qa.question_source]}
          </span>
          {qa.parent_qa_id && <span className="text-xs text-gray-400">↩ 꼬리질문</span>}
        </div>
        <p className="text-sm font-medium text-gray-800">{qa.question_text}</p>
      </div>

      {/* 답변 영역 */}
      {qa.answer_text && (
        <div className="p-4">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{qa.answer_text}</p>
        </div>
      )}

      {/* 꼬리질문 섹션 */}
      {qa.followup_questions && qa.followup_questions.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowFollowups(!showFollowups)}
            className="w-full text-left px-4 py-2 text-sm text-primary font-medium flex items-center gap-1"
          >
            <span>꼬리질문 {qa.followup_questions.length}개</span>
            <span>{showFollowups ? '▲' : '▼'}</span>
          </button>
          {showFollowups && (
            <FollowupPanel questions={qa.followup_questions} onSelect={onSelectFollowup} />
          )}
        </div>
      )}
    </div>
  )
}
```

### 5. `frontend/components/interview/AnswerInput.tsx` — 답변 입력

```typescript
interface Props {
  qa: QAPair
  onSubmit: (qaId: string, answerText: string) => Promise<void>
}

export default function AnswerInput({ qa, onSubmit }: Props) {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!answer.trim()) return
    setLoading(true)
    await onSubmit(qa.id, answer)
    setAnswer('')
    setLoading(false)
  }

  return (
    <div className="border-2 border-primary rounded-xl p-4">
      <div className="bg-orange-50 p-3 rounded-lg mb-3">
        <p className="text-sm font-medium text-gray-800">{qa.question_text}</p>
      </div>
      <textarea
        value={answer}
        onChange={e => setAnswer(e.target.value)}
        placeholder="후보자의 답변을 입력하세요..."
        className="w-full h-24 text-sm border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-gray-400">답변 제출 시 꼬리질문이 AI로 생성됩니다</span>
        <Button onClick={submit} loading={loading} disabled={!answer.trim()}>
          답변 제출 및 꼬리질문 생성
        </Button>
      </div>
    </div>
  )
}
```

### 6. `frontend/components/interview/FollowupPanel.tsx` — 꼬리질문 패널

```typescript
interface Props {
  questions: FollowupQuestion[]
  onSelect: (question: string) => void
}

export default function FollowupPanel({ questions, onSelect }: Props) {
  return (
    <div className="p-4 space-y-2 bg-orange-50">
      <p className="text-xs text-gray-500 font-medium">AI 추천 꼬리질문 (클릭하여 추가)</p>
      {questions.map((q, i) => (
        <button
          key={i}
          onClick={() => onSelect(q.question)}
          className="w-full text-left p-3 bg-white rounded-lg border border-orange-200 hover:border-primary text-sm transition-colors"
        >
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-primary text-white rounded-full text-xs flex items-center justify-center">
              {q.priority}
            </span>
            <div>
              <p className="text-gray-800">{q.question}</p>
              <p className="text-xs text-gray-400 mt-1">{q.reasoning}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
```

### 7. 면접 페이지 전체 로직

```typescript
'use client'
export default function InterviewPage() {
  const { id } = useParams<{ id: string }>()
  const [session, setSession] = useState<InterviewSession | null>(null)
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    const [cr, sr, ar] = await Promise.all([
      api.get(`/api/candidates/${id}`),
      api.post(`/api/candidates/${id}/interview/session`),
      api.get(`/api/candidates/${id}/analysis`).catch(() => ({ data: null }))
    ])
    setCandidate(cr.data)
    setSession(sr.data)
    setAnalysis(ar.data)
    setLoading(false)
  }

  useEffect(() => { loadData() }, [id])

  const addQuestion = async (text: string, source: 'pregenerated' | 'custom') => {
    const r = await api.post('/api/interview/qa', {
      session_id: session!.id,
      question_source: source,
      question_text: text,
    })
    setSession(prev => prev ? {
      ...prev,
      qa_pairs: [...prev.qa_pairs, r.data]
    } : prev)
  }

  const submitAnswer = async (qaId: string, answerText: string) => {
    const r = await api.patch(`/api/interview/qa/${qaId}`, { answer_text: answerText })
    setSession(prev => prev ? {
      ...prev,
      qa_pairs: prev.qa_pairs.map(q => q.id === qaId ? r.data : q)
    } : prev)
  }

  const addFollowup = async (questionText: string) => {
    await addQuestion(questionText, 'custom')  // followup은 custom으로 추가
  }

  const resetSession = async () => {
    await api.delete(`/api/candidates/${id}/interview/session`)
    loadData()
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner /></div>

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar
          candidate={candidate!}
          preemptiveQuestions={analysis?.preemptive_questions ?? []}
          onAddQuestion={addQuestion}
          onReset={resetSession}
        />
        <div className="flex-1 flex flex-col overflow-hidden">
          {session && (
            <QATimeline
              qaPairs={session.qa_pairs}
              sessionId={session.id}
              onSubmitAnswer={submitAnswer}
              onSelectFollowup={addFollowup}
            />
          )}
        </div>
      </div>
    </div>
  )
}
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/frontend
npm run build
```

빌드 성공 + 다음 컴포넌트 파일 존재 확인:
- `components/interview/LeftSidebar.tsx`
- `components/interview/QATimeline.tsx`
- `components/interview/QACard.tsx`
- `components/interview/AnswerInput.tsx`
- `components/interview/FollowupPanel.tsx`

## AC 검증 방법

빌드 성공 시 phase 12 status를 `"completed"`로 변경하라.

## 주의사항

- 면접 페이지 진입 시 `POST /api/candidates/{id}/interview/session` 호출 (기존 세션 있으면 반환, 없으면 생성).
- `submitAnswer` 호출 후 응답에 `followup_questions` 포함됨. 상태 업데이트 시 해당 QAPair 전체 교체.
- 꼬리질문 패널에서 질문 선택 시 `POST /api/interview/qa`로 새 QAPair 생성. `question_source: 'followup'` 사용.
- 세션 초기화 후 `loadData()` 재호출하여 빈 세션 표시.
- `QATimeline`은 `overflow-y-auto`로 스크롤 가능. 새 항목 추가 시 맨 아래로 자동 스크롤.
- `AnswerInput`의 답변 제출 중 (`loading=true`) 버튼 비활성화 및 "꼬리질문 생성 중..." 텍스트 표시.
- 모든 인터랙티브 컴포넌트에 `'use client'` 지시어 필수.
