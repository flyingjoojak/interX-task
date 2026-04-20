'use client'
import { ChangeEvent, DragEvent, useState } from 'react'
import api from '@/lib/api'
import Modal from '@/components/ui/Modal'
import Button from '@/components/ui/Button'

interface Props {
  open: boolean
  onClose: () => void
  onRegistered: () => void
}

const MAX_SIZE = 20 * 1024 * 1024
const ALLOWED_EXTS = ['pdf', 'jpg', 'jpeg', 'png']

function extOf(file: File): string {
  const idx = file.name.lastIndexOf('.')
  return idx >= 0 ? file.name.slice(idx + 1).toLowerCase() : ''
}

export default function RegisterModal({ open, onClose, onRegistered }: Props) {
  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [position, setPosition] = useState('')
  const [resume, setResume] = useState<File | null>(null)
  const [portfolio, setPortfolio] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragZone, setDragZone] = useState<'resume' | 'portfolio' | null>(null)

  const reset = () => {
    setStep(1)
    setName('')
    setPosition('')
    setResume(null)
    setPortfolio(null)
    setError('')
    setLoading(false)
    setDragZone(null)
  }

  const close = () => {
    if (loading) return
    reset()
    onClose()
  }

  const pickFile = (file: File, zone: 'resume' | 'portfolio') => {
    setError('')
    if (file.size > MAX_SIZE) {
      setError('파일 크기는 20MB 이하여야 합니다.')
      return
    }
    const ext = extOf(file)
    if (!ALLOWED_EXTS.includes(ext)) {
      setError('지원되지 않는 형식입니다. PDF/JPG/PNG만 업로드 가능합니다.')
      return
    }
    if (zone === 'resume') setResume(file)
    else setPortfolio(file)
  }

  const onDrop = (e: DragEvent<HTMLLabelElement>, zone: 'resume' | 'portfolio') => {
    e.preventDefault()
    setDragZone(null)
    const file = e.dataTransfer.files?.[0]
    if (file) pickFile(file, zone)
  }

  const onChangeInput = (e: ChangeEvent<HTMLInputElement>, zone: 'resume' | 'portfolio') => {
    const file = e.target.files?.[0]
    if (file) pickFile(file, zone)
    e.target.value = ''
  }

  const uploadDoc = async (candidateId: string, file: File, docType: 'resume' | 'portfolio') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_type', docType)
    await api.post(`/api/candidates/${candidateId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  const submit = async () => {
    if (!resume) {
      setError('이력서 파일을 선택해주세요.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const r = await api.post('/api/candidates/', { name, position: position || null })
      const candidateId = r.data.id as string
      await uploadDoc(candidateId, resume, 'resume')
      if (portfolio) await uploadDoc(candidateId, portfolio, 'portfolio')
      reset()
      onRegistered()
    } catch {
      setError('등록에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const dropzoneCls = (zone: 'resume' | 'portfolio') =>
    `flex items-center justify-center min-h-[72px] border-2 border-dashed rounded-lg px-4 py-6 text-center text-sm cursor-pointer transition-colors ${
      dragZone === zone ? 'border-primary bg-primary-50' : 'border-gray-300 hover:border-primary'
    }`

  return (
    <Modal open={open} onClose={close} title={step === 1 ? '후보자 등록 — 기본 정보' : '후보자 등록 — 파일 첨부'}>
      {step === 1 ? (
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700">이름 *</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">직군 *</label>
            <input
              value={position}
              onChange={e => setPosition(e.target.value)}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={close}>취소</Button>
            <Button onClick={() => setStep(2)} disabled={!name.trim() || !position.trim()}>다음</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-3">이력서 *</p>
            <label
              className={dropzoneCls('resume')}
              onDragOver={e => { e.preventDefault(); setDragZone('resume') }}
              onDragLeave={() => setDragZone(null)}
              onDrop={e => onDrop(e, 'resume')}
            >
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={e => onChangeInput(e, 'resume')}
                className="hidden"
              />
              {resume ? (
                <span className="text-gray-800">{resume.name}</span>
              ) : (
                <span className="text-gray-500">
                  클릭 또는 드래그&드롭 · PDF, JPG, PNG · 최대 20MB
                </span>
              )}
            </label>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700 mb-3">포트폴리오 (선택)</p>
            <label
              className={dropzoneCls('portfolio')}
              onDragOver={e => { e.preventDefault(); setDragZone('portfolio') }}
              onDragLeave={() => setDragZone(null)}
              onDrop={e => onDrop(e, 'portfolio')}
            >
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={e => onChangeInput(e, 'portfolio')}
                className="hidden"
              />
              {portfolio ? (
                <span className="text-gray-800">{portfolio.name}</span>
              ) : (
                <span className="text-gray-500">
                  클릭 또는 드래그&드롭 · PDF, JPG, PNG · 최대 20MB
                </span>
              )}
            </label>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setStep(1)} disabled={loading}>이전</Button>
            <Button onClick={submit} loading={loading} disabled={!resume}>등록하기</Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
