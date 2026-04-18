# Phase 11: frontend-report

## 사전 준비

아래 문서를 읽어라:

- `docs/flow.md` — F3 (분석 진행 중 폴링), F4 (리포트 확인), F7 (PDF 출력)
- `docs/prd.md` — 12가지 핵심가치 정의

이전 phase 산출물:
- `frontend/lib/hooks.ts` — `useAnalysisProgress`
- `frontend/lib/types.ts` — Analysis, ValueScore, Contradiction, PreemptiveQuestion 타입
- `backend/api/analysis.py` — 분석 엔드포인트들

## 작업 내용

### 1. `frontend/app/candidates/[id]/report/page.tsx` — 리포트 페이지 (전체 구현)

```
레이아웃:
- Header
- 상단: 후보자 이름 + 직군 + 상태 Badge + StatusSelector
- 분석 시작 버튼 (미분석 / 재분석 시)
- 분석 중: ProgressBar 컴포넌트 (폴링)
- 분석 완료: 4개 섹션
  1. 문서 신뢰도 점수 + 이슈 목록
  2. 12가지 가치 레이더 차트 + 리스트
  3. 모순/불일치 목록
  4. 사전 압박 질문 목록
- PDF 다운로드 버튼
```

### 2. `frontend/components/report/ProgressBar.tsx` — 분석 진행 바

```typescript
// useAnalysisProgress 훅 사용 (2초 폴링)
// 단계 표시: OCR → 추출 → 가치매핑 → 모순탐지 → 질문생성 → 완료
// progress_percent로 바 너비 조절
// estimated_remaining_seconds로 "약 N초 남음" 표시
// 완료 시 자동으로 분석 결과 표시로 전환
```

```tsx
const STEP_LABELS = ['OCR', '추출', '가치매핑', '모순탐지', '질문생성', '완료']

export default function ProgressBar({ candidateId }: { candidateId: string }) {
  const progress = useAnalysisProgress(candidateId, true)

  if (!progress) return <Spinner />

  return (
    <div className="space-y-3">
      <div className="flex justify-between text-sm text-gray-600">
        <span>분석 중: {progress.current_step}</span>
        {progress.estimated_remaining_seconds && (
          <span>약 {progress.estimated_remaining_seconds}초 남음</span>
        )}
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${progress.progress_percent}%` }}
        />
      </div>
      <div className="flex justify-between">
        {STEP_LABELS.map((label) => (
          <span key={label} className={`text-xs ${progress.current_step === label ? 'text-primary font-medium' : 'text-gray-400'}`}>
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
```

### 3. `frontend/components/report/ValueRadarChart.tsx` — 가치 레이더 차트

Recharts의 `RadarChart` 사용:

```typescript
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts'
import { ValueScore, INTERX_VALUES } from '@/lib/types'

interface Props {
  valuesScores: Record<string, ValueScore>
  onSelectValue: (value: string) => void
  selectedValue: string | null
}

export default function ValueRadarChart({ valuesScores, onSelectValue, selectedValue }: Props) {
  const data = INTERX_VALUES.map(v => ({
    value: v,
    score: valuesScores[v]?.score ?? 0,
  }))

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis
            dataKey="value"
            tick={{ fontSize: 12, cursor: 'pointer' }}
            onClick={(e) => onSelectValue(e.value)}
          />
          <Radar dataKey="score" stroke="#ff8000" fill="#ff8000" fillOpacity={0.2} />
          <Tooltip formatter={(v) => [`${v}점`, '점수']} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

### 4. `frontend/components/report/ValueList.tsx` — 가치 점수 목록

```typescript
// 12가지 가치를 점수 순으로 표시
// 각 항목: 가치명 + 점수 바 + 클릭 시 EvidencePanel 열림
// 선택된 항목 강조 표시
// 80점 이상: primary 컬러, 40점 미만: 빨간색, 나머지: 회색
```

```tsx
export default function ValueList({ valuesScores, onSelect, selected }: Props) {
  return (
    <div className="space-y-2">
      {INTERX_VALUES.map((value) => {
        const score = valuesScores[value]?.score ?? 0
        const color = score >= 80 ? 'bg-primary' : score < 40 ? 'bg-red-400' : 'bg-gray-300'
        return (
          <button
            key={value}
            onClick={() => onSelect(value)}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${selected === value ? 'border-primary bg-orange-50' : 'border-gray-100 hover:border-gray-200'}`}
          >
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium">{value}</span>
              <span className="text-sm font-bold">{score}점</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full">
              <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
            </div>
          </button>
        )
      })}
    </div>
  )
}
```

### 5. `frontend/components/report/EvidencePanel.tsx` — AI 분석 근거 패널

```typescript
// 선택된 가치의 evidence + examples 표시
// 슬라이드인 패널 (우측 고정 패널 또는 모달)
// 닫기 버튼

interface Props {
  value: string
  scoreData: ValueScore | undefined
  onClose: () => void
}

