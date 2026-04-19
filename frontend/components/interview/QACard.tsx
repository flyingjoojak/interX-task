'use client'
import { useState } from 'react'
import { QAPair } from '@/lib/types'
import FollowupPanel from './FollowupPanel'
import Spinner from '@/components/ui/Spinner'

const SOURCE_LABELS: Record<QAPair['question_source'], string> = {
  pregenerated: '사전질문',
  custom: '커스텀',
  followup: '꼬리질문',
}

interface Props {
  qa: QAPair
  onSelectFollowup: (question: string) => void
  usedFollowups: Set<string>
}

export default function QACard({ qa, onSelectFollowup, usedFollowups }: Props) {
  const [showFollowups, setShowFollowups] = useState(false)
  const followups = qa.followup_questions || []
  const isGenerating = qa.answer_text != null && qa.followup_questions === null

  return (
    <div className="border rounded-xl overflow-hidden bg-white">
      <div className="bg-gray-50 p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
            {SOURCE_LABELS[qa.question_source] || qa.question_source}
          </span>
          {qa.parent_qa_id && <span className="text-xs text-gray-400">↩ 꼬리질문</span>}
        </div>
        <p className="text-sm font-medium text-gray-800 whitespace-pre-wrap">{qa.question_text}</p>
      </div>

      {qa.answer_text && (
        <div className="p-4">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{qa.answer_text}</p>
        </div>
      )}

      {isGenerating && (
        <div className="border-t px-4 py-3 flex items-center gap-2 text-sm text-gray-500 bg-primary-50/40">
          <Spinner />
          <span>꼬리질문 생성 중...</span>
        </div>
      )}

      {!isGenerating && followups.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowFollowups(v => !v)}
            className="w-full text-left px-4 py-2 text-sm text-primary font-medium flex items-center gap-1"
          >
            <span>꼬리질문 {followups.length}개</span>
            <span>{showFollowups ? '▲' : '▼'}</span>
          </button>
          {showFollowups && (
            <FollowupPanel
              questions={followups}
              onSelect={onSelectFollowup}
              usedSet={usedFollowups}
            />
          )}
        </div>
      )}
    </div>
  )
}
