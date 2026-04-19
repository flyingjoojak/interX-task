'use client'
import { useEffect, useRef, useState } from 'react'
import api from '@/lib/api'
import { Candidate, CANDIDATE_STATUSES } from '@/lib/types'

interface Props {
  candidate: Candidate
  onUpdated: () => void
}

export default function StatusSelector({ candidate, onUpdated }: Props) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const change = async (status: string) => {
    if (status === candidate.status) { setOpen(false); return }
    setBusy(true)
    try {
      await api.patch(`/api/candidates/${candidate.id}/status`, { status })
      onUpdated()
    } finally {
      setBusy(false)
      setOpen(false)
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        disabled={busy}
        className="text-xs text-gray-500 hover:text-primary px-2 py-0.5 border rounded"
      >
        상태 변경 ▾
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 bg-white border rounded-lg shadow-md z-20 min-w-[120px]">
          {CANDIDATE_STATUSES.map(s => (
            <button
              key={s}
              onClick={() => change(s)}
              className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 ${s === candidate.status ? 'text-primary font-semibold' : 'text-gray-700'}`}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
