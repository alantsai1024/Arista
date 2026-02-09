import { cn } from '@/app/lib/format'
import type { LucideIcon } from 'lucide-react'

interface KpiCardProps {
  title: string
  value: number | string
  tone: 'neutral' | 'online' | 'degraded' | 'offline'
  icon: LucideIcon
  subtitle?: string
}

function toneClass(tone: KpiCardProps['tone']) {
  if (tone === 'online') return 'border-emerald-200 bg-emerald-50'
  if (tone === 'degraded') return 'border-amber-200 bg-amber-50'
  if (tone === 'offline') return 'border-rose-200 bg-rose-50'
  return 'border-slate-200 bg-white'
}

function iconClass(tone: KpiCardProps['tone']) {
  if (tone === 'online') return 'bg-emerald-100 text-emerald-700'
  if (tone === 'degraded') return 'bg-amber-100 text-amber-700'
  if (tone === 'offline') return 'bg-rose-100 text-rose-700'
  return 'bg-sky-100 text-sky-700'
}

export default function KpiCard({ title, value, tone, icon: Icon, subtitle }: KpiCardProps) {
  return (
    <article className={cn('rounded-3xl border p-5 shadow-card transition-transform hover:-translate-y-0.5', toneClass(tone))}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-600">{title}</p>
        <div className={cn('rounded-2xl p-2', iconClass(tone))}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-4xl font-display font-bold text-slate-900">{value}</p>
      {subtitle && <p className="mt-2 text-xs text-slate-500">{subtitle}</p>}
    </article>
  )
}

