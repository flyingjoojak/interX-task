'use client'
import { useEffect, useRef } from 'react'
import { QAPair } from '@/lib/types'
import QACard from './QACard'
import AnswerInput from './AnswerInput'

interface Props {
  qaPairs: QAPair[]
  onSubmitAnswer: (qaId: string, answerText: string) => Promise<void>
  onSelectFollowup: (question: string) => void
  usedFollowups: Set<string>
}

export default function QATimeline({ qaPairs, onSubmitAnswer, onSelectFollowup, usedFollowups }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [qaPairs.length])

  const sorted = [...qaPairs].sort((a, b) => a.order_index - b.order_index)
  const unanswered = sorted.find(q => !q.answer_text)
  const answered = sorted.filter(q => q.answer_text)

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {answered.length === 0 && !unanswered && (
        <div className="text-center text-gray-500 py-20 text-sm">
          좌측에서 질문을 선택하거나 직접 입력하여 면접을 시작하세요.
        </div>
      )}

      {answered.map(qa => (
        <QACard
          key={qa.id}
          qa={qa}
          onSelectFollowup={onSelectFollowup}
          usedFollowups={usedFollowups}
        />
      ))}

      {unanswered && (
        <AnswerInput qa={unanswered} onSubmit={onSubmitAnswer} />
      )}

      <div ref={bottomRef} />
    </div>
  )
}
