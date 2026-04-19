import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'InterX — 에이전트 기반 채용 솔루션',
  description: '12가지 핵심가치 기반 후보자 분석 및 면접 지원',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={`${inter.className} bg-gray-50`}>{children}</body>
    </html>
  )
}
