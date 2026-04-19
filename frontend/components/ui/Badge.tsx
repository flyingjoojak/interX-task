interface BadgeProps {
  status: string
  className?: string
}

const STATUS_COLORS: Record<string, string> = {
  '미분석': 'bg-gray-100 text-gray-600',
  '분석중': 'bg-blue-100 text-blue-700',
  '분석완료': 'bg-green-100 text-green-700',
  '서류합격': 'bg-emerald-100 text-emerald-700',
  '서류탈락': 'bg-red-100 text-red-600',
  '면접합격': 'bg-indigo-100 text-indigo-700',
  '면접탈락': 'bg-red-100 text-red-600',
  '최종합격': 'bg-primary-100 text-primary-700',
  '최종탈락': 'bg-red-100 text-red-600',
}

export default function Badge({ status, className = '' }: BadgeProps) {
  const color = STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color} ${className}`}>
      {status}
    </span>
  )
}
