# Phase 9: frontend-foundation

## 사전 준비

아래 문서를 읽어라:

- `docs/code-architecture.md` — 프론트엔드 폴더 구조, API 엔드포인트 목록
- `docs/flow.md` — F1 (로그인), 전체 화면 구성
- `docs/adr.md` — ADR-008 (Next.js App Router)

이전 phase 산출물:
- `backend/api/auth.py` — `/api/auth/login`, `/api/auth/me`
- `backend/schemas/` — 모든 응답 스키마

## 작업 내용

### 1. Next.js 프로젝트 초기화 (Phase 0에서 이미 생성된 경우 스킵)

`frontend/` 디렉토리가 없거나 `package.json`이 없는 경우에만 실행:

```bash
cd C:/Users/main/Downloads/interX
npx create-next-app@14 frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

### 2. `frontend/tailwind.config.ts` — 브랜드 컬러 설정

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#ff8000',
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#ff8000',
          600: '#ea6c00',
          700: '#c2550a',
          800: '#9a3c0f',
          900: '#7c2d12',
        },
      },
    },
  },
  plugins: [],
}
export default config
```

### 3. `frontend/lib/api.ts` — Axios 클라이언트 (JWT 인터셉터 포함)

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8102',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

### 4. `frontend/lib/types.ts` — TypeScript 타입 정의

백엔드 스키마와 1:1 대응:

```typescript
export interface Candidate {
  id: string
  name: string
  position: string
  status: string
  created_at: string
  documents: Document[]
}

export interface Document {
  id: string
  candidate_id: string
  doc_type: 'resume' | 'portfolio'
  file_type: string
  original_filename: string
  ocr_text?: string
  ocr_method?: string
  ocr_quality_score?: number
  created_at: string
}

export interface Analysis {
  candidate_id: string
  structured_data?: {
    career: CareerItem[]
    education: EducationItem[]
    skills: string[]
    achievements: Achievement[]
    certifications: Certification[]
    projects: Project[]
  }
  values_scores?: Record<string, ValueScore>
  doc_reliability_score?: number
  contradictions?: Contradiction[]
  preemptive_questions?: PreemptiveQuestion[]
  summary?: string
  current_step?: string
}

export interface ValueScore {
  score: number
  evidence: string
  examples: string[]
}

export interface Contradiction {
  source_a: string
  source_b: string
  description: string
  severity: 'high' | 'medium' | 'low'
}

export interface PreemptiveQuestion {
  question: string
  target_value: string | null
  basis: string
}

export interface AnalysisProgress {
  candidate_id: string
  current_step: string | null
  step_started_at: string | null
  estimated_remaining_seconds: number | null
  progress_percent: number
}

export interface InterviewSession {
  id: string
  candidate_id: string
  last_accessed_at: string | null
  created_at: string
  qa_pairs: QAPair[]
}

export interface QAPair {
  id: string
  session_id: string
  question_source: 'pregenerated' | 'custom' | 'followup'
  question_text: string
  answer_text: string | null
  followup_questions: FollowupQuestion[] | null
  parent_qa_id: string | null
  order_index: number
  created_at: string
  answered_at: string | null
}

export interface FollowupQuestion {
  question: string
  reasoning: string
  priority: number
}

export interface CareerItem {
  company: string
  role: string
  start: string
  end: string
  description: string
}

export interface EducationItem {
  school: string
  major: string
  degree: string
  start: string
  end: string
}

export interface Achievement {
  title: string
  description: string
  quantified_result: string | null
}

export interface Certification {
  name: string
  issuer: string
  date: string
}

export interface Project {
  name: string
  role: string
  period: string
  description: string
  tech_stack: string[]
}

export const CANDIDATE_STATUSES = [
  '미분석', '분석중', '분석완료',
  '서류합격', '서류탈락',
  '면접합격', '면접탈락',
  '최종합격', '최종탈락',
] as const

export type CandidateStatus = typeof CANDIDATE_STATUSES[number]

export const INTERX_VALUES = [
  '목표의식', '시간관리', '끈기', '문제해결', '비판적사고', '지속적개선',
  '정성스러움', '자기동기부여', '긍정적태도', '솔직한피드백', '네트워크활용', '호기심',
] as const
```

### 5. `frontend/lib/hooks.ts` — 공통 훅

```typescript
import { useState, useEffect, useCallback } from 'react'
import api from './api'
import { Candidate, Analysis, AnalysisProgress, InterviewSession } from './types'

export function useAuth() {
  const [user, setUser] = useState<{ email: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    api.get('/api/auth/me')
      .then(r => setUser(r.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const r = await api.post('/api/auth/login', { email, password })
    localStorage.setItem('token', r.data.access_token)
    setUser({ email })
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return { user, loading, login, logout }
}

export function useCandidates() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    setLoading(true)
    const r = await api.get('/api/candidates/')
    setCandidates(r.data)
    setLoading(false)
  }, [])

  useEffect(() => { fetch() }, [fetch])
  return { candidates, loading, refetch: fetch }
}

export function useAnalysisProgress(candidateId: string, enabled: boolean) {
  const [progress, setProgress] = useState<AnalysisProgress | null>(null)

  useEffect(() => {
    if (!enabled) return
    const interval = setInterval(async () => {
      try {
        const r = await api.get(`/api/candidates/${candidateId}/analysis/progress`)
        setProgress(r.data)
        if (r.data.current_step === '완료' || r.data.current_step === '오류') {
          clearInterval(interval)
        }
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [candidateId, enabled])

  return progress
}
```

