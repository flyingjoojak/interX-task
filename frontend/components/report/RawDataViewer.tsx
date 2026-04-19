'use client'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Spinner from '@/components/ui/Spinner'

interface RawDocument {
  id: string
  doc_type: string
  file_type: string
  original_name: string
  ocr_method: string | null
  ocr_quality_score: number | null
  ocr_text: string
  ocr_text_length: number
}

interface RawDebugPayload {
  candidate_id: string
  documents: RawDocument[]
  structured_data: unknown
}

interface Props {
  candidateId: string
  open: boolean
  onClose: () => void
}

type Tab = 'ocr' | 'json'

export default function RawDataViewer({ candidateId, open, onClose }: Props) {
  const [data, setData] = useState<RawDebugPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('ocr')
  const [activeDocId, setActiveDocId] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .get(`/api/candidates/${candidateId}/debug/raw`)
      .then((r) => {
        if (cancelled) return
        setData(r.data)
        const first = r.data?.documents?.[0]?.id ?? null
        setActiveDocId(first)
      })
      .catch(() => {
        if (!cancelled) setError('원문 데이터를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, candidateId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const activeDoc = data?.documents.find((d) => d.id === activeDocId) ?? null
  const jsonText = data?.structured_data
    ? JSON.stringify(data.structured_data, null, 2)
    : '(추출 데이터 없음 — 분석이 완료되지 않았거나 추출 단계 전입니다.)'

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).catch(() => {})
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-6xl h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">파싱 원본 데이터 뷰어</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              OCR 원문 텍스트와 Claude가 추출한 structured_data를 비교해 파싱 오류 vs 할루시네이션을 진단합니다.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="닫기"
          >
            &times;
          </button>
        </div>

        <div className="flex gap-1 px-6 pt-3 border-b">
          <button
            onClick={() => setTab('ocr')}
            className={`px-4 py-2 text-sm rounded-t-lg ${
              tab === 'ocr'
                ? 'bg-primary text-white font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            OCR 원문
          </button>
          <button
            onClick={() => setTab('json')}
            className={`px-4 py-2 text-sm rounded-t-lg ${
              tab === 'json'
                ? 'bg-primary text-white font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            추출 JSON (structured_data)
          </button>
        </div>

        <div className="flex-1 overflow-hidden">
          {loading && (
            <div className="flex justify-center items-center h-full">
              <Spinner />
            </div>
          )}
          {error && !loading && (
            <div className="flex justify-center items-center h-full text-red-500 text-sm">
              {error}
            </div>
          )}

          {!loading && !error && data && tab === 'ocr' && (
            <div className="h-full flex">
              <aside className="w-56 border-r overflow-y-auto bg-gray-50">
                {data.documents.length === 0 ? (
                  <p className="p-4 text-xs text-gray-500">업로드된 문서가 없습니다.</p>
                ) : (
                  <ul>
                    {data.documents.map((d) => (
                      <li key={d.id}>
                        <button
                          onClick={() => setActiveDocId(d.id)}
                          className={`w-full text-left px-4 py-3 text-sm border-b ${
                            activeDocId === d.id
                              ? 'bg-white text-primary font-medium'
                              : 'hover:bg-white text-gray-700'
                          }`}
                        >
                          <div className="font-medium">
                            {d.doc_type === 'resume' ? '이력서' : '포트폴리오'}
                          </div>
                          <div className="text-xs text-gray-500 truncate mt-0.5">
                            {d.original_name}
                          </div>
                          <div className="text-[10px] text-gray-400 mt-1">
                            {d.ocr_text_length.toLocaleString()}자 · {d.ocr_method || 'OCR 미실행'}
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </aside>
              <div className="flex-1 flex flex-col">
                {activeDoc ? (
                  <>
                    <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50 text-xs">
                      <div className="text-gray-600">
                        {activeDoc.doc_type === 'resume' ? '이력서' : '포트폴리오'} ·{' '}
                        {activeDoc.file_type.toUpperCase()} ·{' '}
                        품질점수 {activeDoc.ocr_quality_score ?? '-'}
                      </div>
                      <button
                        onClick={() => copyToClipboard(activeDoc.ocr_text)}
                        className="px-2 py-1 text-xs text-gray-600 hover:text-primary hover:bg-white rounded"
                      >
                        복사
                      </button>
                    </div>
                    <pre className="flex-1 overflow-auto p-4 text-xs whitespace-pre-wrap font-mono text-gray-800 bg-white">
                      {activeDoc.ocr_text || '(OCR 텍스트가 아직 저장되지 않았습니다.)'}
                    </pre>
                  </>
                ) : (
                  <div className="flex justify-center items-center h-full text-sm text-gray-500">
                    문서를 선택하세요.
                  </div>
                )}
              </div>
            </div>
          )}

          {!loading && !error && data && tab === 'json' && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50 text-xs">
                <div className="text-gray-600">Analysis.structured_data</div>
                <button
                  onClick={() => copyToClipboard(jsonText)}
                  className="px-2 py-1 text-xs text-gray-600 hover:text-primary hover:bg-white rounded"
                >
                  복사
                </button>
              </div>
              <pre className="flex-1 overflow-auto p-4 text-xs font-mono text-gray-800 bg-white">
                {jsonText}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
