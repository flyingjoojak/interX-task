'use client'
import { PreemptiveQuestion } from '@/lib/types'

export default function PreemptiveQuestions({ questions }: { questions: PreemptiveQuestion[] }) {
  if (!questions || questions.length === 0) {
    return <p className="text-sm text-gray-500">생성된 사전 질문이 없습니다.</p>
  }

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
                <span className="inline-block text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full mr-2">
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
