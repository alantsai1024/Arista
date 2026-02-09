'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ActivitySquare, HardDrive, LayoutDashboard } from 'lucide-react'
import { cn } from '@/app/lib/format'

export default function Navigation() {
  const pathname = usePathname()
  const links = [
    { href: '/fleet', label: 'Fleet Dashboard', icon: LayoutDashboard },
    { href: '/devices', label: '設備管理', icon: HardDrive },
  ]

  return (
    <nav className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/fleet" className="group flex items-center gap-3">
          <div className="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-500 p-2.5 text-white shadow-lg shadow-brand-500/30">
            <ActivitySquare className="h-5 w-5" />
          </div>
          <div>
            <p className="font-display text-base font-semibold text-slate-900">Arista Monitor</p>
            <p className="text-[11px] text-slate-500">由 Avocado AI 開發</p>
          </div>
        </Link>

        <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-1.5">
          {links.map((link) => {
            const active = pathname === link.href || (link.href !== '/fleet' && pathname.startsWith(link.href))
            const Icon = link.icon
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition',
                  active
                    ? 'bg-white text-brand-700 shadow-sm'
                    : 'text-slate-600 hover:bg-white hover:text-slate-900',
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{link.label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
