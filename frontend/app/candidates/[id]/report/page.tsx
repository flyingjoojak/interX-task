'use client'
import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
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
import StatusSelector from '@/components/candidates/StatusSelector'
import RawDataViewer from '@/components/report/RawDataViewer'
import MemoModal from '@/components/report/MemoModal'
import CostReport from '@/components/report/CostReport'

const PROCESSING_STEPS = ['OCR', '추출', '가치매핑', '모순탐지', '질문생성']

export default function ReportPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const id = params?.id
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [selectedValue, setSelectedValue] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [authed, setAuthed] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [rawOpen, setRawOpen] = useState(false)
  const [memoOpen, setMemoOpen] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (!token) { router.replace('/login'); return }
    setAuthed(true)
  }, [router])

  const loadData = useCallback(async () => {
    if (!id) return
    setError('')
    try {
      const [cr, ar] = await Promise.all([
        api.get(`/api/candidates/${id}`),
        api.get(`/api/candidates/${id}/analysis`).catch(() => ({ data: null })),
      ])
      setCandidate(cr.data)
      setAnalysis(ar.data)
      const step = ar.data?.current_step
      if (step && PROCESSING_STEPS.includes(step)) setAnalyzing(true)
      else setAnalyzing(false)
    } catch {
      setError('후보자 정보를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (authed) loadData()
  }, [authed, loadData])

  const startAnalysis = async () => {
    if (!id) return
    setError('')
    try {
      setAnalyzing(true)
      await api.post(`/api/candidates/${id}/analysis`)
      await loadData()
    } catch {
      setAnalyzing(false)
      setError('분석 시작에 실패했습니다.')
    }
  }

  const downloadPdf = async () => {
    if (!id) return
    setPdfLoading(true)
    try {
      const r = await api.get(`/api/candidates/${id}/report/pdf`, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${id}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('PDF 다운로드에 실패했습니다.')
    } finally {
      setPdfLoading(false)
    }
  }

  if (!authed) return null

  if (loading) {
    return (
      <div className="min-h-screen">
        <Header />
        <div className="flex justify-center py-20"><Spinner /></div>
      </div>
    )
  }

  if (!candidate) {
    return (
      <div className="min-h-screen">
        <Header />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center text-gray-500">
          후보자를 찾을 수 없습니다.
        </div>
      </div>
    )
  }

  const valuesScores = analysis?.values_scores ?? {}
  const isComplete = analysis?.current_step === '완료'
  const isAnalyzing = analyzing
  const hasError = analysis?.current_step === '오류'

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{candidate.name}</h1>
            <span className="text-gray-500">{candidate.position || '직군 미지정'}</span>
            <Badge status={candidate.status} />
            <StatusSelector candidate={candidate} onUpdated={loadData} />
          </div>
          <div className="flex gap-2">
            {!isAnalyzing && (
              <Button onClick={startAnalysis}>{isComplete || hasError ? '재분석' : '분석 시작'}</Button>
            )}
            <Button variant="secondary" onClick={() => setMemoOpen(true)}>
              📝 메모
            </Button>
            <Button variant="secondary" onClick={() => setRawOpen(true)}>
              원본 데이터 보기
            </Button>
            {isComplete && (
              <>
                <Button variant="secondary" onClick={downloadPdf} loading={pdfLoading}>
                  PDF 다운로드
                </Button>
                <Button onClick={() => router.push(`/candidates/${candidate.id}/interview`)}>
                  면접 시작
                </Button>
              </>
            )}
          </div>
        </div>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        {isAnalyzing && (
          <div className="bg-white border rounded-xl p-6 mb-8">
            <ProgressBar
              candidateId={candidate.id}
              onComplete={() => { setAnalyzing(false); loadData() }}
              onError={() => { setAnalyzing(false); loadData() }}
            />
          </div>
        )}

        {!isAnalyzing && hasError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 mb-6">
            <p className="text-sm font-semibold text-red-700 mb-1">이전 분석이 실패했습니다</p>
            <p className="text-sm text-red-600 whitespace-pre-wrap">
              {analysis?.error_message || '원인이 알려지지 않은 오류입니다. 서버 로그를 확인해주세요.'}
            </p>
            <p className="text-xs text-red-500 mt-2">상단의 &ldquo;재분석&rdquo; 버튼으로 다시 시도할 수 있습니다.</p>
          </div>
        )}

        {!isAnalyzing && !isComplete && !hasError && (
          <div className="bg-white border rounded-xl p-8 text-center text-gray-500">
            아직 분석이 완료되지 않았습니다. 상단의 &ldquo;분석 시작&rdquo; 버튼을 눌러주세요.
          </div>
        )}

        {isComplete && analysis && (
          <div className="space-y-8">
            <section className="bg-white border rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">문서 신뢰도</h2>
              <div className="flex items-center gap-4">
                <div className="text-4xl font-bold text-primary">
                  {analysis.doc_reliability_score != null ? Math.round(analysis.doc_reliability_score) : '-'}
                </div>
                <div className="text-sm text-gray-500">점 (100점 만점)</div>
              </div>
              {analysis.summary && (
                <p className="mt-4 text-sm text-gray-700 whitespace-pre-wrap">{analysis.summary}</p>
              )}
            </section>

            <section className="bg-white border rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">12가지 핵심가치</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ValueRadarChart
                  valuesScores={valuesScores}
                  onSelectValue={setSelectedValue}
                />
                <ValueList
                  valuesScores={valuesScores}
                  onSelect={setSelectedValue}
                  selected={selectedValue}
                />
              </div>
            </section>

            <section className="bg-white border rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">모순 · 불일치</h2>
              <ContradictionList contradictions={analysis.contradictions || []} />
            </section>

            <section className="bg-white border rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">사전 압박 질문</h2>
              <PreemptiveQuestions questions={analysis.preemptive_questions || []} />
            </section>

            <section className="bg-white border rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Claude API 사용량 · 비용</h2>
              <CostReport candidateId={candidate.id} />
            </section>
          </div>
        )}
      </main>

      <MemoModal
        open={memoOpen}
        candidateId={candidate.id}
        initialMemo={candidate.interviewer_memo || ''}
        onClose={() => setMemoOpen(false)}
        onSaved={(memo) => setCandidate({ ...candidate, interviewer_memo: memo })}
      />

      {selectedValue && (
        <EvidencePanel
          value={selectedValue}
          scoreData={valuesScores[selectedValue]}
          onClose={() => setSelectedValue(null)}
        />
      )}

      <RawDataViewer
        candidateId={candidate.id}
        open={rawOpen}
        onClose={() => setRawOpen(false)}
      />
    </div>
  )
}
