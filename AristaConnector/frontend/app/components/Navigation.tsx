'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Navigation() {
  const pathname = usePathname()
  
  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link 
              href="/fleet" 
              className="flex items-center px-4 text-xl font-bold text-gray-900 hover:text-blue-600"
            >
              Arista vEOS Connector
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <Link 
              href="/fleet" 
              className={`px-3 py-2 text-sm font-medium ${
                pathname === '/fleet' 
                  ? 'text-blue-600 border-b-2 border-blue-600' 
                  : 'text-gray-700 hover:text-blue-600'
              }`}
            >
              機群
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
