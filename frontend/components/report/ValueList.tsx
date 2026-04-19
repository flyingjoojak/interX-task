'use client'
import { ValueScore, INTERX_VALUES } from '@/lib/types'

interface Props {
  valuesScores: Record<string, ValueScore>
  onSelect: (value: string) => void
  selected: string | null
}

export default function ValueList({ valuesScores, onSelect, selected }: Props) {
  return (
    <div className="space-y-2">
      {INTERX_VALUES.map((value) => {
        const score = valuesScores[value]?.score ?? 0
        const color = score >= 80 ? 'bg-primary' : score < 40 ? 'bg-red-400' : 'bg-gray-300'
        return (
          <button
            key={value}
            onClick={() => onSelect(value)}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${
              selected === value ? 'border-primary bg-primary-50' : 'border-gray-100 hover:border-gray-200'
            }`}
          >
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium">{value}</span>
              <span className="text-sm font-bold">{score}점</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full">
              <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
            </div>
          </button>
        )
      })}
    </div>
  )
}
