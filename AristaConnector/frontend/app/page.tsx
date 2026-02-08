'use client'

import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  
  // Redirect to fleet page
  if (typeof window !== 'undefined') {
    router.push('/fleet')
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-xl">重新導向中...</div>
    </div>
  )
}
