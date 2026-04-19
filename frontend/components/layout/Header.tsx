'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function Header() {
  const router = useRouter()
  const logout = () => {
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <header className="h-14 border-b bg-white px-6 flex items-center justify-between">
      <Link href="/" className="font-bold text-xl text-primary">InterX</Link>
      <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">로그아웃</button>
    </header>
  )
}
