'use client'
import { FollowupQuestion } from '@/lib/types'

interface Props {
  questions: FollowupQuestion[]
  onSelect: (question: string) => void
  usedSet?: Set<string>
}

export default function FollowupPanel({ questions, onSelect, usedSet }: Props) {
  return (
    <div className="p-4 space-y-2 bg-primary-50">
      <p className="text-xs text-gray-500 font-medium">AI 추천 꼬리질문 (클릭하여 추가)</p>
      {questions.map((q, i) => {
        const used = usedSet?.has(q.question) ?? false
        return (
          <button
            key={i}
            onClick={() => onSelect(q.question)}
            className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
              used
                ? 'bg-primary-100 border-primary text-primary-700'
                : 'bg-white border-primary-200 hover:border-primary'
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 bg-primary text-white rounded-full text-xs flex items-center justify-center">
                {q.priority}
              </span>
              <div className="flex-1">
                <p className="text-gray-800">{q.question}</p>
                {q.reasoning && <p className="text-xs text-gray-400 mt-1">{q.reasoning}</p>}
                {used && <p className="mt-1 text-[10px] text-primary-700 font-medium">추가됨</p>}
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
