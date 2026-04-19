'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import api from '@/lib/api'
import { Analysis, Candidate, InterviewSession, QAPair } from '@/lib/types'
import Header from '@/components/layout/Header'
import Spinner from '@/components/ui/Spinner'
import LeftSidebar from '@/components/interview/LeftSidebar'
import QATimeline from '@/components/interview/QATimeline'

export default function InterviewPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const id = params?.id
  const [session, setSession] = useState<InterviewSession | null>(null)
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (!token) { router.replace('/login'); return }
    setAuthed(true)
  }, [router])

  const loadData = useCallback(async () => {
    if (!id) return
    setError('')
    try {
      const [cr, sr, ar] = await Promise.all([
        api.get(`/api/candidates/${id}`),
        api.post(`/api/candidates/${id}/interview/session`),
        api.get(`/api/candidates/${id}/analysis`).catch(() => ({ data: null })),
      ])
      setCandidate(cr.data)
      setSession(sr.data)
      setAnalysis(ar.data)
    } catch {
      setError('면접 세션을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (authed) loadData()
  }, [authed, loadData])

  const addQuestion = useCallback(async (
    text: string,
    source: 'pregenerated' | 'custom' | 'followup',
    parentQaId?: string,
  ) => {
    if (!session) return
    const r = await api.post('/api/interview/qa', {
      session_id: session.id,
      question_source: source,
      question_text: text,
      parent_qa_id: parentQaId ?? null,
    })
    const newQa = r.data as QAPair
    setSession(prev => prev ? { ...prev, qa_pairs: [...prev.qa_pairs, newQa] } : prev)
  }, [session])

  const toggleOrAdd = useCallback(async (
    text: string,
    source: 'pregenerated' | 'custom' | 'followup',
    parentQaId?: string,
  ) => {
    if (!session) return
    const sameUnanswered = session.qa_pairs.find(
      q => q.question_text === text && !q.answer_text,
    )
    if (sameUnanswered) {
      try { await api.delete(`/api/interview/qa/${sameUnanswered.id}`) } catch {}
      setSession(prev => prev ? {
        ...prev,
        qa_pairs: prev.qa_pairs.filter(q => q.id !== sameUnanswered.id),
      } : prev)
      return
    }
    const alreadyAdded = session.qa_pairs.find(q => q.question_text === text)
    if (alreadyAdded) return
    const otherUnanswered = session.qa_pairs.find(q => !q.answer_text)
    if (otherUnanswered) {
      try { await api.delete(`/api/interview/qa/${otherUnanswered.id}`) } catch {}
      setSession(prev => prev ? {
        ...prev,
        qa_pairs: prev.qa_pairs.filter(q => q.id !== otherUnanswered.id),
      } : prev)
    }
    await addQuestion(text, source, parentQaId)
  }, [session, addQuestion])

  const handleAddQuestion = useCallback(async (
    text: string,
    source: 'pregenerated' | 'custom',
  ) => {
    await toggleOrAdd(text, source)
  }, [toggleOrAdd])

  const submitAnswer = useCallback(async (qaId: string, answerText: string) => {
    const r = await api.patch(`/api/interview/qa/${qaId}`, { answer_text: answerText })
    const updated = r.data as QAPair
    setSession(prev => prev ? {
      ...prev,
      qa_pairs: prev.qa_pairs.map(q => q.id === qaId ? updated : q),
    } : prev)
  }, [])

  const selectFollowup = useCallback(async (questionText: string) => {
    if (!session) return
    const parent = [...session.qa_pairs]
      .reverse()
      .find(q => q.followup_questions?.some(f => f.question === questionText))
    await toggleOrAdd(questionText, 'followup', parent?.id)
  }, [session, toggleOrAdd])

  const resetSession = useCallback(async () => {
    if (!id) return
    await api.delete(`/api/candidates/${id}/interview/session`)
    await loadData()
  }, [id, loadData])

  const usedPreemptive = useMemo(() => {
    const set = new Set<string>()
    if (!session) return set
    for (const q of session.qa_pairs) {
      if (q.question_source === 'pregenerated' && q.question_text) {
        set.add(q.question_text)
      }
    }
    return set
  }, [session])

  const usedFollowups = useMemo(() => {
    const set = new Set<string>()
    if (!session) return set
    for (const q of session.qa_pairs) {
      if (q.question_source === 'followup' && q.question_text) {
        set.add(q.question_text)
      }
    }
    return set
  }, [session])

  const hasPendingFollowup = useMemo(() => {
    if (!session) return false
    return session.qa_pairs.some(q => q.answer_text != null && q.followup_questions === null)
  }, [session])

  useEffect(() => {
    if (!hasPendingFollowup || !id) return
    const interval = setInterval(async () => {
      try {
        const r = await api.get(`/api/candidates/${id}/interview/session`)
        setSession(r.data)
      } catch {
        // ignore transient errors
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [hasPendingFollowup, id])

  if (!authed) return null

  if (loading) {
    return (
      <div className="min-h-screen">
        <Header />
        <div className="flex justify-center py-20"><Spinner /></div>
      </div>
    )
  }

  if (!candidate || !session) {
    return (
      <div className="min-h-screen">
        <Header />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center text-gray-500">
          {error || '면접 세션 정보를 불러올 수 없습니다.'}
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar
          candidate={candidate}
          preemptiveQuestions={analysis?.preemptive_questions ?? []}
          usedPreemptive={usedPreemptive}
          onAddQuestion={handleAddQuestion}
          onReset={resetSession}
          onStatusChanged={loadData}
        />
        <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
          {error && <p className="px-6 pt-4 text-red-500 text-sm">{error}</p>}
          <QATimeline
            qaPairs={session.qa_pairs}
            onSubmitAnswer={submitAnswer}
            onSelectFollowup={selectFollowup}
            usedFollowups={usedFollowups}
          />
        </div>
      </div>
    </div>
  )
}
