'use client'
import { useState } from 'react'
import { Candidate, PreemptiveQuestion } from '@/lib/types'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import StatusSelector from '@/components/candidates/StatusSelector'

interface Props {
  candidate: Candidate
  preemptiveQuestions: PreemptiveQuestion[]
  usedPreemptive: Set<string>
  onAddQuestion: (text: string, source: 'pregenerated' | 'custom') => Promise<void>
  onReset: () => void
  onStatusChanged: () => void
}

export default function LeftSidebar({
  candidate,
  preemptiveQuestions,
  usedPreemptive,
  onAddQuestion,
  onReset,
  onStatusChanged,
}: Props) {
  const [custom, setCustom] = useState('')
  const [adding, setAdding] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
  const [resetting, setResetting] = useState(false)

  const addCustom = async () => {
    if (!custom.trim() || adding) return
    setAdding(true)
    try {
      await onAddQuestion(custom, 'custom')
      setCustom('')
    } finally {
      setAdding(false)
    }
  }

  const addPregen = async (text: string) => {
    await onAddQuestion(text, 'pregenerated')
  }

  const confirmReset = async () => {
    setResetting(true)
    try {
      await onReset()
      setResetOpen(false)
    } finally {
      setResetting(false)
    }
  }

  return (
    <aside className="w-80 border-r bg-white flex flex-col overflow-hidden">
      <div className="p-4 border-b space-y-2">
        <div className="text-lg font-semibold text-gray-900">{candidate.name}</div>
        <div className="text-sm text-gray-500">{candidate.position || '직군 미지정'}</div>
        <div className="flex items-center gap-2">
          <Badge status={candidate.status} />
          <StatusSelector candidate={candidate} onUpdated={onStatusChanged} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="text-xs font-semibold text-gray-500 mb-2">사전 압박 질문</p>
        {preemptiveQuestions.length === 0 ? (
          <p className="text-xs text-gray-400">생성된 사전 질문이 없습니다.</p>
        ) : (
          <ul className="space-y-2">
            {preemptiveQuestions.map((q, i) => {
              const used = usedPreemptive.has(q.question)
              return (
                <li key={i}>
                  <button
                    onClick={() => addPregen(q.question)}
                    className={`w-full text-left p-2 rounded-lg border text-xs transition-colors ${
                      used
                        ? 'bg-primary-50 border-primary text-primary-700'
                        : 'border-gray-200 hover:border-primary hover:bg-primary-50 text-gray-700'
                    }`}
                  >
                    <p className="font-medium">{q.question}</p>
                    {q.target_value && (
                      <span className="inline-block text-xs bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded-full mt-1">
                        {q.target_value}
                      </span>
                    )}
                    {used && <p className="mt-1 text-[10px]">추가됨</p>}
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="p-4 border-t bg-white space-y-2">
        <p className="text-xs font-semibold text-gray-500">직접 질문 추가</p>
        <textarea
          value={custom}
          onChange={e => setCustom(e.target.value)}
          placeholder="질문을 입력하세요..."
          className="w-full h-16 text-sm border rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <Button
          size="sm"
          className="w-full"
          onClick={addCustom}
          loading={adding}
          disabled={!custom.trim()}
        >
          질문 추가
        </Button>
        <Button variant="ghost" size="sm" className="w-full" onClick={() => setResetOpen(true)}>
          세션 새로 시작
        </Button>
      </div>

      <Modal open={resetOpen} onClose={() => !resetting && setResetOpen(false)} title="면접 세션 초기화">
        <div className="space-y-3">
          <p className="text-sm text-gray-700">모든 Q&amp;A가 삭제됩니다. 계속하시겠습니까?</p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setResetOpen(false)} disabled={resetting}>취소</Button>
            <Button variant="danger" onClick={confirmReset} loading={resetting}>초기화</Button>
          </div>
        </div>
      </Modal>
    </aside>
  )
}
