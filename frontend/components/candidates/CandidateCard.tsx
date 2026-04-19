'use client'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Candidate } from '@/lib/types'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import DeleteConfirmModal from './DeleteConfirmModal'
import StatusSelector from './StatusSelector'

interface Props {
  candidate: Candidate
  onDeleted: () => void
  onStatusChanged: () => void
}

export default function CandidateCard({ candidate, onDeleted, onStatusChanged }: Props) {
  const router = useRouter()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const avg = candidate.avg_value_score
  const avgDisplay = typeof avg === 'number' ? Math.round(avg) : '-'

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm hover:shadow transition-shadow flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-lg font-semibold text-gray-900">{candidate.name}</div>
          <div className="text-sm text-gray-500">{candidate.position || '직군 미지정'}</div>
        </div>
        <button
          onClick={() => setDeleteOpen(true)}
          className="text-gray-400 hover:text-red-500 text-lg leading-none"
          aria-label="삭제"
        >
          🗑
        </button>
      </div>

      <div className="flex items-center gap-2">
        <StatusSelector candidate={candidate} onUpdated={onStatusChanged} />
        <Badge status={candidate.status} />
      </div>

      <div className="text-sm text-gray-600">
        가치 평균 점수: <span className="font-semibold text-gray-900">{avgDisplay}</span>
      </div>

      <div className="flex gap-2 mt-2">
        <Button
          size="sm"
          className="flex-1"
          onClick={() => router.push(`/candidates/${candidate.id}/report`)}
        >
          리포트 보기
        </Button>
      </div>

      <DeleteConfirmModal
        open={deleteOpen}
        candidate={candidate}
        onClose={() => setDeleteOpen(false)}
        onDeleted={() => {
          setDeleteOpen(false)
          onDeleted()
        }}
      />
    </div>
  )
}
