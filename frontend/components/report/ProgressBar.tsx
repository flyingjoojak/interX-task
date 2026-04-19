'use client'
import { useEffect, useRef } from 'react'
import { useAnalysisProgress } from '@/lib/hooks'
import Spinner from '@/components/ui/Spinner'

const STEP_LABELS = ['OCR', '추출', '가치매핑', '모순탐지', '질문생성', '완료']

interface Props {
  candidateId: string
  onComplete?: () => void
  onError?: (message: string | null | undefined) => void
}

export default function ProgressBar({ candidateId, onComplete, onError }: Props) {
  const progress = useAnalysisProgress(candidateId, true)
  const firedRef = useRef(false)

  useEffect(() => {
    if (firedRef.current) return
    if (progress?.current_step === '완료') {
      firedRef.current = true
      onComplete?.()
    } else if (progress?.current_step === '오류') {
      firedRef.current = true
      onError?.(progress.error_message)
    }
  }, [progress?.current_step, progress?.error_message, onComplete, onError])

  if (!progress) return <div className="flex justify-center py-8"><Spinner /></div>

  if (progress.current_step === '오류') {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm font-semibold text-red-700 mb-1">분석 중 오류가 발생했습니다</p>
        <p className="text-sm text-red-600 whitespace-pre-wrap">
          {progress.error_message || '원인이 알려지지 않은 오류입니다. 서버 로그를 확인해주세요.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-between text-sm text-gray-600">
        <span>분석 중: {progress.current_step ?? '대기'}</span>
        {progress.estimated_remaining_seconds != null && (
          <span>약 {progress.estimated_remaining_seconds}초 남음</span>
        )}
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${progress.progress_percent}%` }}
        />
      </div>
      <div className="flex justify-between">
        {STEP_LABELS.map((label) => (
          <span
            key={label}
            className={`text-xs ${progress.current_step === label ? 'text-primary font-medium' : 'text-gray-400'}`}
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
