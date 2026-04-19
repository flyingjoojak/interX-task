'use client'
import { useState } from 'react'
import { QAPair } from '@/lib/types'
import Button from '@/components/ui/Button'

interface Props {
  qa: QAPair
  onSubmit: (qaId: string, answerText: string) => Promise<void>
}

export default function AnswerInput({ qa, onSubmit }: Props) {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!answer.trim() || loading) return
    setLoading(true)
    try {
      await onSubmit(qa.id, answer)
      setAnswer('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-2 border-primary rounded-xl p-4 bg-white">
      <div className="bg-primary-50 p-3 rounded-lg mb-3">
        <p className="text-sm font-medium text-gray-800 whitespace-pre-wrap">{qa.question_text}</p>
      </div>
      <textarea
        value={answer}
        onChange={e => setAnswer(e.target.value)}
        placeholder="후보자의 답변을 입력하세요..."
        className="w-full h-24 text-sm border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        disabled={loading}
      />
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-gray-400">
          {loading ? '꼬리질문 생성 중...' : '답변 제출 시 꼬리질문이 AI로 생성됩니다'}
        </span>
        <Button onClick={submit} loading={loading} disabled={!answer.trim()}>
          답변 제출 및 꼬리질문 생성
        </Button>
      </div>
    </div>
  )
}
