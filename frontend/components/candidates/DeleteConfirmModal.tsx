'use client'
import { useState } from 'react'
import api from '@/lib/api'
import { Candidate } from '@/lib/types'
import Modal from '@/components/ui/Modal'
import Button from '@/components/ui/Button'

interface Props {
  open: boolean
  candidate: Candidate
  onClose: () => void
  onDeleted: () => void
}

export default function DeleteConfirmModal({ open, candidate, onClose, onDeleted }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const confirm = async () => {
    setLoading(true)
    setError('')
    try {
      await api.delete(`/api/candidates/${candidate.id}`)
      onDeleted()
    } catch {
      setError('삭제에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="후보자 삭제">
      <div className="space-y-3">
        <p className="text-sm text-gray-700">
          <span className="font-semibold">{candidate.name}</span>님을 정말 삭제하시겠습니까?
        </p>
        <p className="text-xs text-gray-500">후보자명과 모든 분석 데이터가 삭제됩니다.</p>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>취소</Button>
          <Button variant="danger" onClick={confirm} loading={loading}>삭제</Button>
        </div>
      </div>
    </Modal>
  )
}
