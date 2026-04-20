'use client'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Modal from '@/components/ui/Modal'
import Button from '@/components/ui/Button'

interface Props {
  open: boolean
  candidateId: string
  initialMemo: string
  onClose: () => void
  onSaved: (memo: string) => void
}

export default function MemoModal({ open, candidateId, initialMemo, onClose, onSaved }: Props) {
  const [memo, setMemo] = useState(initialMemo || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setMemo(initialMemo || '')
      setError('')
    }
  }, [open, initialMemo])

  const save = async () => {
    setLoading(true)
    setError('')
    try {
      await api.patch(`/api/candidates/${candidateId}`, { interviewer_memo: memo })
      onSaved(memo)
      onClose()
    } catch {
      setError('메모 저장에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="면접관 메모">
      <div className="space-y-3">
        <p className="text-xs text-gray-500">
          면접관 전용 메모입니다. 후보자에게 노출되지 않으며, 리포트/PDF 공유 시에도 포함되지 않습니다.
        </p>
        <textarea
          value={memo}
          onChange={e => setMemo(e.target.value)}
          rows={8}
          placeholder="후보자 인상, 확인할 사항, 면접 포인트 등을 자유롭게 기록하세요."
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-y"
        />
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="ghost" onClick={onClose} disabled={loading}>취소</Button>
          <Button onClick={save} loading={loading}>저장</Button>
        </div>
      </div>
    </Modal>
  )
}
