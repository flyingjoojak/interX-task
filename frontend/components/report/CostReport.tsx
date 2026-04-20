'use client'
import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface Bucket {
  calls: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  cost_usd: number
}

interface CostResponse {
  candidate_id: string
  total: Bucket
  by_phase: Record<string, Bucket>
  by_step: Record<string, Bucket>
  calls: Array<{
    phase: string
    step: string | null
    model: string
    input_tokens: number
    output_tokens: number
    cost_usd: number
    created_at: string | null
  }>
}

interface Props {
  candidateId: string
}

const fmtTokens = (n: number) => n.toLocaleString()
const fmtUsd = (n: number) => `$${n.toFixed(4)}`

export default function CostReport({ candidateId }: Props) {
  const [data, setData] = useState<CostResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.get(`/api/candidates/${candidateId}/cost`)
      .then(r => { if (!cancelled) setData(r.data) })
      .catch(() => { if (!cancelled) setError('비용 정보를 불러오지 못했습니다.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [candidateId])

  if (loading) return <div className="text-sm text-gray-500">불러오는 중…</div>
  if (error) return <div className="text-sm text-red-500">{error}</div>
  if (!data) return null

  const phases = Object.entries(data.by_phase).sort((a, b) => b[1].cost_usd - a[1].cost_usd)
  const steps = Object.entries(data.by_step).sort((a, b) => b[1].cost_usd - a[1].cost_usd)

  if (data.total.calls === 0) {
    return (
      <p className="text-sm text-gray-500">
        아직 기록된 Claude API 호출이 없습니다. 분석을 실행하면 토큰 사용량이 자동 적재됩니다.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500">총 호출 수</div>
          <div className="text-xl font-bold">{data.total.calls}</div>
        </div>
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500">입력 토큰</div>
          <div className="text-xl font-bold">{fmtTokens(data.total.input_tokens)}</div>
        </div>
        <div className="border rounded-lg p-3">
          <div className="text-xs text-gray-500">출력 토큰</div>
          <div className="text-xl font-bold">{fmtTokens(data.total.output_tokens)}</div>
        </div>
        <div className="border rounded-lg p-3 bg-primary/5">
          <div className="text-xs text-gray-500">총 비용 (USD)</div>
          <div className="text-xl font-bold text-primary">{fmtUsd(data.total.cost_usd)}</div>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">단계별 (phase)</h3>
        <table className="w-full text-sm border">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">phase</th>
              <th className="text-right p-2">호출</th>
              <th className="text-right p-2">in</th>
              <th className="text-right p-2">out</th>
              <th className="text-right p-2">USD</th>
            </tr>
          </thead>
          <tbody>
            {phases.map(([k, v]) => (
              <tr key={k} className="border-t">
                <td className="p-2">{k}</td>
                <td className="p-2 text-right">{v.calls}</td>
                <td className="p-2 text-right">{fmtTokens(v.input_tokens)}</td>
                <td className="p-2 text-right">{fmtTokens(v.output_tokens)}</td>
                <td className="p-2 text-right">{fmtUsd(v.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details>
        <summary className="text-sm font-semibold text-gray-700 cursor-pointer">세부 step별 (펼치기)</summary>
        <table className="w-full text-sm border mt-2">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">step</th>
              <th className="text-right p-2">호출</th>
              <th className="text-right p-2">in</th>
              <th className="text-right p-2">out</th>
              <th className="text-right p-2">USD</th>
            </tr>
          </thead>
          <tbody>
            {steps.map(([k, v]) => (
              <tr key={k} className="border-t">
                <td className="p-2">{k}</td>
                <td className="p-2 text-right">{v.calls}</td>
                <td className="p-2 text-right">{fmtTokens(v.input_tokens)}</td>
                <td className="p-2 text-right">{fmtTokens(v.output_tokens)}</td>
                <td className="p-2 text-right">{fmtUsd(v.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      <p className="text-xs text-gray-500">
        비용은 Anthropic 공식 단가(Sonnet 4.6: $3/M input, $15/M output) 기준 추정치입니다.
      </p>
    </div>
  )
}
