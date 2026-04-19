'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { Candidate } from '@/lib/types'
import Header from '@/components/layout/Header'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import CandidateCard from '@/components/candidates/CandidateCard'
import RegisterModal from '@/components/candidates/RegisterModal'

const FILTERS = ['전체', '분석완료', '서류합격', '면접합격', '최종합격'] as const
type Filter = typeof FILTERS[number]

export default function Home() {
  const router = useRouter()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Filter>('전체')
  const [registerOpen, setRegisterOpen] = useState(false)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    if (!token) {
      router.replace('/login')
      return
    }
    setAuthed(true)
  }, [router])

  const fetchList = async () => {
    setLoading(true)
    try {
      const r = await api.get('/api/candidates/')
      setCandidates(r.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (authed) fetchList()
  }, [authed])

  const visible = filter === '전체'
    ? candidates
    : candidates.filter(c => c.status === filter)

  if (!authed) return null

  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">후보자 관리</h1>
          <Button onClick={() => setRegisterOpen(true)}>＋ 새 후보자 등록</Button>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-sm border transition-colors ${
                filter === f
                  ? 'bg-primary text-white border-primary'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-primary'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : visible.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-3">👤</div>
            <p>등록된 후보자가 없습니다.</p>
            <p className="text-sm text-gray-400 mt-1">상단의 &ldquo;새 후보자 등록&rdquo; 버튼으로 시작하세요.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {visible.map(c => (
              <CandidateCard
                key={c.id}
                candidate={c}
                onDeleted={fetchList}
                onStatusChanged={fetchList}
              />
            ))}
          </div>
        )}
      </main>

      <RegisterModal
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onRegistered={() => {
          setRegisterOpen(false)
          fetchList()
        }}
      />
    </div>
  )
}
