'use client'
import { Contradiction } from '@/lib/types'

const SEVERITY_COLORS: Record<Contradiction['severity'], string> = {
  high: 'border-red-400 bg-red-50',
  medium: 'border-yellow-400 bg-yellow-50',
  low: 'border-gray-300 bg-gray-50',
}
const SEVERITY_LABELS: Record<Contradiction['severity'], string> = {
  high: '높음',
  medium: '중간',
  low: '낮음',
}

export default function ContradictionList({ contradictions }: { contradictions: Contradiction[] }) {
  if (!contradictions || contradictions.length === 0) {
    return <p className="text-sm text-gray-500">탐지된 모순이 없습니다.</p>
  }

  return (
    <div className="space-y-3">
      {contradictions.map((c, i) => (
        <div key={i} className={`border-l-4 rounded-r-lg p-4 ${SEVERITY_COLORS[c.severity] || SEVERITY_COLORS.low}`}>
          <div className="flex justify-between items-start mb-1">
            <span className="text-xs font-medium text-gray-500">{c.source_a} ↔ {c.source_b}</span>
            <span className="text-xs font-medium">심각도: {SEVERITY_LABELS[c.severity] || '-'}</span>
          </div>
          <p className="text-sm text-gray-700">{c.description}</p>
        </div>
      ))}
    </div>
  )
}
