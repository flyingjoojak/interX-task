'use client'
import { ValueScore } from '@/lib/types'

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
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
      </div>
      <div className="text-4xl font-bold text-primary mb-4">{scoreData.score}점</div>
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700 mb-1">분석 근거</p>
        <p className="text-sm text-gray-600 whitespace-pre-wrap">{scoreData.evidence}</p>
      </div>
      {scoreData.examples && scoreData.examples.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">이력서 인용</p>
          <ul className="space-y-2">
            {scoreData.examples.map((ex, i) => (
              <li key={i} className="text-sm text-gray-600 bg-gray-50 rounded p-2 italic">&ldquo;{ex}&rdquo;</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
