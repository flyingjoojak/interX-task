'use client'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts'
import { ValueScore, INTERX_VALUES } from '@/lib/types'

interface Props {
  valuesScores: Record<string, ValueScore>
  onSelectValue: (value: string) => void
}

export default function ValueRadarChart({ valuesScores, onSelectValue }: Props) {
  const data = INTERX_VALUES.map(v => ({
    value: v,
    score: valuesScores[v]?.score ?? 0,
  }))

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis
            dataKey="value"
            tick={({ x, y, payload, textAnchor }) => (
              <text
                x={x}
                y={y}
                textAnchor={textAnchor}
                fontSize={12}
                fill="#374151"
                style={{ cursor: 'pointer' }}
                onClick={() => onSelectValue(payload.value as string)}
              >
                {payload.value}
              </text>
            )}
          />
          <Radar dataKey="score" stroke="#ff8000" fill="#ff8000" fillOpacity={0.2} />
          <Tooltip formatter={(v) => [`${v}점`, '점수']} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