### 6. `frontend/components/ui/` — 공통 UI 컴포넌트

**`Button.tsx`**:
```typescript
import { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

export default function Button({
  variant = 'primary', size = 'md', loading, children, className = '', ...props
}: ButtonProps) {
  const base = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors disabled:opacity-50'
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-600',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    ghost: 'text-gray-600 hover:bg-gray-100',
  }
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : null}
      {children}
    </button>
  )
}
```

**`Badge.tsx`**:
```typescript
interface BadgeProps {
  status: string
  className?: string
}

const STATUS_COLORS: Record<string, string> = {
  '미분석': 'bg-gray-100 text-gray-600',
  '분석중': 'bg-blue-100 text-blue-700',
  '분석완료': 'bg-green-100 text-green-700',
  '서류합격': 'bg-emerald-100 text-emerald-700',
  '서류탈락': 'bg-red-100 text-red-600',
  '면접합격': 'bg-indigo-100 text-indigo-700',
  '면접탈락': 'bg-red-100 text-red-600',
  '최종합격': 'bg-primary-100 text-primary-700',
  '최종탈락': 'bg-red-100 text-red-600',
}

export default function Badge({ status, className = '' }: BadgeProps) {
  const color = STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color} ${className}`}>
      {status}
    </span>
  )
}
```

**`Modal.tsx`**:
```typescript
import { ReactNode, useEffect } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export default function Modal({ open, onClose, title, children }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        {children}
      </div>
    </div>
  )
}
```

**`Spinner.tsx`**:
```typescript
export default function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' }
  return (
    <div className={`animate-spin rounded-full border-2 border-gray-200 border-t-primary ${sizes[size]}`} />
  )
}
```

### 7. `frontend/components/layout/Header.tsx`

```typescript
'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function Header() {
  const router = useRouter()
  const logout = () => {
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <header className="h-14 border-b bg-white px-6 flex items-center justify-between">
      <Link href="/" className="font-bold text-xl text-primary">InterX</Link>
      <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">로그아웃</button>
    </header>
  )
}
```

### 8. `frontend/app/layout.tsx`

```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'InterX — 에이전트 기반 채용 솔루션',
  description: '12가지 핵심가치 기반 후보자 분석 및 면접 지원',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={`${inter.className} bg-gray-50`}>{children}</body>
    </html>
  )
}
```

### 9. `frontend/app/login/page.tsx`

```typescript
'use client'
import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import Button from '@/components/ui/Button'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('admin@interx.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const r = await api.post('/api/auth/login', { email, password })
      localStorage.setItem('token', r.data.access_token)
      router.push('/')
    } catch {
      setError('이메일 또는 비밀번호를 확인해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-primary mb-2">InterX</h1>
        <p className="text-gray-500 text-sm mb-6">에이전트 기반 채용 솔루션</p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">이메일</label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">비밀번호</label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <Button type="submit" className="w-full" loading={loading}>로그인</Button>
        </form>
      </div>
    </div>
  )
}
```

### 10. `frontend/.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:8102
```

### 11. `frontend/next.config.ts` 업데이트

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8102/api/:path*',
      },
    ]
  },
}

export default nextConfig
```

### 12. 패키지 설치

```bash
cd C:/Users/main/Downloads/interX/frontend
npm install axios recharts
npm install --save-dev @types/node
```

## Acceptance Criteria

```bash
cd C:/Users/main/Downloads/interX/frontend

# TypeScript 타입 체크 + 빌드
npm run build
```

빌드 성공 (exit 0) + TypeScript 에러 없으면 통과.

## AC 검증 방법

빌드 성공 시 phase 9 status를 `"completed"`로 변경하라.

## 주의사항

- `tailwind.config.ts`의 primary 컬러를 반드시 `#ff8000`으로 설정. CSS 변수가 아닌 Tailwind 테마 확장 방식 사용.
- `api.ts`의 baseURL은 환경변수에서 읽되, 기본값은 `http://localhost:8102`.
- `useAnalysisProgress` 훅은 `enabled=true`일 때만 폴링 시작. 컴포넌트 언마운트 시 interval 정리 필수.
- Next.js 14 App Router 사용. `'use client'` 지시어는 클라이언트 컴포넌트에만 추가.
- `globals.css`에 `@tailwind base; @tailwind components; @tailwind utilities;` 포함 확인.
- 빌드 실패 시 TypeScript 에러 메시지를 확인하고 수정 후 재빌드.
- next.config.ts가 이미 존재하면 rewrites 설정만 추가 (덮어쓰기 주의).