export default function EvidencePanel({ value, scoreData, onClose }: Props) {
  if (!scoreData) return null
  return (
    <div className="fixed right-0 top-14 h-[calc(100vh-3.5rem)] w-80 bg-white border-l shadow-lg p-6 overflow-y-auto z-40">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">{value}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>
      </div>
      <div className="text-4xl font-bold text-primary mb-4">{scoreData.score}점</div>
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700 mb-1">분석 근거</p>
        <p className="text-sm text-gray-600">{scoreData.evidence}</p>
      </div>
      {scoreData.examples.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">이력서 인용</p>
          <ul className="space-y-2">
            {scoreData.examples.map((ex, i) => (
              <li key={i} className="text-sm text-gray-600 bg-gray-50 rounded p-2 italic">"{ex}"</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

### 6. `frontend/components/report/ContradictionList.tsx`

```typescript
const SEVERITY_COLORS = {
  high: 'border-red-400 bg-red-50',
  medium: 'border-yellow-400 bg-yellow-50',
  low: 'border-gray-300 bg-gray-50',
}
const SEVERITY_LABELS = { high: '높음', medium: '중간', low: '낮음' }

export default function ContradictionList({ contradictions }: { contradictions: Contradiction[] }) {
  if (contradictions.length === 0) return <p className="text-sm text-gray-500">탐지된 모순이 없습니다.</p>

  return (
    <div className="space-y-3">
      {contradictions.map((c, i) => (
        <div key={i} className={`border-l-4 rounded-r-lg p-4 ${SEVERITY_COLORS[c.severity]}`}>
          <div className="flex justify-between items-start mb-1">
            <span className="text-xs font-medium text-gray-500">{c.source_a} ↔ {c.source_b}</span>
            <span className="text-xs font-medium">심각도: {SEVERITY_LABELS[c.severity]}</span>
          </div>
          <p className="text-sm text-gray-700">{c.description}</p>
        </div>
      ))}
    </div>
  )
}
```

### 7. `frontend/components/report/PreemptiveQuestions.tsx`

```typescript
export default function PreemptiveQuestions({ questions }: { questions: PreemptiveQuestion[] }) {
  if (questions.length === 0) return <p className="text-sm text-gray-500">생성된 사전 질문이 없습니다.</p>

  return (
    <ol className="space-y-4">
      {questions.map((q, i) => (
        <li key={i} className="border rounded-xl p-4">
          <div className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-primary text-white rounded-full text-xs flex items-center justify-center font-medium">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-medium text-gray-800 mb-1">{q.question}</p>
              {q.target_value && (
                <span className="inline-block text-xs bg-orange-100 text-primary px-2 py-0.5 rounded-full mr-2">
                  {q.target_value}
                </span>
              )}
              <p className="text-xs text-gray-500 mt-1">{q.basis}</p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}
```

### 8. 리포트 페이지 전체 조립

```typescript
'use client'
import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import api from '@/lib/api'
import { Analysis, Candidate } from '@/lib/types'
import Header from '@/components/layout/Header'
import ProgressBar from '@/components/report/ProgressBar'
import ValueRadarChart from '@/components/report/ValueRadarChart'
import ValueList from '@/components/report/ValueList'
import EvidencePanel from '@/components/report/EvidencePanel'
import ContradictionList from '@/components/report/ContradictionList'
import PreemptiveQuestions from '@/components/report/PreemptiveQuestions'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [selectedValue, setSelectedValue] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    const [cr, ar] = await Promise.all([
      api.get(`/api/candidates/${id}`),
      api.get(`/api/candidates/${id}/analysis`).catch(() => ({ data: null }))
    ])
    setCandidate(cr.data)
    setAnalysis(ar.data)
    setLoading(false)
    if (ar.data?.current_step === '분석중') setAnalyzing(true)
  }

  useEffect(() => { loadData() }, [id])

  const startAnalysis = async () => {
    setAnalyzing(true)
    await api.post(`/api/candidates/${id}/analysis`)
  }

  const downloadPdf = async () => {
    const r = await api.get(`/api/candidates/${id}/report/pdf`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([r.data]))
    const a = document.createElement('a'); a.href = url
    a.download = `report_${id}.pdf`; a.click()
  }

  const isComplete = analysis?.current_step === '완료'
  const isAnalyzing = analyzing || analysis?.current_step === '분석중'

  // ... 렌더링 로직
}
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/frontend
npm run build
```

빌드 성공 + 다음 컴포넌트 파일 존재 확인:
- `components/report/ProgressBar.tsx`
- `components/report/ValueRadarChart.tsx`
- `components/report/ValueList.tsx`
- `components/report/EvidencePanel.tsx`
- `components/report/ContradictionList.tsx`
- `components/report/PreemptiveQuestions.tsx`

## AC 검증 방법

빌드 성공 시 phase 11 status를 `"completed"`로 변경하라.

## 주의사항

- `recharts`는 SSR에서 에러를 낼 수 있다. `RadarChart`를 포함하는 컴포넌트는 반드시 `'use client'` 지시어 추가.
- 분석 진행 중 → 완료 전환: `useAnalysisProgress`가 `current_step === '완료'`를 반환하면 `loadData()`를 다시 호출하여 결과 표시.
- `EvidencePanel`은 가치 선택 시 우측 패널로 표시. 모바일 대응보다 데스크탑 우선 레이아웃.
- PDF 다운로드는 `responseType: 'blob'` 필수.
- 분석 결과가 없을 때 (`analysis === null` 또는 `current_step !== '완료'`) 분석 시작 버튼 표시.
- 이미 분석 중일 때 (`isAnalyzing === true`) 시작 버튼 숨기고 ProgressBar 표시.
- 가치 레이더 차트와 리스트를 나란히 배치 (2열 레이아웃). 모바일에서는 세로 배치.
